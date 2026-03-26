"use client";

import { useState, useEffect } from "react";
import { FileText, CheckCircle, XCircle, AlertCircle } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";

interface AuditLog {
  id: string;
  agent_id: string;
  action: string;
  resource?: string;
  result: "allowed" | "denied" | "error";
  tool_called?: string;
  prompt_snippet?: string;
  result_summary?: string;
  cost_usd?: number;
  duration_ms?: number;
  created_at: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const ResultIcon = ({ result }: { result: string }) => {
  if (result === "allowed") return <CheckCircle className="h-4 w-4 text-green-400" />;
  if (result === "denied") return <XCircle className="h-4 w-4 text-red-400" />;
  return <AlertCircle className="h-4 w-4 text-yellow-400" />;
};

const resultBadgeClass = {
  allowed: "bg-green-500/20 text-green-400 border-green-500/30",
  denied: "bg-red-500/20 text-red-400 border-red-500/30",
  error: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
} as const;

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [agentFilter, setAgentFilter] = useState("");

  useEffect(() => {
    async function fetchLogs() {
      try {
        const params = new URLSearchParams({ limit: "100" });
        if (agentFilter) params.set("agent_id", agentFilter);
        const res = await fetch(`${API_URL}/v1/audit/logs?${params}`);
        if (res.ok) setLogs(await res.json());
      } finally {
        setLoading(false);
      }
    }
    fetchLogs();
  }, [agentFilter]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Audit Logs</h1>
        <p className="text-muted-foreground mt-1">
          Every action performed by every agent, with full context
        </p>
      </div>

      <div className="flex gap-3">
        <Input
          placeholder="Filter by agent ID..."
          value={agentFilter}
          onChange={(e) => setAgentFilter(e.target.value)}
          className="max-w-sm"
        />
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40 text-muted-foreground">
          Loading audit logs...
        </div>
      ) : logs.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 space-y-4">
            <FileText className="h-12 w-12 text-muted-foreground/50" />
            <div className="text-center">
              <p className="font-medium">No audit logs yet</p>
              <p className="text-sm text-muted-foreground mt-1">
                Actions will appear here as agents use their credentials
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {logs.map((log) => (
            <Card key={log.id} className="hover:border-primary/30 transition-colors">
              <CardContent className="py-3 px-4">
                <div className="flex items-start gap-3">
                  <ResultIcon result={log.result} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="font-mono text-sm font-medium">{log.action}</span>
                      {log.resource && (
                        <span className="text-xs text-muted-foreground truncate max-w-xs">
                          → {log.resource}
                        </span>
                      )}
                      <Badge
                        variant="outline"
                        className={`text-xs ${resultBadgeClass[log.result]}`}
                      >
                        {log.result}
                      </Badge>
                      {log.tool_called && (
                        <Badge variant="secondary" className="text-xs">
                          {log.tool_called}
                        </Badge>
                      )}
                    </div>
                    <div className="flex items-center gap-4 mt-1 text-xs text-muted-foreground">
                      <span className="font-mono truncate max-w-[140px]">{log.agent_id}</span>
                      {log.cost_usd != null && (
                        <span>${log.cost_usd.toFixed(6)}</span>
                      )}
                      {log.duration_ms != null && (
                        <span>{log.duration_ms}ms</span>
                      )}
                      <span>{new Date(log.created_at).toLocaleString()}</span>
                    </div>
                    {log.prompt_snippet && (
                      <p className="text-xs text-muted-foreground mt-1 italic truncate">
                        "{log.prompt_snippet}"
                      </p>
                    )}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
