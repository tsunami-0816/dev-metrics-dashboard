<script setup lang="ts">
// 视图③：根因分布饼图（D-21 / T19）
// 链路：fetch /api/failures → 根因占比环形图（Top N + 其余合并）+ 最近失败明细表
// 单色相阶梯（teal ramp）+ 灰色「其余」，不做彩虹配色
import { computed, ref, shallowRef, watch } from "vue";
import type { EChartsOption } from "echarts";
import { useApiData } from "../composables/useApiData";
import { useChart } from "../composables/useChart";
import type { FailuresResp } from "../api/types";
import { escapeHtml } from "../lib/escapeHtml";
import ChartCard from "../components/ChartCard.vue";

const TOP_N = 6;
const RAMP = ["#0f766e", "#2f837a", "#4f9089", "#6fa39b", "#8fb6ae", "#aecdc7"];
const OTHER_COLOR = "#c9cdd1";

const { data, loading, error, reload } = useApiData<FailuresResp>("/api/failures");

const chartEl = ref<HTMLElement | null>(null);
const option = shallowRef<EChartsOption | null>(null);

interface Slice {
  name: string;
  value: number;
  color: string;
}

const slices = computed<Slice[]>(() => {
  if (!data.value || data.value.by_root_cause.length === 0) return [];
  const sorted = [...data.value.by_root_cause].sort((a, b) => b.count - a.count);
  const top = sorted.slice(0, TOP_N).map((item, i) => ({
    name: item.root_cause,
    value: item.count,
    color: RAMP[i] ?? RAMP[RAMP.length - 1],
  }));
  const restCount = sorted.slice(TOP_N).reduce((acc, item) => acc + item.count, 0);
  const out = [...top];
  if (restCount > 0) out.push({ name: `其余 ${sorted.length - TOP_N} 类`, value: restCount, color: OTHER_COLOR });
  return out;
});

watch(
  [data, slices],
  () => {
    if (slices.value.length === 0) {
      option.value = null;
      return;
    }
    option.value = {
      animation: false,
      tooltip: {
        trigger: "item",
        formatter: (params: unknown) => {
          const p = params as { name: string; value: number; percent: number };
          return `${escapeHtml(p.name)}<br/><b>${p.value}</b> 条（${p.percent}%）`;
        },
        backgroundColor: "#ffffff",
        borderColor: "#e8e8e8",
        textStyle: { color: "#111111", fontSize: 12 },
        extraCssText: "max-width:360px;white-space:normal;",
      },
      series: [
        {
          type: "pie",
          radius: ["58%", "82%"],
          center: ["50%", "50%"],
          data: slices.value.map((s) => ({
            name: s.name,
            value: s.value,
            itemStyle: { color: s.color },
          })),
          label: { show: false },
          labelLine: { show: false },
          emphasis: { scale: false },
        },
      ],
    };
  },
  { immediate: true },
);

useChart(chartEl, option);

const total = computed(() => data.value?.total ?? 0);
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h1 class="page-title">根因分布</h1>
      <p v-if="data" class="page-sub">失败日志全量 {{ total }} 条（4 种格式代际容错解析）</p>
    </header>
    <div class="grid">
      <ChartCard
        class="pie-card"
        title="失败根因占比"
        :coverage="data?.coverage"
        :loading="loading"
        :error="error"
        :empty="total === 0"
        empty-text="暂无失败记录"
        @retry="reload"
      >
        <div class="pie-row">
          <div ref="chartEl" class="pie-chart" />
          <ul class="legend-table">
            <li v-for="s in slices" :key="s.name" :title="s.name">
              <span class="swatch" :style="{ background: s.color }" />
              <span class="legend-name" :title="s.name">{{ s.name }}</span>
              <span class="num legend-value">{{ s.value }}</span>
            </li>
          </ul>
        </div>
      </ChartCard>
      <ChartCard
        class="recent-card"
        title="最近失败（20 条）"
        :coverage="data?.coverage"
        :loading="loading"
        :error="error"
        :empty="!data || data.recent.length === 0"
        @retry="reload"
      >
        <div class="table-scroll">
          <table class="data-table recent-table">
            <thead>
              <tr>
                <th>项目</th>
                <th>时间</th>
                <th>步骤</th>
                <th>类别</th>
                <th class="cell-truncate" title="根因">根因</th>
                <th class="num">轮次</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(r, i) in data?.recent ?? []" :key="i">
                <td class="cell-truncate" :title="r.project_name">{{ r.project_name }}</td>
                <td class="num">{{ r.occurred_at }}</td>
                <td class="num">{{ r.step_no }}</td>
                <td>{{ r.category }}</td>
                <td class="cell-truncate" :title="r.root_cause">{{ r.root_cause }}</td>
                <td class="num">{{ r.round_no }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </ChartCard>
    </div>
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
}
.grid {
  display: grid;
  grid-template-columns: minmax(420px, 5fr) 7fr;
  gap: var(--gap);
  align-items: start;
}
/* grid 子项默认 min-width:auto 会被表格 min-content 撑破，必须显式归零，滚动容器才生效 */
.grid > * {
  min-width: 0;
}
.pie-row {
  display: flex;
  align-items: center;
  gap: 20px;
}
.pie-chart {
  width: 260px;
  height: 260px;
  flex: none;
}
.legend-table {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
  flex: 1;
}
.legend-table li {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: var(--fs-small);
}
.legend-name {
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.legend-value {
  color: var(--muted);
}
/* 第 6 步冒烟修复：6 列 nowrap 表格在 1440 宽下把整页撑出 134px 横向滚动（inspect: overflow）。
   改为卡片内横向滚动容器，保住列宽与可读性，页面不再横向滚动。 */
.table-scroll {
  overflow-x: auto;
}
/* 6 列在 1440 宽下放不进 7fr 卡片：固定布局 + 全列省略号，保证「轮次」列不被裁掉、页面不横向滚动 */
.recent-table {
  table-layout: fixed;
  width: 100%;
}
.recent-table th,
.recent-table td {
  overflow: hidden;
  text-overflow: ellipsis;
}
.recent-table th:nth-child(1) {
  width: 22%;
}
.recent-table th:nth-child(2) {
  width: 25%;
}
.recent-table th:nth-child(3) {
  width: 7%;
}
.recent-table th:nth-child(4) {
  width: 14%;
}
.recent-table th:nth-child(5) {
  width: 26%;
}
.recent-table th:nth-child(6) {
  width: 7%;
}
.recent-table .cell-truncate {
  max-width: none;
}
.table-scroll .data-table th,
.table-scroll .data-table td {
  padding-left: 8px;
  padding-right: 8px;
}
.swatch {
  width: 10px;
  height: 10px;
  border-radius: 2px;
  flex: none;
}
@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .pie-row {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
