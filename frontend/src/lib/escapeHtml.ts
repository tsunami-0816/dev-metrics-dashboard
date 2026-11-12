// HTML 转义共享 util（ISS-REV-001，5.5 Review P1）
// ECharts tooltip formatter 以 HTML 字符串拼接，所有来自接口的插值
// （项目名/步骤名/状态/尾注/根因等 markdown 自由文本）必须统一转义
export function escapeHtml(s: string | null | undefined): string {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
