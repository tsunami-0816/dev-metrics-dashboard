<script setup lang="ts">
// 视图⑤：跨项目对比 + 逃逸矩阵（降级口径）覆盖率角标（D-23 / T21，高风险项）
// 链路：fetch /api/metrics → 全景对比表 + 失败数条形图 + 逃逸矩阵 N/M 角标
// 覆盖率角标数值必须与接口 coverage_ratio 一致（T21 验收标准）
import { computed, ref, shallowRef, watch } from "vue";
import type { EChartsOption } from "echarts";
import { useApiData } from "../composables/useApiData";
import { useChart } from "../composables/useChart";
import type { MetricsResp } from "../api/types";
import { escapeHtml } from "../lib/escapeHtml";
import ChartCard from "../components/ChartCard.vue";

const { data, loading, error, reload } = useApiData<MetricsResp>("/api/metrics");

const compare = computed(() => data.value?.cross_compare ?? null);
const escape = computed(() => data.value?.escape_matrix ?? null);

// 按失败数降序（对比图：谁返工最多）
const failBars = computed(() =>
  [...(compare.value?.projects ?? [])].sort((a, b) => b.failures - a.failures),
);

const barEl = ref<HTMLElement | null>(null);
const barOption = shallowRef<EChartsOption | null>(null);

watch(
  [data, failBars],
  () => {
    if (!compare.value || failBars.value.length === 0) {
      barOption.value = null;
      return;
    }
    const items = [...failBars.value].reverse();
    barOption.value = {
      animation: false,
      tooltip: {
        trigger: "item",
        formatter: (params: unknown) => {
          const p = params as { name: string; value: number; dataIndex: number };
          const row = items[p.dataIndex];
          return `<b>${escapeHtml(p.name)}</b>：失败 ${p.value} 次 · 未关闭问题 ${row?.open_issues ?? 0} · 报红 ${row?.gate_reds ?? 0}`;
        },
        backgroundColor: "#ffffff",
        borderColor: "#e8e8e8",
        textStyle: { color: "#111111", fontSize: 12 },
        extraCssText: "max-width:360px;white-space:normal;",
      },
      grid: { left: 8, top: 8, right: 40, bottom: 8, containLabel: true },
      xAxis: {
        type: "value",
        minInterval: 1,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: "#6c6c6c", fontSize: 11 },
        splitLine: { show: true, lineStyle: { color: "#e5e5e5", width: 1 } },
      },
      yAxis: {
        type: "category",
        data: items.map((p) => p.project),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: "#111111", fontSize: 12 },
      },
      series: [
        {
          type: "bar",
          data: items.map((p) => p.failures),
          barWidth: 14,
          itemStyle: { color: "#2f837a", borderRadius: 0 },
          label: { show: true, position: "right", color: "#111111", fontSize: 12 },
        },
      ],
    };
  },
  { immediate: true },
);

useChart(barEl, barOption);

// 逃逸矩阵：found_step(行) × source_step_inferred(列)
const matrix = computed(() => {
  if (!escape.value) return null;
  const found = [...new Set(escape.value.rows.map((r) => r.found_step))];
  const sources = [...new Set(escape.value.rows.map((r) => r.source_step_inferred ?? "—"))];
  const cell = new Map<string, number>();
  for (const r of escape.value.rows) {
    cell.set(`${r.found_step}|${r.source_step_inferred ?? "—"}`, r.count);
  }
  return { found, sources, cell };
});

