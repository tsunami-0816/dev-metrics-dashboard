// 接口契约类型（来源：5A OpenAPI http://127.0.0.1:8091/docs，6 paths 实测 2026-11-11）
// 字段名与后端 app/api/* 逐字一致，未臆造任何字段。

export interface Coverage {
  /** 口径范围：全量 / 增量 / 推断 */
  scope: string;
  /** 数据来源表 */
  source: string;
  /** 口径说明 */
  note: string;
}

export interface StepCell {
  step_no: string;
  step_name: string;
  /** E4 归一枚举：未开始/进行中/已完成/卡在人工/已回流/不适用 */
  status: string;
  /** 状态尾注（括号内容剥离） */
  note: string | null;
  finished_at: string | null;
}

export interface ProjectRow {
  name: string;
  route: string;
  board_status: string;
  parse_ok: boolean;
  parsed_at: string;
  steps: StepCell[];
  steps_total: number;
  steps_done: number;
  steps_na: number;
  completion: number;
}

export interface ProjectsResp {
  coverage: Coverage;
  projects: ProjectRow[];
}

export interface ReworkTopItem {
  step_no: string;
  fail_count: number;
  projects: string;
}

export interface ReworkPerProject {
  project_name: string;
  step_no: string;
  fail_count: number;
}

export interface StepsResp {
  coverage: Coverage;
  top: ReworkTopItem[];
  per_project: ReworkPerProject[];
}

export interface FailureCount {
  category?: string;
  root_cause?: string;
  project_name?: string;
  count: number;
}

export interface RecentFailure {
  project_name: string;
  occurred_at: string;
  step_no: string;
  category: string;
  root_cause: string;
  round_no: number;
}

export interface FailuresResp {
  coverage: Coverage;
  total: number;
  by_category: { category: string; count: number }[];
  by_root_cause: { root_cause: string; count: number }[];
  by_project: { project_name: string; count: number }[];
  recent: RecentFailure[];
}

export interface ReworkRateBlock {
  coverage: Coverage;
  overall: {
    projects_with_rework: number;
    total_projects: number;
    rate: number;
  };
  per_project: { project: string; failure_count: number }[];
}

export interface GateTrendBlock {
  coverage: Coverage;
  total: number;
  points: { date: string; count: number }[];
}

export interface EscapeMatrixBlock {
  coverage: Coverage;
  coverage_ratio: { inferable: number; total: number; ratio: number };
  rows: { found_step: string; source_step_inferred: string | null; count: number }[];
}

export interface CrossCompareRow {
  project: string;
  route: string;
  board_status: string;
  steps_total: number;
  steps_done: number;
  completion: number;
  failures: number;
  open_issues: number;
  gate_reds: number;
}

export interface CrossCompareBlock {
  coverage: Coverage;
  projects: CrossCompareRow[];
}

export interface MetricsResp {
  rework_rate: ReworkRateBlock;
  gate_reds_trend: GateTrendBlock;
  escape_matrix: EscapeMatrixBlock;
  cross_compare: CrossCompareBlock;
}

export interface ReconcileFinding {
  rule: string;
  class: string;
  project: string;
  detail: string;
}

export interface UnresolvedItem {
  project_name: string;
  file_name: string;
  line_no: number;
  reason: string;
  action: string;
}

export interface ReconcileResp {
  coverage: Coverage;
  summary: {
    total_findings: number;
    by_class: { "A_产物存在性": number; "B_条数勾稽": number; "C_状态词闭环": number };
    unresolved_count: number;
  };
  classes: {
    "A_产物存在性": ReconcileFinding[];
    "B_条数勾稽": ReconcileFinding[];
    "C_状态词闭环": ReconcileFinding[];
  };
  unresolved: UnresolvedItem[];
}

export interface CollectResp {
  /** 库文件路径 */
  db_path: string;
  /** 项目总数 */
  total: number;
  /** 可解析项目数 */
  parsed_ok: number;
  /** 可解析比率 0~1 */
  ratio: number;
  /** 坏行/降级登记条数 */
  anomalies: number;
  /** 各表行数 */
  counts: Record<string, number>;
  /** 本次采集 ran_at（ISO） */
  collected_at: string | null;
  /** 本次采集项目数 */
  projects: number | null;
}

export interface HealthResp {
  status?: string;
  db_initialized?: boolean;
  /** 最近一次 collect.py 的 ran_at（ISO），源库无 collect_runs 记录时为 null */
  collected_at?: string | null;
  /** 最近一次采集的项目数 */
  projects?: number | null;
}
