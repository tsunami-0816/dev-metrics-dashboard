<script setup lang="ts">
// D-25 数据源覆盖范围角标：全量 / 增量 / 推断 三级口径（T22）
// scope 值来自接口 coverage.scope 字段，未臆造；title 悬浮展示 source + note 全文
import { computed } from "vue";
import type { Coverage } from "../api/types";

const props = defineProps<{ coverage: Coverage | null | undefined }>();

const levelClass = computed(() => {
  const scope = props.coverage?.scope ?? "";
  if (scope === "全量") return "badge-full";
  if (scope === "增量") return "badge-incremental";
  return "badge-inferred"; // 推断 / 未知口径按最谨慎一级展示
});

const tip = computed(() => {
  if (!props.coverage) return "";
  return `口径：${props.coverage.scope}\n来源：${props.coverage.source}\n${props.coverage.note}`;
});
</script>

<template>
  <span
    v-if="coverage"
    class="badge"
    :class="levelClass"
    :title="tip"
  >口径：{{ coverage.scope }}</span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  align-items: center;
  flex: none;
  white-space: nowrap;
  font-size: var(--fs-small);
  line-height: 1;
  padding: 4px 8px;
  border-radius: var(--radius-chip);
  border: 1px solid transparent;
  cursor: help;
}
.badge-full {
  background: #eef4f0;
  color: var(--positive);
  border-color: #d9e8e0;
}
.badge-incremental {
  background: #f1f3f4;
  color: var(--muted);
  border-color: #e2e4e6;
}
.badge-inferred {
  background: #fdf6e7;
  color: var(--warning);
  border-color: #f3e3c0;
}
</style>
