"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { PipelineBuilder } from "@/components/pipeline-builder";
import type { MonitorCreate, Stage } from "@/types/api";

interface AddMonitorDialogProps {
  open: boolean;
  onClose: () => void;
  onAdd: (data: MonitorCreate) => Promise<void>;
}

const COMMON_SCHEDULES = [
  { label: "Every minute", value: "* * * * *" },
  { label: "Every 5 min", value: "*/5 * * * *" },
  { label: "Every 15 min", value: "*/15 * * * *" },
  { label: "Every hour", value: "0 * * * *" },
  { label: "Every 6 hours", value: "0 */6 * * *" },
  { label: "Daily 9am", value: "0 9 * * *" },
  { label: "Weekdays 9am", value: "0 9 * * 1-5" },
];

export function AddMonitorDialog({ open, onClose, onAdd }: AddMonitorDialogProps) {
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [interval, setInterval] = useState(30);
  const [schedule, setSchedule] = useState("");
  const [tags, setTags] = useState("");
  const [pipeline, setPipeline] = useState<Stage[]>([{ type: "http" }]);
  const [useSchedule, setUseSchedule] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function reset() {
    setName("");
    setUrl("");
    setInterval(30);
    setSchedule("");
    setTags("");
    setPipeline([{ type: "http" }]);
    setUseSchedule(false);
    setError(null);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);

    if (!name.trim() || !url.trim()) {
      setError("Name and URL are required");
      return;
    }

    if (pipeline.length === 0) {
      setError("At least one pipeline stage is required");
      return;
    }

    setIsSubmitting(true);
    try {
      const data: MonitorCreate = {
        name: name.trim(),
        url: url.trim(),
        pipeline,
        interval,
        tags: tags.split(",").map(t => t.trim()).filter(Boolean),
      };

      if (useSchedule && schedule) {
        data.schedule = schedule;
      }

      await onAdd(data);
      reset();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create monitor");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(isOpen) => { if (!isOpen) { reset(); onClose(); } }}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Add Monitor</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="p-3 text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg">
              {error}
            </div>
          )}

          {/* Name */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Service"
              className="w-full px-3 py-2 rounded-md bg-muted/50 border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            />
          </div>

          {/* URL */}
          <div className="space-y-2">
            <label className="text-sm font-medium">URL</label>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://example.com"
              className="w-full px-3 py-2 rounded-md bg-muted/50 border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            />
          </div>

          {/* Tags */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Tags (comma separated)</label>
            <input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="production, api, critical"
              className="w-full px-3 py-2 rounded-md bg-muted/50 border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            />
          </div>

          {/* Pipeline Builder */}
          <PipelineBuilder pipeline={pipeline} onChange={setPipeline} />

          {/* Schedule Toggle */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="useSchedule"
              checked={useSchedule}
              onChange={(e) => setUseSchedule(e.target.checked)}
              className="rounded"
            />
            <label htmlFor="useSchedule" className="text-sm font-medium">
              Use cron schedule instead of interval
            </label>
          </div>

          {/* Interval or Schedule */}
          {useSchedule ? (
            <div className="space-y-2">
              <label className="text-sm font-medium">Cron Schedule</label>
              <input
                type="text"
                value={schedule}
                onChange={(e) => setSchedule(e.target.value)}
                placeholder="*/5 * * * *"
                className="w-full px-3 py-2 rounded-md bg-muted/50 border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none font-mono"
              />
              <div className="flex flex-wrap gap-1.5 mt-2">
                {COMMON_SCHEDULES.map((s) => (
                  <Badge
                    key={s.value}
                    variant={schedule === s.value ? "default" : "outline"}
                    className="cursor-pointer text-xs"
                    onClick={() => setSchedule(s.value)}
                  >
                    {s.label}
                  </Badge>
                ))}
              </div>
              <p className="text-xs text-muted-foreground mt-1">
                Format: minute hour day month weekday
              </p>
            </div>
          ) : (
            <div className="space-y-2">
              <label className="text-sm font-medium">Check Interval (seconds)</label>
              <input
                type="number"
                value={interval}
                onChange={(e) => setInterval(parseInt(e.target.value) || 30)}
                min={10}
                className="w-full px-3 py-2 rounded-md bg-muted/50 border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none"
              />
              <p className="text-xs text-muted-foreground">Minimum: 10 seconds</p>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => { reset(); onClose(); }} className="flex-1">
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting} className="flex-1">
              {isSubmitting ? "Creating..." : "Create Monitor"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
