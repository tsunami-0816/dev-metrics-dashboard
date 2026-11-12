<script setup lang="ts">
// 视图②：步骤返工 TOP 柱状图（D-20 / T18）
// 链路：fetch /api/steps → 横向条形图按失败数降序 + 明细表 → 返工排序一眼可见
import { computed, ref, shallowRef, watch } from "vue";
import type { EChartsOption } from "echarts";
import { useApiData } from "../composables/useApiData";
import { useChart } from "../composables/useChart";
import type { StepsResp } from "../api/types";
import { escapeHtml } from "../lib/escapeHtml";
import ChartCard from "../components/ChartCard.vue";

const { data, loading, error, reload } = useApiData<StepsResp>("/api/steps");

const chartEl = ref<HTMLElement | null>(null);
const option = shallowRef<EChartsOption | null>(null);

const top10 = computed(() => data.value?.top.slice(0, 10) ?? []);

watch(
  [data, top10],
  () => {
    if (!data.value || top10.value.length === 0) {
      option.value = null;
      return;
    }
    // /api/steps 已降序返回；横向条形图 y 轴自下而上绘制，反转保持最大在顶
    const items = [...top10.value].reverse();
    option.value = {
      animation: false,
      tooltip: {
        trigger: "item",
        formatter: (params: unknown) => {
          const p = params as { name: string; value: number; dataIndex: number };
          const item = items[p.dataIndex];
          const projects = item?.projects ?? "";
          const shown = projects.length > 60 ? projects.slice(0, 60) + "…" : projects;
          return `<b>步骤 ${p.name}</b>：${p.value} 次失败<br/>涉及项目：${escapeHtml(shown)}`;
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
        data: items.map((i) => i.step_no),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: "#111111", fontSize: 12 },
      },
      series: [
        {
          type: "bar",
          data: items.map((i) => i.fail_count),
          barWidth: 18,
          itemStyle: { color: "#2f837a", borderRadius: 0 },
          label: {
            show: true,
            position: "right",
            color: "#111111",
            fontSize: 12,
            fontFamily: "inherit",
          },
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
      <h1 class="page-title">步骤返工 TOP</h1>
    </header>
    <ChartCard
      title="失败次数按步骤聚合（前 10）"
      subline="失败日志 triggered_rule / 度量台账 gate_reds 双源交叉提取"
      :coverage="data?.coverage"
      :loading="loading"
      :error="error"
      :empty="!data || data.top.length === 0"
      empty-text="暂无失败记录"
      @retry="reload"
    >
      <div ref="chartEl" class="bar-chart" />
      <div v-if="data && data.per_project.length > 0" class="detail">
        <h3 class="detail-title">项目明细</h3>
        <table class="data-table">
          <thead>
            <tr>
              <th>项目</th>
              <th>步骤</th>
              <th class="num">失败次数</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(row, i) in data.per_project" :key="i">
              <td>{{ row.project_name }}</td>
              <td class="num">{{ row.step_no }}</td>
              <td class="num">{{ row.fail_count }}</td>
            </tr>
          </tbody>
        </table>
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
.bar-chart {
  width: 100%;
  height: 320px;
}
.detail {
  margin-top: 20px;
}
.detail-title {
  margin: 0 0 8px;
  font-size: var(--fs-section);
  font-weight: 600;
}
</style>
