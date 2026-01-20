"use client";

import { useState } from "react";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import type { Monitor, CheckResult } from "@/types/api";

interface MonitorCardProps {
  monitor: Monitor;
  onRunCheck: () => Promise<CheckResult | null>;
  onDelete: () => void;
  onToggle: (enabled: boolean) => void;
  onViewLogs: () => void;
}

function getStatusColor(status: string | null): string {
  switch (status) {
    case "up":
      return "bg-green-500";
    case "degraded":
      return "bg-yellow-500";
    case "down":
      return "bg-red-500";
    default:
      return "bg-gray-500";
  }
}

function getStatusGlow(status: string | null): string {
  switch (status) {
    case "up":
      return "shadow-[0_0_15px_rgba(34,197,94,0.3)]";
    case "degraded":
      return "shadow-[0_0_15px_rgba(234,179,8,0.3)]";
    case "down":
      return "shadow-[0_0_15px_rgba(239,68,68,0.5)]";
    default:
      return "";
  }
}

function formatRelativeTime(dateStr: string | null): string {
  if (!dateStr) return "Never";
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffSec = Math.floor(diffMs / 1000);
  const diffMin = Math.floor(diffSec / 60);
  const diffHour = Math.floor(diffMin / 60);
  const diffDay = Math.floor(diffHour / 24);

  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffMin < 60) return `${diffMin}m ago`;
  if (diffHour < 24) return `${diffHour}h ago`;
  return `${diffDay}d ago`;
}

export function MonitorCard({ monitor, onRunCheck, onDelete, onToggle, onViewLogs }: MonitorCardProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [lastResult, setLastResult] = useState<CheckResult | null>(null);

  async function handleRunCheck() {
    setIsRunning(true);
    try {
      const result = await onRunCheck();
      setLastResult(result);
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <Card className={`relative overflow-hidden transition-all duration-300 hover:border-primary/50 ${!monitor.enabled ? "opacity-50" : ""} ${getStatusGlow(monitor.last_status)}`}>
      {/* Status indicator bar */}
      <div className={`absolute top-0 left-0 right-0 h-1 ${getStatusColor(monitor.last_status)}`} />

      <CardHeader className="pb-3 pt-5">
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${getStatusColor(monitor.last_status)} ${monitor.last_status === "up" || monitor.last_status === "down" ? "animate-pulse" : ""}`} />
              <h3 className="font-semibold truncate">{monitor.name}</h3>
            </div>
            <a
              href={monitor.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted-foreground hover:text-primary truncate block mt-1 transition-colors"
            >
              {monitor.url}
            </a>
          </div>
          <Badge
            variant="outline"
            className={`
              ${monitor.last_status === "up" ? "border-green-500/50 text-green-500" : ""}
              ${monitor.last_status === "degraded" ? "border-yellow-500/50 text-yellow-500" : ""}
              ${monitor.last_status === "down" ? "border-red-500/50 text-red-500" : ""}
              ${!monitor.last_status ? "border-gray-500/50 text-gray-500" : ""}
            `}
          >
            {monitor.last_status || "unknown"}
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Checks */}
        <div className="flex flex-wrap gap-1.5">
          {monitor.checks.map((check, i) => (
            <Badge key={i} variant="secondary" className="text-xs font-mono">
              {check.type}
            </Badge>
          ))}
        </div>

        {/* Tags */}
        {monitor.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {monitor.tags.map((tag) => (
              <Badge key={tag} variant="outline" className="text-xs">
                #{tag}
              </Badge>
            ))}
          </div>
        )}

        {/* Info Grid */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div className="p-2 rounded-md bg-muted/50">
            <div className="text-xs text-muted-foreground">Last check</div>
            <div className="font-medium">{formatRelativeTime(monitor.last_check)}</div>
          </div>
          <div className="p-2 rounded-md bg-muted/50">
            <div className="text-xs text-muted-foreground">Interval</div>
            <div className="font-medium">{monitor.interval}s</div>
          </div>
        </div>

        {/* Last Result */}
        {lastResult && (
          <div className={`p-3 rounded-lg text-sm border ${
            lastResult.status === "up" ? "bg-green-500/10 border-green-500/20" :
            lastResult.status === "degraded" ? "bg-yellow-500/10 border-yellow-500/20" :
            "bg-red-500/10 border-red-500/20"
          }`}>
            <div className="flex justify-between items-center">
              <span className="font-medium">{lastResult.status}</span>
              <span className="text-muted-foreground">{lastResult.elapsed_ms.toFixed(0)}ms</span>
            </div>
            <div className="text-xs text-muted-foreground mt-1 truncate">
              {lastResult.message}
            </div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2 pt-2">
          <Button
            size="sm"
            variant="default"
            onClick={handleRunCheck}
            disabled={isRunning || !monitor.enabled}
          >
            {isRunning ? (
              <svg className="w-4 h-4 animate-spin" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
              </svg>
            )}
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={onViewLogs}
            title="View logs"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => onToggle(!monitor.enabled)}
            title={monitor.enabled ? "Disable" : "Enable"}
          >
            {monitor.enabled ? (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            )}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-red-500 hover:text-red-400 hover:bg-red-500/10"
            onClick={onDelete}
            title="Delete"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
