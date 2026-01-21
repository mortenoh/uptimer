"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import type { Stage, StageInfo, StageOption } from "@/types/api";
import { api } from "@/lib/api";

interface StageConfigProps {
  stage: Stage;
  stageInfo: StageInfo | undefined;
  onChange: (stage: Stage) => void;
}

function StageConfig({ stage, stageInfo, onChange }: StageConfigProps) {
  if (!stageInfo?.options.length) {
    return null;
  }

  function handleOptionChange(optionName: string, value: unknown) {
    onChange({ ...stage, [optionName]: value });
  }

  return (
    <div className="space-y-3 pt-2">
      {stageInfo.options.map((option) => (
        <div key={option.name} className="space-y-1">
          <label className="text-xs font-medium text-muted-foreground flex items-center gap-1">
            {option.label}
            {option.required && <span className="text-red-400">*</span>}
          </label>
          {option.type === "boolean" ? (
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={Boolean(stage[option.name as keyof Stage])}
                onChange={(e) => handleOptionChange(option.name, e.target.checked)}
                className="rounded"
              />
              <span className="text-xs text-muted-foreground">{option.description}</span>
            </label>
          ) : option.type === "number" ? (
            <input
              type="number"
              value={(stage[option.name as keyof Stage] as number) ?? option.default ?? ""}
              onChange={(e) => {
                const val = e.target.value;
                handleOptionChange(option.name, val === "" ? undefined : parseFloat(val));
              }}
              placeholder={option.placeholder || option.description}
              className="w-full px-2 py-1.5 text-sm rounded-md bg-muted/50 border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            />
          ) : option.type === "object" ? (
            <textarea
              value={
                typeof stage[option.name as keyof Stage] === "object"
                  ? JSON.stringify(stage[option.name as keyof Stage], null, 2)
                  : (stage[option.name as keyof Stage] as string) ?? ""
              }
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  handleOptionChange(option.name, parsed);
                } catch {
                  // Keep raw value for editing
                }
              }}
              placeholder={option.placeholder || option.description}
              rows={3}
              className="w-full px-2 py-1.5 text-sm font-mono rounded-md bg-muted/50 border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none resize-none"
            />
          ) : (
            <input
              type="text"
              value={(stage[option.name as keyof Stage] as string) ?? ""}
              onChange={(e) => handleOptionChange(option.name, e.target.value || undefined)}
              placeholder={option.placeholder || option.description}
              className="w-full px-2 py-1.5 text-sm rounded-md bg-muted/50 border border-border focus:border-primary focus:ring-1 focus:ring-primary outline-none"
            />
          )}
          {option.description && option.type !== "boolean" && (
            <p className="text-xs text-muted-foreground">{option.description}</p>
          )}
        </div>
      ))}
    </div>
  );
}

interface PipelineBuilderProps {
  pipeline: Stage[];
  onChange: (pipeline: Stage[]) => void;
}

