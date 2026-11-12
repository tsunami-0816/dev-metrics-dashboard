<script setup lang="ts">
// 对账页：不一致 + 未解析清单表格（D-24 / T23）
// 链路：fetch /api/reconcile → A/B/C 三类勾稽差异逐条表格 + 未解析文件清单
// 0 差异时显示「三方一致」提示；超长文本截断 + title 悬浮（任务拆解 §7）
import { computed } from "vue";
import { useApiData } from "../composables/useApiData";
import type { ReconcileResp, ReconcileFinding } from "../api/types";
import ChartCard from "../components/ChartCard.vue";

const { data, loading, error, reload } = useApiData<ReconcileResp>("/api/reconcile");

const CLASS_DEFS = [
  { key: "A_产物存在性", label: "A · 产物存在性" },
  { key: "B_条数勾稽", label: "B · 条数勾稽" },
  { key: "C_状态词闭环", label: "C · 状态词闭环" },
] as const;

const classList = computed(() => {
  if (!data.value) return [];
  return CLASS_DEFS.map((def) => ({
    ...def,
    items: data.value!.classes[def.key] as ReconcileFinding[],
    count: data.value!.summary.by_class[def.key] ?? 0,
  }));
});

const hasFindings = computed(() => (data.value?.summary.total_findings ?? 0) > 0);
</script>

<template>
  <div class="page">
    <header class="page-head">
      <h1 class="page-title">三方对账</h1>
      <p v-if="data" class="page-sub">
        看板 / 台账 / 失败日志三方互验，只读不修数；共
        {{ data.summary.total_findings }} 条差异 · 未解析 {{ data.summary.unresolved_count }} 条
      </p>
    </header>

    <ChartCard
      v-for="cls in classList"
      :key="cls.key"
      class="block"
      :title="`${cls.label}（${cls.count}）`"
      :coverage="data?.coverage"
      :loading="loading"
      :error="error"
      :empty="!data || cls.items.length === 0"
      :empty-text="cls.key === 'A_产物存在性' ? '该类无差异' : '该类无差异'"
      @retry="reload"
    >
      <table class="data-table">
        <thead>
          <tr>
            <th>规则</th>
            <th>项目</th>
            <th>差异详情</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(item, i) in cls.items" :key="i">
            <td class="rule-cell">{{ item.rule }}</td>
            <td>{{ item.project }}</td>
            <td class="cell-truncate detail-cell" :title="item.detail">{{ item.detail }}</td>
          </tr>
        </tbody>
      </table>
    </ChartCard>

    <ChartCard
      class="block"
      :title="`未解析清单（${data?.summary.unresolved_count ?? 0}）`"
      subline="源文件坏行/未知代际显式登记，单文件失败不中断采集"
      :coverage="data?.coverage"
      :loading="loading"
      :error="error"
      :empty="!data || data.unresolved.length === 0"
      empty-text="无未解析记录"
      @retry="reload"
    >
      <table class="data-table">
        <thead>
          <tr>
            <th>项目</th>
            <th>文件</th>
            <th class="num">行号</th>
            <th>原因</th>
            <th>处理动作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(u, i) in data?.unresolved ?? []" :key="i">
            <td>{{ u.project_name }}</td>
            <td>{{ u.file_name }}</td>
            <td class="num">{{ u.line_no }}</td>
            <td class="cell-truncate" :title="u.reason">{{ u.reason }}</td>
            <td>{{ u.action }}</td>
          </tr>
        </tbody>
      </table>
    </ChartCard>

    <div v-if="data && !hasFindings" class="all-clear">三方一致，未发现勾稽差异。</div>
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
.block {
  margin-top: var(--gap);
}
.rule-cell {
  white-space: nowrap;
  color: var(--muted);
}
.detail-cell {
  max-width: 560px;
}
.all-clear {
  margin-top: var(--gap);
  padding: 14px 20px;
  border: 1px dashed var(--control);
  border-radius: var(--radius-card);
  color: var(--muted);
  text-align: center;
}
</style>
