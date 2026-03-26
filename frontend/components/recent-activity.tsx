import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle, XCircle, AlertCircle } from "lucide-react";

interface Log {
  id: string;
  agent_id: string;
  action: string;
  result: string;
  created_at: string;
}

const ResultIcon = ({ result }: { result: string }) => {
  if (result === "allowed") return <CheckCircle className="h-3 w-3 text-green-400 shrink-0" />;
  if (result === "denied") return <XCircle className="h-3 w-3 text-red-400 shrink-0" />;
  return <AlertCircle className="h-3 w-3 text-yellow-400 shrink-0" />;
};

export function RecentActivity({ logs }: { logs: Log[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Recent Agent Activity</CardTitle>
      </CardHeader>
      <CardContent>
        {logs.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-8">
            No activity logged yet. Agents will appear here as they take actions.
          </p>
        ) : (
          <div className="space-y-2">
            {logs.map((log) => (
              <div key={log.id} className="flex items-center gap-3 text-sm py-1">
                <ResultIcon result={log.result} />
                <span className="font-mono text-xs text-muted-foreground w-28 truncate">
                  {log.agent_id.slice(0, 8)}...
                </span>
                <span className="font-mono text-xs flex-1">{log.action}</span>
                <span className="text-xs text-muted-foreground">
                  {new Date(log.created_at).toLocaleTimeString()}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
