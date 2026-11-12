// 步骤列排序：生产线 1→11（含 5A/5B/5.5 分支与 10.x）在前，翻新线 F0→F4 在后，
// 未知步骤号追加尾部按字典序（对 27 种实测 step_no 全覆盖，未知值不丢列）
const CANONICAL = [
  "1", "2", "3", "4", "5A", "5B", "5.5", "6", "6.5", "7", "7.5", "8", "8.5",
  "9", "10", "10.0", "10.5", "10.6", "10.7", "11",
  "F0", "F1", "R-1", "F2", "R-2", "F3", "F4",
];

export function sortStepNos(steps: Iterable<string>): string[] {
  const set = new Set(steps);
  const known = CANONICAL.filter((s) => set.has(s));
  const extra = [...set].filter((s) => !CANONICAL.includes(s)).sort();
  return [...known, ...extra];
}

/** E4 归一状态枚举 → 热力图色块（6 值全覆盖；色只上数据，不上 chrome） */
export const STATUS_COLORS: Record<string, string> = {
  已完成: "#5d9a77",
  进行中: "#2f837a",
  卡在人工: "#d9973c",
  已回流: "#c96868",
  未开始: "#e9ebee",
  不适用: "#f7f7f8",
};

export const STATUS_ORDER = ["已完成", "进行中", "卡在人工", "已回流", "未开始", "不适用"];