const escapeBadgeCoverage = computed(() => {
  const e = escape.value;
  if (!e) return null;
  return {
    scope: "推断",
    source: e.coverage.source,
    note: `${e.coverage.note}（仅 source 维度可推断的 ${e.coverage_ratio.inferable}/${e.coverage_ratio.total} 条问题参与计数，覆盖率 ${(e.coverage_ratio.ratio * 100).toFixed(1)}%）`,
  };
});
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h1 class="page-title">跨项目对比</h1>
    </header>
    <ChartCard
      title="项目全景对比"
      subline="步骤完成度 / 失败 / 未关闭问题 / 报红，四列同看"
      :coverage="compare?.coverage"
      :loading="loading"
      :error="error"
      :empty="!compare || compare.projects.length === 0"
      empty-text="暂无项目数据"
      @retry="reload"
    >
      <table class="data-table">
        <thead>
          <tr>
            <th>项目</th>
            <th>路线</th>
            <th>看板状态</th>
            <th class="num">步骤（完成/总）</th>
            <th class="num">完成度</th>
            <th class="num">失败</th>
            <th class="num">未关闭问题</th>
            <th class="num">报红</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="p in compare?.projects ?? []" :key="p.project">
            <td class="cell-truncate" :title="p.board_status ? `${p.project}（${p.board_status}）` : p.project">
              {{ p.project }}
            </td>
            <td>{{ p.route }}</td>
            <td class="cell-truncate" :title="p.board_status">{{ p.board_status }}</td>
            <td class="num">{{ p.steps_done }}/{{ p.steps_total }}</td>
            <td class="num">{{ (p.completion * 100).toFixed(0) }}%</td>
            <td class="num">{{ p.failures }}</td>
            <td class="num">{{ p.open_issues }}</td>
            <td class="num">{{ p.gate_reds }}</td>
          </tr>
        </tbody>
      </table>
    </ChartCard>

    <ChartCard
      class="block"
      title="失败数按项目"
      :coverage="compare?.coverage"
      :loading="loading"
      :error="error"
      :empty="!compare || compare.projects.length === 0"
      @retry="reload"
    >
      <div ref="barEl" class="bar-chart" />
    </ChartCard>

    <ChartCard
      class="block"
      title="逃逸矩阵（found × source 推断）"
      subline="问题在哪个阶段被发现（行）× 归属哪个步骤（列，文本推断）"
      :coverage="escapeBadgeCoverage"
      :loading="loading"
      :error="error"
      :empty="!matrix || matrix.found.length === 0"
      empty-text="无可算的逃逸数据"
      @retry="reload"
    >
      <p v-if="escape" class="coverage-line">
        覆盖率：仅 {{ escape.coverage_ratio.inferable }}/{{ escape.coverage_ratio.total }} 条问题可推断归属步骤
        （{{ (escape.coverage_ratio.ratio * 100).toFixed(1) }}%）；推断不了的显式留空，不硬凑。
      </p>
      <table v-if="matrix" class="data-table matrix-table">
        <thead>
          <tr>
            <th>found \ source</th>
            <th v-for="s in matrix.sources" :key="s" class="num">{{ s }}</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in matrix.found" :key="f">
            <th>{{ f }}</th>
            <td v-for="s in matrix.sources" :key="s" class="num">
              <span v-if="matrix.cell.get(`${f}|${s}`) !== undefined" class="matrix-cell">{{ matrix.cell.get(`${f}|${s}`) }}</span>
              <span v-else class="matrix-empty">–</span>
            </td>
          </tr>
        </tbody>
      </table>
    </ChartCard>
  </div>
</template>

<style scoped>
.page-head {
  margin-bottom: 20px;
}
.page-title {
  margin: 0;
  font-size: var(--fs-title);
  font-weight: 600;
  line-height: 32px;
}
.block {
  margin-top: var(--gap);
}
.bar-chart {
  width: 100%;
  height: 300px;
}
.coverage-line {
  margin: 0 0 12px;
  font-size: var(--fs-small);
  color: var(--muted);
}
.matrix-table th {
  font-weight: 600;
  color: var(--text);
}
.matrix-cell {
  display: inline-block;
  min-width: 28px;
  padding: 2px 8px;
  border-radius: var(--radius-chip);
  background: var(--accent-tint);
  color: var(--accent);
  font-weight: 600;
}
.matrix-empty {
  color: var(--control);
}
</style>
