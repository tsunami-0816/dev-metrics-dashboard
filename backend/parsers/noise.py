# -*- coding: utf-8 -*-
"""噪声处理规则集（D-07 / 架构 §3 硬规则 1-4）.

规则编号与架构《第二轮技术架构设计文档》§3 一一对应：
- §3-1 HTML 注释行跳过（模板示例行不产生数据）
- §3-2 空单元格容错（空值 → NULL 落库，不算坏行）
- §3-3 步骤号归一（第5.5步 / step6.5 / 6.5 → 统一 label）
- §3-4 状态词归一映射 + 括号尾注剥离（E4）
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterator, List, Optional, Tuple

# E4 归一枚举（固定 6 值）
STATUS_ENUM = ("未开始", "进行中", "已完成", "卡在人工", "已回流", "不适用")

# 前缀 → 枚举映射表（顺序即匹配优先级；同前缀族内更长的词在前）
_PREFIX_MAP: Tuple[Tuple[str, str], ...] = (
    ("未开始", "未开始"),
    ("进行中", "进行中"),
    ("卡在人工", "卡在人工"),
    ("已回流", "已回流"),
    ("不适用", "不适用"),
    ("已人工放行", "已完成"),
    ("已完成", "已完成"),
    ("已通过", "已完成"),
    ("已闭环", "已完成"),
    ("已交付", "已完成"),
    ("已豁免", "不适用"),
    ("跳过", "不适用"),
    ("忽略", "不适用"),
)

# 模块级注释行跳过计数（collect_runs.skipped_lines 汇总用）
_SKIPPED_TOTAL = 0


def reset_skipped_total() -> None:
    """重置模块级计数（每次采集开始时调用）."""
    global _SKIPPED_TOTAL  # noqa: PLW0603
    _SKIPPED_TOTAL = 0


def total_skipped_lines() -> int:
    """本次采集累计跳过的注释/噪声行数."""
    return _SKIPPED_TOTAL


def _bump_skipped(n: int) -> None:
    global _SKIPPED_TOTAL  # noqa: PLW0603
    _SKIPPED_TOTAL += n


# 开头的装饰符号 / emoji（✅ ⏭️ 🤖 👤 等，含变体选择符 U+FE0F）
_LEAD_SYMBOL_RE = re.compile(r"^[^\u4e00-\u9fffA-Za-z0-9（(]+")

# 步骤号 label：第5.5步 / step6.5 / 6.5 / 5A / F0 / 10.0 / 👤 R-1（人工卡点行）
_STEP_RE = re.compile(r"^(?:第|step)?([0-9]+(?:\.[0-9]+)?[ab]?|f[0-9]+|r-[0-9]+)(?:步)?$")


@dataclass
class ParseAnomaly:
    """坏行/坏文件登记项（D-08，落 parse_anomalies 表）."""

    project_name: str
    file_name: str
    line_no: Optional[int] = None
    reason: str = ""
    action: str = "跳过"


@dataclass
class AnomalyLog:
    """单项目解析过程中的异常收集器（C01：单文件异常不中断）."""

    project_name: str
    items: List[ParseAnomaly] = field(default_factory=list)

    def add(
        self,
        file_name: str,
        reason: str,
        line_no: Optional[int] = None,
        action: str = "跳过",
    ) -> None:
        self.items.append(
            ParseAnomaly(
                project_name=self.project_name,
                file_name=file_name,
                line_no=line_no,
                reason=reason,
                action=action,
            )
        )


class TableScanner:
    """markdown 表格行扫描器（§3-1 注释跳过 + 分隔行/全空行跳过）.

    用法：
        scanner = TableScanner()
        for lineno, cells in scanner.rows(text):
            ...
        scanner.skipped_comment_lines  # 本文件跳过的注释行数
    （模块级 total_skipped_lines() 汇总所有 scanner 的计数，供 collect_runs.skipped_lines）
    """

    def __init__(self) -> None:
        self.skipped_comment_lines = 0

    def rows(self, text: str) -> Iterator[Tuple[int, List[str]]]:
        in_comment = False
        for lineno, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if in_comment:  # §3-1：多行注释内部
                self.skipped_comment_lines += 1
                _bump_skipped(1)
                if "-->" in line:
                    in_comment = False
                continue
            if line.startswith("<!--"):  # §3-1：注释起始行
                self.skipped_comment_lines += 1
                _bump_skipped(1)
                if "-->" not in line:
                    in_comment = True
                continue
            if not line.startswith("|"):
                continue
            cells = split_row(line)
            if is_separator_row(cells):
                continue
            if not any(cells):  # §3-2：全空行（无任何信息的表格行）跳过
                continue
            yield lineno, cells


def split_row(line: str) -> List[str]:
    """把一行 markdown 表格切成单元格列表（§3-2：空单元格保留为 ''）."""
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def is_separator_row(cells: List[str]) -> bool:
    """判定 |---|---| 形态的分隔行."""
    non_empty = [c for c in cells if c]
    if not non_empty:
        return False
    return all(re.fullmatch(r":?-{2,}:?", c) for c in non_empty)


def align_row(
    cells: List[str],
    header_len: int,
    anomaly_log: Optional[AnomalyLog] = None,
    file_name: str = "",
    lineno: Optional[int] = None,
) -> Optional[List[str]]:
    """行对齐到表头列数（§3-2 + 溢出吸收）.

    - 不足：右侧补 ''（空单元格 → NULL）
    - 溢出：多余单元格合并进最后一列（自由文本列），并登记 parse_anomaly
    - 全空行：返回 None
    """
    if not any(cells):
        return None
    if len(cells) <= header_len:
        return cells + [""] * (header_len - len(cells))
    merged = cells[: header_len - 1] + [" | ".join(cells[header_len - 1 :])]
    if anomaly_log is not None:
        anomaly_log.add(
            file_name,
            f"行单元格数({len(cells)})多于表头列数({header_len})，溢出合并进最后一列",
            line_no=lineno,
            action="吸收溢出",
        )
    return merged


def normalize_step_label(raw: Optional[str]) -> Optional[str]:
    """§3-3 步骤号归一：返回统一 label（'5.5' / '5A' / 'F0' / 'R-1' / '10.0'），不可识别返回 None.

    注意：'10' 与 '10.0' 是两个不同步骤，不做浮点化（避免 10.0→10 撞车）。
    兼容 '👤 R-1' / '👤 9' 这类带人工卡点 emoji 前缀的翻新线步骤标签。
    """
    if raw is None:
        return None
    s = str(raw).strip().lower().replace(" ", "").replace("\u3000", "")
    if not s:
        return None
    s = _LEAD_SYMBOL_RE.sub("", s)  # 剥离 👤/🤖 等前缀符号
    m = _STEP_RE.match(s)
    if not m:
        return None
    return m.group(1).upper()


def normalize_status(raw: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """§3-4 状态词归一：返回 (枚举状态, 尾注).

    - 剥离 markdown 加粗与开头 emoji/装饰符
    - 括号尾注（如「已完成（附条件通过）」）剥离进 note，不丢信息
    - 前缀匹配到固定 6 值枚举；未匹配 → (原文, None)，由对账规则 C 兜底暴露
    """
    if raw is None or not str(raw).strip():
        return (None, None)
    s = str(raw).strip().replace("**", "").strip()
    s = _LEAD_SYMBOL_RE.sub("", s)
    note: Optional[str] = None
    m = re.match(r"^(.*?)[（(](.*)[)）]\s*$", s)
    if m and m.group(1).strip():
        s = m.group(1).strip()
        note = m.group(2).strip()
    for prefix, enum in _PREFIX_MAP:
        if s.startswith(prefix):
            if note is None:
                if prefix in ("跳过", "忽略", "已豁免"):
                    note = prefix
                elif prefix == "已人工放行":
                    note = "人工放行"
            return (enum, note)
    return (s, note)


def to_int(raw: Optional[str]) -> Optional[int]:
    """'1'→1 / 'R1'→1 / '第2轮'→2 / 空→None（§3-2）."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    m = re.search(r"(\d+)", s)
    return int(m.group(1)) if m else None


