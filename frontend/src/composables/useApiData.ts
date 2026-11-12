// 数据加载组合式函数：加载中 / 错误 / 数据三态，支持手动刷新（防抖由调用方按钮禁用保证）
import { onMounted, ref, shallowRef } from "vue";
import { ApiError, request } from "../api/client";

export function useApiData<T>(path: string) {
  const data = shallowRef<T | null>(null);
  const loading = ref(true);
  const refreshing = ref(false);
  const error = shallowRef<ApiError | null>(null);

  async function load(isRefresh = false): Promise<void> {
    if (isRefresh) {
      refreshing.value = true;
    } else {
      loading.value = true;
    }
    error.value = null;
    try {
      data.value = await request<T>(path);
    } catch (e) {
      error.value = e instanceof ApiError ? e : new ApiError("network", String(e));
      if (isRefresh) {
        // 刷新失败保留旧数据（app-screens：刷新已上屏数据时保留旧值）
      } else {
        data.value = null;
      }
    } finally {
      loading.value = false;
      refreshing.value = false;
    }
  }

  onMounted(() => {
    void load();
  });

  return { data, loading, refreshing, error, reload: () => load(true) };
}
