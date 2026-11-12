<script setup lang="ts">
// 应用外壳（app-screen：labelled 侧边栏 + 画布，无顶栏）
// - 产品名与范围在侧栏顶部（工作流仓 · projects/）
// - 侧栏底部后端健康状态：唯一“活物”，诚实反映 8091 /health
// - ISS-S6-005：「数据截至 HH:MM」= 最近一次 collect.py 采集时间，避免把快照误当实时
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { ApiError, request } from "./api/client";
import type { CollectResp, HealthResp } from "./api/types";

const navItems = [
  { to: "/", label: "项目×步骤热力图" },
  { to: "/rework", label: "步骤返工 TOP" },
  { to: "/root-cause", label: "根因分布" },
  { to: "/gate-trend", label: "门禁报红趋势" },
  { to: "/compare", label: "跨项目对比" },
  { to: "/reconcile", label: "三方对账" },
];

const route = useRoute();
const backendUp = ref<boolean | null>(null);
const health = ref<HealthResp | null>(null);

const refreshing = ref(false);
const collectError = ref<string | null>(null);
const refreshTick = ref(0);

// 一键刷新：先在服务端重采 collect.py 幂等重建，成功后更新「数据截至」并
// 递增 refreshTick 触发 RouterView 重挂载，各视图 onMounted 重新拉取最新数据
async function onRefresh() {
  if (refreshing.value) return;
  refreshing.value = true;
  collectError.value = null;
  try {
    const res = await request<CollectResp>("/api/collect", { method: "POST" });
    health.value = {
      status: "ok",
      db_initialized: true,
      collected_at: res.collected_at,
      projects: res.projects,
    };
    backendUp.value = true;
    refreshTick.value++;
  } catch (e) {
    collectError.value = e instanceof ApiError ? e.message : String(e);
  } finally {
    refreshing.value = false;
  }
}

onMounted(async () => {
  try {
    health.value = await request<HealthResp>("/health");
    backendUp.value = true;
  } catch {
    backendUp.value = false;
  }
});

// "2026-11-11T21:47:08" → "11-11 21:47"；无采集记录时返回 null（不编造时间）
const collectedLabel = computed(() => {
  const raw = health.value?.collected_at;
  if (!raw) return null;
  const m = /^(\d{4})-(\d{2})-(\d{2})[T ](\d{2}):(\d{2})/.exec(raw);
  return m ? `${m[2]}-${m[3]} ${m[4]}:${m[5]}` : raw;
});

const collectedTip = computed(() => {
  if (!collectedLabel.value) return "暂无采集记录：请先运行 collect.py";
  const n = health.value?.projects;
  return `数据为 collect.py 采集快照${n ? `（${n} 个项目）` : ""}；源文件变动后需重跑采集才会更新`;
});
</script>

<template>
  <div class="shell">
    <aside class="sidebar">
      <div class="brand">
        <svg class="mark" viewBox="0 0 24 24" aria-hidden="true">
          <rect x="3" y="3" width="7" height="7" rx="1" />
          <rect x="14" y="3" width="7" height="7" rx="1" />
          <rect x="3" y="14" width="7" height="7" rx="1" />
          <rect x="14" y="14" width="7" height="7" rx="1" opacity="0.35" />
        </svg>
        <div class="brand-text">
          <span class="brand-name">研发效能看板</span>
          <span class="brand-scope">本地工作流仓 projects/</span>
        </div>
      </div>
      <nav class="nav">
        <RouterLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-item"
          :class="{ active: route.path === item.to }"
        >
          {{ item.label }}
        </RouterLink>
      </nav>
      <div class="foot-actions">
        <button class="refresh-btn" type="button" :disabled="refreshing" @click="onRefresh">
          {{ refreshing ? "采集中…" : "刷新数据" }}
        </button>
        <p v-if="collectError" class="foot-error">{{ collectError }}</p>
      </div>
      <div class="sidebar-foot">
        <span class="dot" :class="backendUp === null ? 'unknown' : backendUp ? 'up' : 'down'" />
        <div class="foot-text">
          <span>{{ backendUp === null ? "后端检测中…" : backendUp ? "后端 8091 在线" : "后端 8091 不可达" }}</span>
          <span v-if="collectedLabel && backendUp" class="foot-sub" :title="collectedTip">
            数据截至 {{ collectedLabel }}
          </span>
        </div>
      </div>
    </aside>
    <main class="canvas">
      <RouterView :key="refreshTick" />
    </main>
  </div>
</template>

<style scoped>
.shell {
  display: flex;
  min-height: 100vh;
}
.sidebar {
  width: 232px;
  flex: none;
  display: flex;
  flex-direction: column;
  padding: 16px 12px;
  border-right: 1px solid var(--border);
  background: var(--ground);
}
.brand {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px 16px;
}
.mark {
  width: 22px;
  height: 22px;
  flex: none;
  fill: var(--accent);
}
.brand-text {
  display: flex;
  flex-direction: column;
}
.brand-name {
  font-size: 15px;
  font-weight: 600;
  line-height: 20px;
}
.brand-scope {
  font-size: var(--fs-small);
  color: var(--faint);
}
.nav {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-item {
  display: block;
  line-height: var(--nav-row);
  padding: 0 12px;
  border-radius: 8px;
  font-size: var(--fs-body);
  color: var(--muted);
}
.nav-item:hover {
  background: var(--raised);
  color: var(--text);
}
.nav-item:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: -1px;
}
.nav-item.active {
  background: var(--active);
  color: var(--text);
}
.foot-actions {
  margin-top: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 8px 0;
}
.refresh-btn {
  height: var(--control-height);
  font-size: var(--fs-body);
  background: var(--primary);
  color: #ffffff;
  border: 1px solid var(--primary);
  border-radius: var(--radius-control);
  cursor: pointer;
}
.refresh-btn:hover:not(:disabled) {
  background: var(--accent);
  border-color: var(--accent);
}
.refresh-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
.foot-error {
  margin: 0;
  font-size: var(--fs-small);
  color: var(--negative);
}
.sidebar-foot {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 10px 8px 2px;
}
.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  flex: none;
}
.dot.up {
  background: var(--positive);
}
.dot.down {
  background: var(--negative);
}
.dot.unknown {
  background: var(--control);
}
.foot-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  font-size: var(--fs-small);
  color: var(--faint);
}
.foot-sub {
  color: var(--faint);
  font-variant-numeric: tabular-nums;
  cursor: help;
  white-space: nowrap;
}
.canvas {
  flex: 1;
  min-width: 0;
  padding: 24px 28px 48px;
}
</style>
