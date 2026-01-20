import type { Monitor, MonitorCreate, MonitorUpdate, CheckResult } from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchApi<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;

  // Get auth from localStorage (set during login)
  const auth = typeof window !== "undefined" ? localStorage.getItem("auth") : null;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (auth) {
    headers["Authorization"] = `Basic ${auth}`;
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      ...headers,
      ...(options.headers as Record<string, string>),
    },
  });

  if (!response.ok) {
    const text = await response.text();
    throw new ApiError(response.status, text || response.statusText);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

export const api = {
  // Auth
  setAuth(username: string, password: string) {
    const auth = btoa(`${username}:${password}`);
    if (typeof window !== "undefined") {
      localStorage.setItem("auth", auth);
    }
    return auth;
  },

  clearAuth() {
    if (typeof window !== "undefined") {
      localStorage.removeItem("auth");
    }
  },

  isAuthenticated() {
    if (typeof window !== "undefined") {
      return !!localStorage.getItem("auth");
    }
    return false;
  },

  // Monitors
  async listMonitors(tag?: string): Promise<Monitor[]> {
    const params = tag ? `?tag=${encodeURIComponent(tag)}` : "";
    return fetchApi<Monitor[]>(`/api/monitors${params}`);
  },

  async getMonitor(id: string): Promise<Monitor> {
    return fetchApi<Monitor>(`/api/monitors/${id}`);
  },

  async createMonitor(data: MonitorCreate): Promise<Monitor> {
    return fetchApi<Monitor>("/api/monitors", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  async updateMonitor(id: string, data: MonitorUpdate): Promise<Monitor> {
    return fetchApi<Monitor>(`/api/monitors/${id}`, {
      method: "PUT",
      body: JSON.stringify(data),
    });
  },

  async deleteMonitor(id: string): Promise<void> {
    return fetchApi<void>(`/api/monitors/${id}`, {
      method: "DELETE",
    });
  },

  // Checks
  async runCheck(monitorId: string): Promise<CheckResult> {
    return fetchApi<CheckResult>(`/api/monitors/${monitorId}/check`, {
      method: "POST",
    });
  },

  async runAllChecks(tag?: string): Promise<CheckResult[]> {
    const params = tag ? `?tag=${encodeURIComponent(tag)}` : "";
    return fetchApi<CheckResult[]>(`/api/monitors/check-all${params}`, {
      method: "POST",
    });
  },

  async getResults(monitorId: string, limit = 100): Promise<CheckResult[]> {
    return fetchApi<CheckResult[]>(
      `/api/monitors/${monitorId}/results?limit=${limit}`
    );
  },

  // Tags
  async listTags(): Promise<string[]> {
    return fetchApi<string[]>("/api/monitors/tags");
  },
};

export { ApiError };
