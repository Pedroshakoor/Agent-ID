"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Copy, Shield } from "lucide-react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (agent: Record<string, unknown>) => void;
}

export function RegisterAgentDialog({ open, onOpenChange, onCreated }: Props) {
  const [form, setForm] = useState({
    name: "",
    owner_id: "",
    description: "",
    framework: "",
  });
  const [result, setResult] = useState<{ api_key: string; id: string } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function reset() {
    setForm({ name: "", owner_id: "", description: "", framework: "" });
    setResult(null);
    setError(null);
  }

  async function submit() {
    if (!form.name || !form.owner_id) {
      setError("Name and Owner ID are required");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/v1/agents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: form.name,
          owner_id: form.owner_id,
          description: form.description || undefined,
          framework: form.framework || undefined,
        }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Registration failed");
      }
      const data = await res.json();
      setResult({ api_key: data.api_key, id: data.id });
      onCreated(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) reset(); onOpenChange(o); }}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Register Agent
          </DialogTitle>
          <DialogDescription>
            Register a new AI agent to receive a verifiable identity and API key.
          </DialogDescription>
        </DialogHeader>

        {!result ? (
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="name">Agent Name *</Label>
              <Input
                id="name"
                placeholder="my-langchain-agent"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="owner_id">Owner ID *</Label>
              <Input
                id="owner_id"
                placeholder="user-123 or org-abc"
                value={form.owner_id}
                onChange={(e) => setForm({ ...form, owner_id: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                placeholder="What does this agent do?"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="framework">Framework</Label>
              <Input
                id="framework"
                placeholder="langchain, crewai, autogen..."
                value={form.framework}
                onChange={(e) => setForm({ ...form, framework: e.target.value })}
              />
            </div>
            {error && <p className="text-sm text-destructive">{error}</p>}
            <Button onClick={submit} disabled={loading} className="w-full">
              {loading ? "Registering..." : "Register Agent"}
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="rounded-lg bg-green-500/10 border border-green-500/30 p-4 space-y-2">
              <p className="text-sm font-medium text-green-400">Agent registered successfully!</p>
              <p className="text-xs text-muted-foreground">
                Save your API key — it will only be shown once.
              </p>
            </div>
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">Agent ID</Label>
              <div className="flex gap-2">
                <Input value={result.id} readOnly className="font-mono text-xs" />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => navigator.clipboard.writeText(result.id)}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <div className="space-y-2">
              <Label className="text-xs text-muted-foreground">API Key (save this!)</Label>
              <div className="flex gap-2">
                <Input value={result.api_key} readOnly className="font-mono text-xs" />
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => navigator.clipboard.writeText(result.api_key)}
                >
                  <Copy className="h-4 w-4" />
                </Button>
              </div>
            </div>
            <Button
              onClick={() => { reset(); onOpenChange(false); }}
              variant="outline"
              className="w-full"
            >
              Done
            </Button>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
