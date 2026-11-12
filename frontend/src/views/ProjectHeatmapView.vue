<script setup lang="ts">
// 视图①：项目×步骤热力图（D-19 / T17）
// 链路：fetch /api/projects → ECharts heatmap → 卡点状态色块可见，悬浮看尾注
import { computed, ref, shallowRef, watch } from "vue";
import type { EChartsOption } from "echarts";
import { useApiData } from "../composables/useApiData";
import { useChart } from "../composables/useChart";
import { STATUS_COLORS, STATUS_ORDER, sortStepNos } from "../lib/stepOrder";
import { escapeHtml } from "../lib/escapeHtml";
import type { ProjectsResp, StepCell } from "../api/types";
import ChartCard from "../components/ChartCard.vue";

const { data, loading, error, reload } = useApiData<ProjectsResp>("/api/projects");

const chartEl = ref<HTMLElement | null>(null);
const option = shallowRef<EChartsOption | null>(null);

interface CellPayload {
  project: string;
  stepLabel: string;
  cell: StepCell;
}

const stepCols = computed(() => {
  if (!data.value) return [];
  return sortStepNos(data.value.projects.flatMap((p) => p.steps.map((s) => s.step_no)));
});

const projectNames = computed(() => data.value?.projects.map((p) => p.name) ?? []);

watch(
  [data, stepCols],
  () => {
    if (!data.value || stepCols.value.length === 0) {
      option.value = null;
      return;
    }
    const xIdx = new Map(stepCols.value.map((s, i) => [s, i]));
    const yIdx = new Map(projectNames.value.map((p, i) => [p, i]));
    const seriesData: { value: [number, number, number]; payload: CellPayload }[] = [];
    for (const p of data.value.projects) {
      for (const s of p.steps) {
        const xi = xIdx.get(s.step_no);
        const yi = yIdx.get(p.name);
        if (xi === undefined || yi === undefined) continue;
        seriesData.push({
          value: [xi, yi, STATUS_ORDER.indexOf(s.status)],
          payload: { project: p.name, stepLabel: `${s.step_no} ${s.step_name}`, cell: s },
        });
      }
    }
    option.value = {
      animation: false,
      tooltip: {
        trigger: "item",
        formatter: (params: unknown) => {
          const p = params as { data?: { payload?: CellPayload } };
          const d = p.data?.payload;
          if (!d) return "";
          const note = d.cell.note ? `<br/>尾注：${escapeHtml(d.cell.note)}` : "";
          const finished = d.cell.finished_at ? `<br/>完成：${escapeHtml(d.cell.finished_at)}` : "";
          return `<b>${escapeHtml(d.project)}</b> · ${escapeHtml(d.stepLabel)}<br/>状态：${escapeHtml(d.cell.status)}${note}${finished}`;
        },
        backgroundColor: "#ffffff",
        borderColor: "#e8e8e8",
        textStyle: { color: "#111111", fontSize: 12 },
        extraCssText: "max-width:360px;white-space:normal;",
      },
      grid: { left: 8, top: 8, right: 8, bottom: 28, containLabel: true },
      xAxis: {
        type: "category",
        data: stepCols.value,
        splitArea: { show: false },
        axisLine: { show: true, lineStyle: { color: "#e8e8e8" } },
        axisTick: { show: false },
        axisLabel: { color: "#6c6c6c", fontSize: 11, interval: 0, hideOverlap: true },
      },
      yAxis: {
        type: "category",
        data: projectNames.value,
        inverse: true,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: "#111111", fontSize: 12 },
      },
      visualMap: {
        show: false,
        type: "piecewise",
        min: 0,
        max: STATUS_ORDER.length - 1,
        pieces: STATUS_ORDER.map((status, idx) => ({
          value: idx,
          color: STATUS_COLORS[status],
        })),
      },
      series: [
        {
          type: "heatmap",
          data: seriesData,
          itemStyle: { borderColor: "#ffffff", borderWidth: 1 },
          emphasis: { itemStyle: { borderColor: "#111111", borderWidth: 1 } },
        },
      ],
    };
  },
  { immediate: true },
);

useChart(chartEl, option);

const presentStatuses = computed(() =>
  STATUS_ORDER.filter((s) =>
    data.value?.projects.some((p) => p.steps.some((c) => c.status === s)),
  ),
);

const summary = computed(() => {
  if (!data.value) return null;
  const ps = data.value.projects;
  const avg = ps.reduce((acc, p) => acc + p.completion, 0) / (ps.length || 1);
  const blocked = ps.reduce(
    (acc, p) => acc + p.steps.filter((s) => s.status === "卡在人工" || s.status === "进行中").length,
    0,
  );
  return { total: ps.length, avg, blocked };
});
</script>

<template>
  <div class="page">
    <header class="page-head">
      <div>
        <h1 class="page-title">项目×步骤热力图</h1>
        <p v-if="summary" class="page-sub">
          {{ summary.total }} 个项目 · 平均完成度 {{ (summary.avg * 100).toFixed(0) }}% · 进行中/卡在人工步骤 {{ summary.blocked }} 个
        </p>
      </div>
    </header>
    <ChartCard
      title="步骤推进状态矩阵"
      subline="色块 = 归一后状态；悬浮查看步骤名与尾注。空白 = 该项目无此步骤（生产/翻新线差异）"
      :coverage="data?.coverage"
      :loading="loading"
      :error="error"
      :empty="!data || data.projects.length === 0"
      empty-text="暂无项目数据"
      @retry="reload"
    >
      <div ref="chartEl" class="heatmap" />
      <div class="legend">
        <span v-for="s in presentStatuses" :key="s" class="legend-item">
          <span class="swatch" :style="{ background: STATUS_COLORS[s] }" />
          {{ s }}
        </span>
      </div>
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
.page-sub {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: var(--fs-body);
}
.heatmap {
  width: 100%;
  height: 420px;
}
.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 12px;
}
.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-small);
  color: var(--muted);
}
.swatch {
  width: 12px;
  height: 12px;
  border-radius: 2px;
  border: 1px solid var(--border);
}
</style>
