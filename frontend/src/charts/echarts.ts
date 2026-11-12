// ECharts 按需注册（D-18/D-19~D-23 图表渲染）
// 图表风格遵循 app-screen 规则：无 y 轴线、3-5 条浅网格线、柱图方角、单序列无图例
import * as echarts from "echarts/core";
import { BarChart, HeatmapChart, LineChart, PieChart } from "echarts/charts";
import {
  GridComponent,
  TooltipComponent,
  VisualMapComponent,
  LegendComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([
  BarChart,
  HeatmapChart,
  LineChart,
  PieChart,
  GridComponent,
  TooltipComponent,
  VisualMapComponent,
  LegendComponent,
  CanvasRenderer,
]);

export { echarts };