export function PipelineBuilder({ pipeline, onChange }: PipelineBuilderProps) {
  const [stageInfos, setStageInfos] = useState<StageInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedStage, setExpandedStage] = useState<number | null>(null);

  useEffect(() => {
    async function fetchStages() {
      try {
        const stages = await api.listStages();
        setStageInfos(stages);
      } catch (error) {
        console.error("Failed to fetch stages:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchStages();
  }, []);

  function getStageInfo(type: string): StageInfo | undefined {
    return stageInfos.find((s) => s.type === type);
  }

  function addStage(type: string) {
    const newStage: Stage = { type };
    onChange([...pipeline, newStage]);
    setExpandedStage(pipeline.length);
  }

  function removeStage(index: number) {
    const updated = pipeline.filter((_, i) => i !== index);
    onChange(updated);
    if (expandedStage === index) {
      setExpandedStage(null);
    } else if (expandedStage !== null && expandedStage > index) {
      setExpandedStage(expandedStage - 1);
    }
  }

  function updateStage(index: number, stage: Stage) {
    const updated = [...pipeline];
    updated[index] = stage;
    onChange(updated);
  }

  function moveStage(index: number, direction: "up" | "down") {
    const newIndex = direction === "up" ? index - 1 : index + 1;
    if (newIndex < 0 || newIndex >= pipeline.length) return;

    const updated = [...pipeline];
    [updated[index], updated[newIndex]] = [updated[newIndex], updated[index]];
    onChange(updated);

    if (expandedStage === index) {
      setExpandedStage(newIndex);
    } else if (expandedStage === newIndex) {
      setExpandedStage(index);
    }
  }

  if (loading) {
    return <div className="text-sm text-muted-foreground">Loading stages...</div>;
  }

  // Group stages by network vs transform
  const networkStages = stageInfos.filter((s) => s.is_network_stage);
  const transformStages = stageInfos.filter((s) => !s.is_network_stage);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium">Pipeline Stages</label>
        <span className="text-xs text-muted-foreground">{pipeline.length} stage{pipeline.length !== 1 ? "s" : ""}</span>
      </div>

      {/* Current pipeline */}
      {pipeline.length > 0 ? (
        <div className="space-y-2">
          {pipeline.map((stage, index) => {
            const info = getStageInfo(stage.type);
            const isExpanded = expandedStage === index;
            const hasOptions = info?.options && info.options.length > 0;

            return (
              <div
                key={index}
                className="border border-border rounded-lg bg-muted/30 overflow-hidden"
              >
                {/* Stage header */}
                <div className="flex items-center gap-2 p-2">
                  <span className="text-xs font-mono text-muted-foreground w-5">{index + 1}.</span>

                  <button
                    type="button"
                    onClick={() => hasOptions && setExpandedStage(isExpanded ? null : index)}
                    className={`flex-1 flex items-center gap-2 text-left ${hasOptions ? "cursor-pointer" : "cursor-default"}`}
                  >
                    <Badge
                      variant={info?.is_network_stage ? "default" : "secondary"}
                      className="text-xs"
                    >
                      {info?.name || stage.type}
                    </Badge>
                    {hasOptions && (
                      <svg
                        className={`h-3 w-3 text-muted-foreground transition-transform ${isExpanded ? "rotate-180" : ""}`}
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    )}
                  </button>

                  {/* Move buttons */}
                  <div className="flex gap-0.5">
                    <button
                      type="button"
                      onClick={() => moveStage(index, "up")}
                      disabled={index === 0}
                      className="p-1 text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
                      title="Move up"
                    >
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                      </svg>
                    </button>
                    <button
                      type="button"
                      onClick={() => moveStage(index, "down")}
                      disabled={index === pipeline.length - 1}
                      className="p-1 text-muted-foreground hover:text-foreground disabled:opacity-30 disabled:cursor-not-allowed"
                      title="Move down"
                    >
                      <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                      </svg>
                    </button>
                  </div>

                  {/* Remove button */}
                  <button
                    type="button"
                    onClick={() => removeStage(index)}
                    className="p-1 text-muted-foreground hover:text-red-400"
                    title="Remove stage"
                  >
                    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                {/* Stage configuration */}
                {isExpanded && hasOptions && (
                  <div className="px-3 pb-3 border-t border-border">
                    <StageConfig
                      stage={stage}
                      stageInfo={info}
                      onChange={(updated) => updateStage(index, updated)}
                    />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground py-2">No stages yet. Add a stage to start building your pipeline.</p>
      )}

      {/* Add stage section */}
      <div className="space-y-2 pt-2 border-t border-border">
        <p className="text-xs font-medium text-muted-foreground">Add Stage</p>

        {/* Network stages */}
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">Network</p>
          <div className="flex flex-wrap gap-1.5">
            {networkStages.map((stage) => (
              <Button
                key={stage.type}
                type="button"
                variant="outline"
                size="sm"
                onClick={() => addStage(stage.type)}
                className="h-7 text-xs"
                title={stage.description}
              >
                + {stage.name}
              </Button>
            ))}
          </div>
        </div>

        {/* Transform stages */}
        <div className="space-y-1">
          <p className="text-xs text-muted-foreground">Transform / Validate</p>
          <div className="flex flex-wrap gap-1.5">
            {transformStages.map((stage) => (
              <Button
                key={stage.type}
                type="button"
                variant="outline"
                size="sm"
                onClick={() => addStage(stage.type)}
                className="h-7 text-xs"
                title={stage.description}
              >
                + {stage.name}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
