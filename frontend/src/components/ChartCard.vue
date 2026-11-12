<script setup lang="ts">
// 卡片容器：标题行（左侧 16px/500 标题 + 右侧口径角标）+ 统一 loading/empty/error 三态
// 错误态给「重试」动作（任务拆解 §6：接口不可用统一错误提示，不白屏）
import type { Coverage } from "../api/types";
import type { ApiError } from "../api/client";
import CoverageBadge from "./CoverageBadge.vue";

defineProps<{
  title: string;
  subline?: string;
  coverage?: Coverage | null;
  loading?: boolean;
  error?: ApiError | null;
  empty?: boolean;
  emptyText?: string;
}>();

const emit = defineEmits<{ retry: [] }>();
</script>

<template>
  <section class="card">
    <header class="card-head">
      <div class="head-left">
        <h2 class="card-title">{{ title }}</h2>
        <p v-if="subline" class="subline">{{ subline }}</p>
      </div>
      <CoverageBadge :coverage="coverage" />
    </header>
    <div class="card-body">
      <div v-if="loading" class="state">
        <span class="loading-text">加载中…</span>
      </div>
      <div v-else-if="error" class="state">
        <p class="state-msg">{{ error.message }}</p>
        <button class="retry" type="button" @click="emit('retry')">重试</button>
      </div>
      <div v-else-if="empty" class="state">
        <p class="state-msg">{{ emptyText ?? "暂无数据" }}</p>
      </div>
      <slot v-else />
    </div>
  </section>
</template>

<style scoped>
.card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  padding: var(--card-pad);
}
.card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--gap);
  margin-bottom: 14px;
}
.card-title {
  margin: 0;
  font-size: var(--fs-section);
  font-weight: 600;
  line-height: 22px;
}
.subline {
  margin: 4px 0 0;
  font-size: var(--fs-small);
  color: var(--muted);
}
.state {
  min-height: 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}
.state-msg {
  margin: 0;
  color: var(--muted);
  font-size: var(--fs-body);
  text-align: center;
}
.loading-text {
  color: var(--faint);
}
.retry {
  height: var(--control-height);
  padding: 0 16px;
  font-size: var(--fs-body);
  background: var(--surface);
  border: 1px solid var(--control);
  border-radius: var(--radius-control);
  color: var(--text);
  cursor: pointer;
}
.retry:hover {
  background: var(--raised);
}
.retry:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
</style>
