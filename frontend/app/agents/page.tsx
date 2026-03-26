"use client";

import { useState, useEffect } from "react";
import { Plus, Shield, Trash2, ExternalLink } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { RegisterAgentDialog } from "@/components/register-agent-dialog";

interface Agent {
  id: string;
  name: string;
  owner_id: string;
  status: string;
  description?: string;
  framework?: string;
  created_at: string;
  last_active_at?: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);

  async function fetchAgents() {
    try {
      const res = await fetch(`${API_URL}/v1/agents?limit=100`);
      if (res.ok) setAgents(await res.json());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchAgents();
  }, []);

  const statusColor = {
    active: "bg-green-500/20 text-green-400 border-green-500/30",
    suspended: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
    revoked: "bg-red-500/20 text-red-400 border-red-500/30",
  } as const;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground mt-1">
            Manage registered AI agents and their identities
          </p>
        </div>
        <Button onClick={() => setDialogOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Register Agent
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-40 text-muted-foreground">
          Loading agents...
        </div>
      ) : agents.length === 0 ? (
        <Card className="border-dashed">
          <CardContent className="flex flex-col items-center justify-center py-16 space-y-4">
            <Shield className="h-12 w-12 text-muted-foreground/50" />
            <div className="text-center">
              <p className="font-medium">No agents registered yet</p>
              <p className="text-sm text-muted-foreground mt-1">
                Register your first agent to get started
              </p>
            </div>
            <Button onClick={() => setDialogOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Register Agent
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {agents.map((agent) => (
            <Card key={agent.id} className="hover:border-primary/50 transition-colors">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-base font-semibold">{agent.name}</CardTitle>
                  <Badge
                    variant="outline"
                    className={statusColor[agent.status as keyof typeof statusColor]}
                  >
                    {agent.status}
                  </Badge>
                </div>
                {agent.description && (
                  <p className="text-sm text-muted-foreground">{agent.description}</p>
                )}
              </CardHeader>
              <CardContent className="space-y-2 text-sm">
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Owner</span>
                  <span className="font-mono text-xs">{agent.owner_id}</span>
                </div>
                {agent.framework && (
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span>Framework</span>
                    <Badge variant="secondary" className="text-xs">{agent.framework}</Badge>
                  </div>
                )}
                <div className="flex items-center justify-between text-muted-foreground">
                  <span>Registered</span>
                  <span>{new Date(agent.created_at).toLocaleDateString()}</span>
                </div>
                {agent.last_active_at && (
                  <div className="flex items-center justify-between text-muted-foreground">
                    <span>Last active</span>
                    <span>{new Date(agent.last_active_at).toLocaleString()}</span>
                  </div>
                )}
                <div className="pt-2">
                  <code className="text-xs text-muted-foreground font-mono bg-muted px-2 py-1 rounded block truncate">
                    {agent.id}
                  </code>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      <RegisterAgentDialog
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onCreated={(agent) => {
          setAgents((prev) => [agent as unknown as Agent, ...prev]);
        }}
      />
    </div>
  );
}
