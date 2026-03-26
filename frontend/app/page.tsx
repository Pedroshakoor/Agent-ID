import { Shield, Activity, Key, FileText } from "lucide-react";
import { StatCard } from "@/components/stat-card";
import { RecentActivity } from "@/components/recent-activity";

async function getStats() {
  const apiUrl = process.env.API_URL || "http://localhost:8000";
  try {
    const [agentsRes, logsRes] = await Promise.all([
      fetch(`${apiUrl}/v1/agents?limit=200`, { cache: "no-store" }),
      fetch(`${apiUrl}/v1/audit/logs?limit=10`, { cache: "no-store" }),
    ]);
    const agents = agentsRes.ok ? await agentsRes.json() : [];
    const logs = logsRes.ok ? await logsRes.json() : [];
    return { agents, logs };
  } catch {
    return { agents: [], logs: [] };
  }
}

export default async function DashboardPage() {
  const { agents, logs } = await getStats();

  const activeAgents = agents.filter((a: { status: string }) => a.status === "active").length;
  const totalActions = logs.length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Verifiable identity for every AI agent
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <StatCard
          title="Total Agents"
          value={agents.length}
          description="Registered agents"
          icon={<Shield className="h-4 w-4 text-muted-foreground" />}
        />
        <StatCard
          title="Active Agents"
          value={activeAgents}
          description="Currently active"
          icon={<Activity className="h-4 w-4 text-muted-foreground" />}
        />
        <StatCard
          title="Credentials Issued"
          value="—"
          description="All time"
          icon={<Key className="h-4 w-4 text-muted-foreground" />}
        />
        <StatCard
          title="Recent Actions"
          value={totalActions}
          description="Last 10 logged"
          icon={<FileText className="h-4 w-4 text-muted-foreground" />}
        />
      </div>

      <RecentActivity logs={logs} />
    </div>
  );
}
