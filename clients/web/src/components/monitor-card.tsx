"use client";

import { useState } from "react";
import { Card } from "@/components/ui/card";
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
    case "up": return "bg-green-500";
    case "degraded": return "bg-yellow-500";
    case "down": return "bg-red-500";
    default: return "bg-gray-500";
  }
}

function getStatusBorder(status: string | null): string {
  switch (status) {
    case "up": return "border-l-green-500";
    case "degraded": return "border-l-yellow-500";
    case "down": return "border-l-red-500";
    default: return "border-l-gray-500";
  }
}

function formatTime(dateStr: string | null): string {
  if (!dateStr) return "Never";
  return new Date(dateStr).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function MonitorCard({ monitor, onRunCheck, onDelete, onToggle, onViewLogs }: MonitorCardProps) {
  const [isRunning, setIsRunning] = useState(false);
  const [showActions, setShowActions] = useState(false);
  const [lastResult, setLastResult] = useState<CheckResult | null>(null);
  const [flash, setFlash] = useState(false);

  async function handleRunCheck(e: React.MouseEvent) {
    e.stopPropagation();
    setIsRunning(true);
    try {
      const result = await onRunCheck();
      setLastResult(result);
      // Flash effect
      setFlash(true);
      setTimeout(() => setFlash(false), 500);
    } finally {
      setIsRunning(false);
    }
  }

  return (
    <Card
      className={`
        relative overflow-hidden transition-all duration-200
        border-l-4 ${getStatusBorder(monitor.last_status)}
        hover:bg-muted/50 cursor-pointer
        ${!monitor.enabled ? "opacity-50" : ""}
        ${flash ? "ring-2 ring-primary ring-opacity-50" : ""}
      `}
      onClick={onViewLogs}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
    >
      <div className="p-4">
        {/* Header Row */}
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2 min-w-0 flex-1">
            <div className={`w-2.5 h-2.5 rounded-full flex-shrink-0 ${getStatusColor(monitor.last_status)} ${monitor.last_status === "down" ? "animate-pulse" : ""}`} />
            <h3 className="font-semibold truncate">{monitor.name}</h3>
          </div>
          <Badge
            variant="outline"
            className={`
              ml-2 flex-shrink-0 uppercase text-[10px] font-bold tracking-wider
              ${monitor.last_status === "up" ? "border-green-500/50 text-green-400 bg-green-500/10" : ""}
              ${monitor.last_status === "degraded" ? "border-yellow-500/50 text-yellow-400 bg-yellow-500/10" : ""}
              ${monitor.last_status === "down" ? "border-red-500/50 text-red-400 bg-red-500/10" : ""}
              ${!monitor.last_status ? "border-gray-500/50 text-gray-400" : ""}
            `}
          >
            {monitor.last_status || "unknown"}
          </Badge>
        </div>

        {/* URL */}
        <a
          href={monitor.url}
          target="_blank"
          rel="noopener noreferrer"
          onClick={(e) => e.stopPropagation()}
          className="text-sm text-muted-foreground hover:text-primary truncate block mb-3 transition-colors"
        >
          {monitor.url}
        </a>

        {/* Tags & Checks Row */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          {monitor.checks.map((check, i) => (
            <Badge key={i} variant="secondary" className="text-[10px] font-mono px-1.5 py-0">
              {check.type}
            </Badge>
          ))}
          {monitor.tags.slice(0, 3).map((tag) => (
            <Badge key={tag} variant="outline" className="text-[10px] px-1.5 py-0">
              {tag}
            </Badge>
          ))}
          {monitor.tags.length > 3 && (
            <Badge variant="outline" className="text-[10px] px-1.5 py-0">
              +{monitor.tags.length - 3}
            </Badge>
          )}
        </div>

        {/* Stats Row */}
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>Last: {formatTime(monitor.last_check)}</span>
          <span>Every {monitor.interval}s</span>
        </div>

        {/* Last Result */}
        {lastResult && (
          <div className={`
            mt-3 p-3 rounded-md text-xs border font-mono
            ${lastResult.status === "up" ? "bg-green-500/10 border-green-500/30" : ""}
            ${lastResult.status === "degraded" ? "bg-yellow-500/10 border-yellow-500/30" : ""}
            ${lastResult.status === "down" ? "bg-red-500/10 border-red-500/30" : ""}
          `}>
            {/* Status line */}
            <div className={`font-semibold ${
              lastResult.status === "up" ? "text-green-400" :
              lastResult.status === "degraded" ? "text-yellow-400" : "text-red-400"
            }`}>
              {lastResult.status.toUpperCase()} {lastResult.message}
            </div>

            {/* Details grid */}
            <div className="mt-2 space-y-1 text-muted-foreground">
              <div className="flex justify-between">
                <span>Time:</span>
                <span className="text-foreground">{lastResult.elapsed_ms.toFixed(0)}ms</span>
              </div>
              {lastResult.details && Object.entries(lastResult.details).map(([key, value]) => {
                // Handle nested objects (like http checker details)
                if (typeof value === "object" && value !== null) {
                  return Object.entries(value as Record<string, unknown>).map(([k, v]) => (
                    <div key={`${key}-${k}`} className="flex justify-between">
                      <span className="capitalize">{k.replace(/_/g, " ")}:</span>
                      <span className="text-foreground truncate ml-2 max-w-[150px]">{String(v)}</span>
                    </div>
                  ));
                }
                return (
                  <div key={key} className="flex justify-between">
                    <span className="capitalize">{key.replace(/_/g, " ")}:</span>
                    <span className="text-foreground truncate ml-2 max-w-[150px]">{String(value)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Action Buttons - Show on Hover */}
        <div className={`
          flex gap-2 mt-3 pt-3 border-t border-border/50
          transition-all duration-200
          ${showActions ? "opacity-100" : "opacity-0"}
        `}>
          <Button
            size="sm"
            variant="default"
            className="flex-1 h-8 text-xs"
            onClick={handleRunCheck}
            disabled={isRunning || !monitor.enabled}
          >
            {isRunning ? (
              <>
                <svg className="w-3 h-3 mr-1.5 animate-spin" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Checking...
              </>
            ) : (
              <>
                <svg className="w-3 h-3 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                </svg>
                Run Check
              </>
            )}
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs"
            onClick={(e) => { e.stopPropagation(); onToggle(!monitor.enabled); }}
          >
            {monitor.enabled ? "Pause" : "Resume"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-8 w-8 p-0 text-red-500 hover:text-red-400 hover:bg-red-500/10"
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
            </svg>
          </Button>
        </div>

        {/* Click hint */}
        <div className={`
          text-[10px] text-center text-muted-foreground mt-2
          transition-all duration-200
          ${showActions ? "opacity-100" : "opacity-0"}
        `}>
          Click card to view history
        </div>
      </div>
    </Card>
  );
}
