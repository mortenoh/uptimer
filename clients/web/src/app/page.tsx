"use client";

import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { Monitor, MonitorCreate, CheckResult } from "@/types/api";
import { LoginForm } from "@/components/login-form";
import { Dashboard } from "@/components/dashboard";

export default function Home() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [tags, setTags] = useState<string[]>([]);
  const [selectedTag, setSelectedTag] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Check auth on mount
  useEffect(() => {
    setIsAuthenticated(api.isAuthenticated());
    setIsLoading(false);
  }, []);

  // Load data when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      loadData();
    }
  }, [isAuthenticated, selectedTag]);

  async function loadData() {
    try {
      setError(null);
      const [monitorsData, tagsData] = await Promise.all([
        api.listMonitors(selectedTag || undefined),
        api.listTags(),
      ]);
      setMonitors(monitorsData);
      setTags(tagsData);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        api.clearAuth();
        setIsAuthenticated(false);
      } else {
        setError(err instanceof Error ? err.message : "Failed to load data");
      }
    }
  }

  function handleLogin(username: string, password: string) {
    api.setAuth(username, password);
    setIsAuthenticated(true);
  }

  function handleLogout() {
    api.clearAuth();
    setIsAuthenticated(false);
    setMonitors([]);
    setTags([]);
  }

  async function handleRunCheck(monitorId: string): Promise<CheckResult | null> {
    try {
      const result = await api.runCheck(monitorId);
      await loadData(); // Refresh monitor status
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Check failed");
      return null;
    }
  }

  async function handleRunAllChecks() {
    try {
      await api.runAllChecks(selectedTag || undefined);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Checks failed");
    }
  }

  async function handleDeleteMonitor(id: string) {
    try {
      await api.deleteMonitor(id);
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  }

  async function handleToggleMonitor(id: string, enabled: boolean) {
    try {
      await api.updateMonitor(id, { enabled });
      await loadData();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Update failed");
    }
  }

  async function handleLoadLogs(monitorId: string): Promise<CheckResult[]> {
    return api.getResults(monitorId, 50);
  }

  async function handleAddMonitor(data: MonitorCreate): Promise<void> {
    await api.createMonitor(data);
    await loadData();
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <div className="text-muted-foreground">Loading...</div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginForm onLogin={handleLogin} />;
  }

  return (
    <Dashboard
      monitors={monitors}
      tags={tags}
      selectedTag={selectedTag}
      error={error}
      onSelectTag={setSelectedTag}
      onLogout={handleLogout}
      onRefresh={loadData}
      onRunCheck={handleRunCheck}
      onRunAllChecks={handleRunAllChecks}
      onDeleteMonitor={handleDeleteMonitor}
      onToggleMonitor={handleToggleMonitor}
      onLoadLogs={handleLoadLogs}
      onAddMonitor={handleAddMonitor}
    />
  );
}
