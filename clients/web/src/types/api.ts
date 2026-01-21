export interface Stage {
  type: string;
  username?: string;
  password?: string;
  // Value extractors
  expr?: string;
  store_as?: string;
  // Threshold
  min?: number;
  max?: number;
  value?: string;
  // Contains/Regex
  pattern?: string;
  negate?: boolean;
  // Age
  max_age?: number;
  // SSL
  warn_days?: number;
  // TCP
  port?: number;
  // DNS
  expected_ip?: string;
  // JSON Schema
  schema?: Record<string, unknown>;
}

export interface Monitor {
  id: string;
  name: string;
  url: string;
  pipeline: Stage[];
  interval: number;
  schedule: string | null;
  enabled: boolean;
  tags: string[];
  created_at: string;
  updated_at: string;
  last_check: string | null;
  last_status: "up" | "degraded" | "down" | null;
}

export interface MonitorCreate {
  name: string;
  url: string;
  pipeline?: Stage[];
  interval?: number;
  schedule?: string;
  enabled?: boolean;
  tags?: string[];
}

export interface MonitorUpdate {
  name?: string;
  url?: string;
  pipeline?: Stage[];
  interval?: number;
  schedule?: string;
  enabled?: boolean;
  tags?: string[];
}

export interface CheckResult {
  id: string;
  monitor_id: string;
  status: "up" | "degraded" | "down";
  message: string;
  elapsed_ms: number;
  details: Record<string, unknown>;
  checked_at: string;
}

export type Status = "up" | "degraded" | "down";
