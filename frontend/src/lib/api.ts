import axios, { AxiosError } from "axios";

const ACCESS_KEY = "tms.access";
const REFRESH_KEY = "tms.refresh";

export const tokenStore = {
  get access() {
    return localStorage.getItem(ACCESS_KEY);
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh: string) {
    localStorage.setItem(ACCESS_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export const api = axios.create({
  baseURL: "/api/v1",
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = tokenStore.access;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Routes that must render even without a (valid) session. A failed token
// refresh here should not bounce the visitor to /login.
const PUBLIC_AUTH_PATHS = [
  "/login",
  "/register",
  "/set-password",
  "/reset-password",
  "/forgot-password",
  "/verify",
];

function isPublicAuthPath(pathname: string): boolean {
  return PUBLIC_AUTH_PATHS.some((p) => pathname.startsWith(p));
}

let refreshing: Promise<string> | null = null;

async function doRefresh(): Promise<string> {
  const refresh = tokenStore.refresh;
  if (!refresh) throw new Error("No refresh token");
  const { data } = await axios.post("/api/v1/auth/refresh", {
    refresh_token: refresh,
  });
  tokenStore.set(data.access_token, data.refresh_token);
  return data.access_token;
}

api.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as any;
    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      tokenStore.refresh &&
      !original.url?.includes("/auth/login") &&
      !original.url?.includes("/auth/refresh")
    ) {
      original._retry = true;
      try {
        refreshing = refreshing ?? doRefresh();
        const token = await refreshing;
        refreshing = null;
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      } catch (e) {
        refreshing = null;
        tokenStore.clear();
        // Don't hijack public auth pages (e.g. an employee opening their
        // password-setup link with a stale/expired session still lingering in
        // localStorage) — clearing the tokens is enough; let them stay.
        if (!isPublicAuthPath(window.location.pathname)) {
          window.location.href = "/login";
        }
      }
    }
    return Promise.reject(error);
  }
);

// Turn a FastAPI/Pydantic validation error item into a human-readable message.
// Raw messages like "String should match pattern '^[a-zA-Z0-9._-]+$'" are
// meaningless to an admin, so we map the common cases to plain language.
function humanizeValidationError(item: any): string | null {
  if (!item) return null;
  const field = Array.isArray(item.loc) ? String(item.loc[item.loc.length - 1]) : "";
  const label = field
    ? field.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())
    : "Field";
  if (item.type === "string_pattern_mismatch") {
    if (field === "username") {
      return "Username can be a handle or an email address — letters, numbers and . _ % + @ - only (no spaces).";
    }
    return `${label} contains invalid characters.`;
  }
  if (item.type === "string_too_short") {
    return `${label} is too short.`;
  }
  if (item.type === "string_too_long") {
    return `${label} is too long.`;
  }
  return item.msg ?? null;
}

export function apiError(err: unknown, fallback = "Something went wrong"): string {
  const ax = err as AxiosError<any>;
  const detail = ax?.response?.data?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail) && detail.length) {
    return humanizeValidationError(detail[0]) ?? fallback;
  }
  return ax?.message ?? fallback;
}