def to_float(raw: Optional[str]) -> Optional[float]:
    """'12.5'→12.5 / 空→None."""
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)", s)
    return float(m.group(1)) if m else None


def nonempty(raw: Optional[str]) -> Optional[str]:
    """§3-2 空单元格 → None（NULL 落库）."""
    if raw is None:
        return None
    s = str(raw).strip()
    return s if s else None


def extract_section(text: str, heading_regex: str) -> str:
    """截取标题匹配 heading_regex 的 # 段落正文.

    - heading_regex 与「去掉 # 前缀后的标题文本」做 search（兼容 #/##/### 任意级别）
    - 段内更深层级的子标题（如基本信息段里的 ### 端口分配）视为段内内容，不截断
    - 遇到同级或更浅级别的标题时结束
    """
    lines = text.splitlines()
    out: List[str] = []
    in_section = False
    section_level = 0
    pat = re.compile(heading_regex)
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("#"):
            level = len(stripped) - len(stripped.lstrip("#"))
            heading_text = stripped.lstrip("#").strip()
            if in_section:
                if level <= section_level:
                    break
                out.append(line)  # 更深层级子标题：段内内容
                continue
            if pat.search(heading_text):
                in_section = True
                section_level = level
            continue
        if in_section:
            out.append(line)
    return "\n".join(out)
