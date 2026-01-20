"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { MonitorCard } from "@/components/monitor-card";
import { MonitorLogs } from "@/components/monitor-logs";
import type { Monitor, CheckResult } from "@/types/api";

interface DashboardProps {
  monitors: Monitor[];
  tags: string[];
  selectedTag: string | null;
  error: string | null;
  onSelectTag: (tag: string | null) => void;
  onLogout: () => void;
  onRefresh: () => void;
  onRunCheck: (monitorId: string) => Promise<CheckResult | null>;
  onRunAllChecks: () => void;
  onDeleteMonitor: (id: string) => void;
  onToggleMonitor: (id: string, enabled: boolean) => void;
  onLoadLogs: (monitorId: string) => Promise<CheckResult[]>;
}

export function Dashboard({
  monitors,
  tags,
  selectedTag,
  error,
  onSelectTag,
  onLogout,
  onRefresh,
  onRunCheck,
  onRunAllChecks,
  onDeleteMonitor,
  onToggleMonitor,
  onLoadLogs,
}: DashboardProps) {
  const [logsMonitor, setLogsMonitor] = useState<Monitor | null>(null);
  const upCount = monitors.filter((m) => m.last_status === "up").length;
  const degradedCount = monitors.filter((m) => m.last_status === "degraded").length;
  const downCount = monitors.filter((m) => m.last_status === "down").length;
  const unknownCount = monitors.filter((m) => m.last_status === null).length;

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 flex items-center justify-center">
                <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-blue-600 bg-clip-text text-transparent">
                  Uptimer
                </h1>
                <p className="text-xs text-muted-foreground">Service Monitoring</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" onClick={onRefresh}>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh
              </Button>
              <Button size="sm" onClick={onRunAllChecks}>
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Run All
              </Button>
              <Button variant="ghost" size="sm" onClick={onLogout}>
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Error Alert */}
        {error && (
          <div className="mb-6 p-4 text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg backdrop-blur">
            {error}
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className={`p-6 rounded-xl border bg-gradient-to-br from-green-500/10 to-green-600/5 border-green-500/20 ${upCount > 0 ? 'glow-green' : ''}`}>
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse"></div>
              <span className="text-sm text-muted-foreground">Up</span>
            </div>
            <div className="text-4xl font-bold text-green-500 mt-2">{upCount}</div>
          </div>
          <div className={`p-6 rounded-xl border bg-gradient-to-br from-yellow-500/10 to-yellow-600/5 border-yellow-500/20 ${degradedCount > 0 ? 'glow-yellow' : ''}`}>
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
              <span className="text-sm text-muted-foreground">Degraded</span>
            </div>
            <div className="text-4xl font-bold text-yellow-500 mt-2">{degradedCount}</div>
          </div>
          <div className={`p-6 rounded-xl border bg-gradient-to-br from-red-500/10 to-red-600/5 border-red-500/20 ${downCount > 0 ? 'glow-red' : ''}`}>
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-red-500 animate-pulse"></div>
              <span className="text-sm text-muted-foreground">Down</span>
            </div>
            <div className="text-4xl font-bold text-red-500 mt-2">{downCount}</div>
          </div>
          <div className="p-6 rounded-xl border bg-gradient-to-br from-gray-500/10 to-gray-600/5 border-gray-500/20">
            <div className="flex items-center gap-3">
              <div className="w-3 h-3 rounded-full bg-gray-500"></div>
              <span className="text-sm text-muted-foreground">Unknown</span>
            </div>
            <div className="text-4xl font-bold text-gray-400 mt-2">{unknownCount}</div>
          </div>
        </div>

        {/* Tags Filter */}
        {tags.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-6">
            <Badge
              variant={selectedTag === null ? "default" : "outline"}
              className="cursor-pointer hover:bg-primary/80 transition-colors"
              onClick={() => onSelectTag(null)}
            >
              All ({monitors.length})
            </Badge>
            {tags.map((tag) => (
              <Badge
                key={tag}
                variant={selectedTag === tag ? "default" : "outline"}
                className="cursor-pointer hover:bg-primary/80 transition-colors"
                onClick={() => onSelectTag(tag)}
              >
                {tag}
              </Badge>
            ))}
          </div>
        )}

        {/* Monitor Grid */}
        {monitors.length === 0 ? (
          <div className="text-center py-16">
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-muted flex items-center justify-center">
              <svg className="w-8 h-8 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M12 2a10 10 0 100 20 10 10 0 000-20z" />
              </svg>
            </div>
            <h3 className="text-lg font-medium text-muted-foreground">No monitors found</h3>
            <p className="text-sm text-muted-foreground mt-1">Create a monitor to start tracking uptime</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {monitors.map((monitor) => (
              <MonitorCard
                key={monitor.id}
                monitor={monitor}
                onRunCheck={() => onRunCheck(monitor.id)}
                onDelete={() => onDeleteMonitor(monitor.id)}
                onToggle={(enabled) => onToggleMonitor(monitor.id, enabled)}
                onViewLogs={() => setLogsMonitor(monitor)}
              />
            ))}
          </div>
        )}

        {/* Logs Modal */}
        <MonitorLogs
          monitor={logsMonitor}
          open={logsMonitor !== null}
          onClose={() => setLogsMonitor(null)}
          onLoadLogs={onLoadLogs}
        />
      </main>
    </div>
  );
}
