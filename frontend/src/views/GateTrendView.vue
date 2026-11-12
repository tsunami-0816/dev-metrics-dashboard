<script setup lang="ts">
// 视图④：门禁报红趋势折线图（D-22 / T20）
// 链路：fetch /api/metrics → gate_reds_trend.points 折线 → 报红按日期趋势
// 数据量小（当前 4 个日期点）：直线段 + 点标数值，y 轴从 0 起、整数刻度
import { computed, ref, shallowRef, watch } from "vue";
import type { EChartsOption } from "echarts";
import { useApiData } from "../composables/useApiData";
import { useChart } from "../composables/useChart";
import type { MetricsResp } from "../api/types";
import ChartCard from "../components/ChartCard.vue";

const { data, loading, error, reload } = useApiData<MetricsResp>("/api/metrics");

const chartEl = ref<HTMLElement | null>(null);
const option = shallowRef<EChartsOption | null>(null);

const trend = computed(() => data.value?.gate_reds_trend ?? null);

watch(
  [data, trend],
  () => {
    if (!trend.value || trend.value.points.length === 0) {
      option.value = null;
      return;
    }
    option.value = {
      animation: false,
      tooltip: {
        trigger: "item",
        formatter: (params: unknown) => {
          const p = params as { name: string; value: number };
          return `<b>${p.name}</b>：报红 ${p.value} 次`;
        },
        backgroundColor: "#ffffff",
        borderColor: "#e8e8e8",
        textStyle: { color: "#111111", fontSize: 12 },
      },
      grid: { left: 8, top: 24, right: 24, bottom: 8, containLabel: true },
      xAxis: {
        type: "category",
        data: trend.value.points.map((p) => p.date),
        boundaryGap: false,
        axisLine: { show: true, lineStyle: { color: "#e8e8e8" } },
        axisTick: { show: false },
        axisLabel: { color: "#6c6c6c", fontSize: 11 },
      },
      yAxis: {
        type: "value",
        minInterval: 1,
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: "#6c6c6c", fontSize: 11 },
        splitLine: { show: true, lineStyle: { color: "#e5e5e5", width: 1 } },
      },
      series: [
        {
          type: "line",
          data: trend.value.points.map((p) => p.count),
          lineStyle: { color: "#2f837a", width: 2 },
          itemStyle: { color: "#2f837a" },
          symbol: "circle",
          symbolSize: 6,
          label: { show: true, position: "top", color: "#111111", fontSize: 12 },
        },
      ],
    };
  },
  { immediate: true },
);

useChart(chartEl, option);
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h1 class="page-title">门禁报红趋势</h1>
      <p v-if="trend" class="page-sub">
        累计 {{ trend.total }} 次报红（失败日志 triggered_rule + 度量台账 gate_reds 双源）
      </p>
    </header>
    <ChartCard
      title="报红事件按日期"
      :coverage="trend?.coverage"
      :loading="loading"
      :error="error"
      :empty="!trend || trend.points.length === 0"
      empty-text="暂无报红记录"
      @retry="reload"
    >
      <div ref="chartEl" class="line-chart" />
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
}
.line-chart {
  width: 100%;
  height: 280px;
}
</style>
