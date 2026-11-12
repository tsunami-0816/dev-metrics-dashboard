// 统一 API client（D-18）
// - 相对路径请求：dev 态走 Vite 代理(5184→8091)，演示态同源直连（T26 StaticFiles）
// - 统一响应包 {code,msg,data}：code=0 出数；code=2 空库引导；其余按服务端错误处理
// - 10s 超时（任务拆解 §6）；网络失败抛 ApiError，由页面渲染错误提示，不白屏

export type ApiErrorKind = "network" | "empty" | "server";

export class ApiError extends Error {
  kind: ApiErrorKind;
  code?: number;
  constructor(kind: ApiErrorKind, message: string, code?: number) {
    super(message);
    this.name = "ApiError";
    this.kind = kind;
    this.code = code;
  }
}

const TIMEOUT_MS = 10_000;

interface Envelope<T> {
  code: number;
  msg: string;
  data: T;
}

interface RequestOptions {
  method?: string;
  body?: unknown;
}

export async function request<T>(path: string, options?: RequestOptions): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  const method = options?.method ?? "GET";
  let resp: Response;
  try {
    resp = await fetch(path, {
      signal: controller.signal,
      method,
      headers:
        options?.body !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: options?.body !== undefined ? JSON.stringify(options.body) : undefined,
    });
  } catch (e) {
    if (e instanceof DOMException && e.name === "AbortError") {
      throw new ApiError("network", "请求超时（10s），请确认 8091 服务已启动");
    }
    throw new ApiError("network", "接口不可用，请确认 8091 服务已启动");
  } finally {
    clearTimeout(timer);
  }
  if (!resp.ok) {
    throw new ApiError("network", `接口异常 HTTP ${resp.status}，请确认 8091 服务已启动`);
  }
  let body: Envelope<T>;
  try {
    body = (await resp.json()) as Envelope<T>;
  } catch {
    throw new ApiError("server", "响应不是合法 JSON");
  }
  if (body.code === 0) {
    return body.data;
  }
  if (body.code === 2) {
    // D-17 空库兜底：后端已给出引导文案，前端原样展示
    throw new ApiError("empty", body.msg || "数据库未初始化，请先运行 collect.py");
  }
  throw new ApiError("server", body.msg || `服务端错误（code=${body.code}）`);
}
