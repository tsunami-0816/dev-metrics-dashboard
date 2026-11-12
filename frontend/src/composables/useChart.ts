// 图表实例组合式函数：初始化 / 数据驱动 setOption / 容器自适应 / 卸载销毁
// 注意：卡片槽位在 loading 结束后才挂载，必须等 DOM 更新完成（flush: post）再 init，
// 否则容器 ref 仍为 null 导致图表不初始化（批1 实测踩到：数据到了但图空白）。
import { onBeforeUnmount, watch, type Ref, type ShallowRef } from "vue";
import type { EChartsOption } from "echarts";
import { echarts } from "../charts/echarts";

export function useChart(
  elRef: Ref<HTMLElement | null>,
  optionRef: ShallowRef<EChartsOption | null>,
): { resize: () => void } {
  let chart: echarts.ECharts | null = null;
  let observer: ResizeObserver | null = null;

  function ensureChart(): echarts.ECharts | null {
    if (!elRef.value) return null;
    if (!chart) {
      chart = echarts.init(elRef.value);
      observer = new ResizeObserver(() => chart?.resize());
      observer.observe(elRef.value);
    }
    return chart;
  }

  watch(
    [elRef, optionRef],
    () => {
      const opt = optionRef.value;
      if (!opt || !elRef.value) return;
      ensureChart()?.setOption(opt, { notMerge: true });
    },
    { immediate: true, flush: "post" },
  );

  onBeforeUnmount(() => {
    observer?.disconnect();
    chart?.dispose();
    chart = null;
  });

  return {
    resize: () => chart?.resize(),
  };
}
