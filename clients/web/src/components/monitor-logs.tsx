"use client";

import { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Badge } from "@/components/ui/badge";
import type { Monitor, CheckResult } from "@/types/api";

interface MonitorLogsProps {
  monitor: Monitor | null;
  open: boolean;
  onClose: () => void;
  onLoadLogs: (monitorId: string) => Promise<CheckResult[]>;
}

function formatDateTime(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleString();
}

function getStatusColor(status: string): string {
  switch (status) {
    case "up":
      return "bg-green-500/10 border-green-500/30 text-green-400";
    case "degraded":
      return "bg-yellow-500/10 border-yellow-500/30 text-yellow-400";
    case "down":
      return "bg-red-500/10 border-red-500/30 text-red-400";
    default:
      return "bg-gray-500/10 border-gray-500/30 text-gray-400";
  }
}

export function MonitorLogs({ monitor, open, onClose, onLoadLogs }: MonitorLogsProps) {
  const [logs, setLogs] = useState<CheckResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && monitor) {
      setLoading(true);
      setError(null);
      onLoadLogs(monitor.id)
        .then(setLogs)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [open, monitor, onLoadLogs]);

  return (
    <Dialog open={open} onOpenChange={(isOpen) => !isOpen && onClose()}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>Logs:</span>
            <span className="text-primary">{monitor?.name}</span>
          </DialogTitle>
        </DialogHeader>

        <div className="flex-1 overflow-auto">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <div className="text-muted-foreground">Loading logs...</div>
            </div>
          )}

          {error && (
            <div className="p-4 text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg">
              {error}
            </div>
          )}

          {!loading && !error && logs.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              No check results yet
            </div>
          )}

          {!loading && !error && logs.length > 0 && (
            <div className="space-y-2">
              {logs.map((log) => (
                <div
                  key={log.id}
                  className={`p-3 rounded-lg border ${getStatusColor(log.status)}`}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className={getStatusColor(log.status)}>
                        {log.status}
                      </Badge>
                      <span className="text-sm font-medium">{log.elapsed_ms.toFixed(0)}ms</span>
                    </div>
                    <span className="text-xs text-muted-foreground">
                      {formatDateTime(log.checked_at)}
                    </span>
                  </div>
                  <div className="mt-2 text-sm text-muted-foreground truncate">
                    {log.message}
                  </div>
                  {log.details && Object.keys(log.details).length > 0 && (
                    <details className="mt-2">
                      <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                        Details
                      </summary>
                      <pre className="mt-2 p-2 text-xs bg-black/20 rounded overflow-auto max-h-32">
                        {JSON.stringify(log.details, null, 2)}
                      </pre>
                    </details>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
