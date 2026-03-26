"use client";

import { useState } from "react";
import { Key, Copy, Eye, EyeOff, RefreshCw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface IssuedToken {
  token: string;
  credential_id: string;
  jti: string;
  expires_at: string;
  scope: object;
}

export default function ApiKeysPage() {
  const [agentId, setAgentId] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [ttl, setTtl] = useState("15");
  const [result, setResult] = useState<IssuedToken | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [showToken, setShowToken] = useState(false);

  async function issueToken() {
    if (!agentId || !apiKey) {
      setError("Agent ID and API key are required");
      return;
    }
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API_URL}/v1/credentials/issue`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": apiKey,
        },
        body: JSON.stringify({ agent_id: agentId, ttl_minutes: parseInt(ttl) }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to issue credential");
      }
      setResult(await res.json());
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Issue Credentials</h1>
        <p className="text-muted-foreground mt-1">
          Issue short-lived JWT credentials for your agents
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Key className="h-4 w-4" />
            Request a Credential
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="agentId">Agent ID</Label>
            <Input
              id="agentId"
              placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
              value={agentId}
              onChange={(e) => setAgentId(e.target.value)}
              className="font-mono text-sm"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="apiKey">Agent API Key</Label>
            <Input
              id="apiKey"
              type="password"
              placeholder="agid_..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="font-mono text-sm"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ttl">TTL (minutes)</Label>
            <Input
              id="ttl"
              type="number"
              min="1"
              max="1440"
              value={ttl}
              onChange={(e) => setTtl(e.target.value)}
              className="w-32"
            />
          </div>
          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}
          <Button onClick={issueToken} disabled={loading}>
            {loading ? (
              <RefreshCw className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Key className="mr-2 h-4 w-4" />
            )}
            Issue Credential
          </Button>
        </CardContent>
      </Card>

      {result && (
        <Card className="border-green-500/30">
          <CardHeader>
            <CardTitle className="text-base text-green-400">Credential Issued</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <Label className="text-xs text-muted-foreground">JWT Token</Label>
              <div className="flex gap-2 mt-1">
                <Input
                  type={showToken ? "text" : "password"}
                  value={result.token}
                  readOnly
                  className="font-mono text-xs"
                />
                <Button variant="ghost" size="icon" onClick={() => setShowToken(!showToken)}>
                  {showToken ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </Button>
                <Button variant="ghost" size="icon" onClick={() => copyToClipboard(result.token)}>
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <p className="text-muted-foreground text-xs">Credential ID</p>
                <p className="font-mono text-xs">{result.credential_id}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">JTI</p>
                <p className="font-mono text-xs truncate">{result.jti}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">Expires At</p>
                <p className="text-xs">{new Date(result.expires_at).toLocaleString()}</p>
              </div>
            </div>
            <div>
              <p className="text-muted-foreground text-xs mb-1">Scope</p>
              <pre className="text-xs bg-muted rounded p-3 overflow-auto max-h-40">
                {JSON.stringify(result.scope, null, 2)}
              </pre>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
