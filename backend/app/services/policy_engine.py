"""
Policy Engine — evaluates JSON policy documents against requested actions.

Policy Document Schema:
{
  "effect": "allow" | "deny",          # default: "allow"
  "resources": ["email:*", "file:*"],  # glob-style resource matching
  "actions": ["read", "send", "*"],    # action matching
  "conditions": {                       # optional
    "max_daily": 100,                  # max actions per day
    "time_window": {                   # UTC time window
      "start": "09:00",
      "end": "17:00"
    },
    "ip_allowlist": ["10.0.0.0/8"],   # CIDR ranges
    "require_2fa": false
  }
}
"""

import fnmatch
import ipaddress
import json
from datetime import datetime, timezone
from typing import Any


class PolicyViolation(Exception):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


class PolicyDocument:
    def __init__(self, doc: dict):
        self.effect: str = doc.get("effect", "allow")
        self.resources: list[str] = doc.get("resources", ["*"])
        self.actions: list[str] = doc.get("actions", ["*"])
        self.conditions: dict[str, Any] = doc.get("conditions", {})

    @classmethod
    def from_json(cls, json_str: str) -> "PolicyDocument":
        return cls(json.loads(json_str))

    def matches_resource(self, resource: str) -> bool:
        return any(fnmatch.fnmatch(resource, pattern) for pattern in self.resources)

    def matches_action(self, action: str) -> bool:
        return any(fnmatch.fnmatch(action, pattern) for pattern in self.actions)

    def check_conditions(
        self,
        *,
        daily_count: int = 0,
        ip_address: str | None = None,
        current_time: datetime | None = None,
    ) -> tuple[bool, str]:
        """Returns (is_allowed, reason)."""
        if current_time is None:
            current_time = datetime.now(timezone.utc)

        # max_daily check
        max_daily = self.conditions.get("max_daily")
        if max_daily is not None and daily_count >= max_daily:
            return False, f"Daily limit of {max_daily} actions exceeded ({daily_count} used)"

        # time_window check
        time_window = self.conditions.get("time_window")
        if time_window:
            start_str = time_window.get("start", "00:00")
            end_str = time_window.get("end", "23:59")
            current_hm = current_time.strftime("%H:%M")
            if not (start_str <= current_hm <= end_str):
                return False, f"Action outside allowed time window ({start_str}-{end_str} UTC)"

        # ip_allowlist check
        ip_allowlist = self.conditions.get("ip_allowlist")
        if ip_allowlist and ip_address:
            try:
                client_ip = ipaddress.ip_address(ip_address)
                allowed = any(
                    client_ip in ipaddress.ip_network(cidr, strict=False)
                    for cidr in ip_allowlist
                )
                if not allowed:
                    return False, f"IP address {ip_address} not in allowlist"
            except ValueError:
                return False, f"Invalid IP address format: {ip_address}"

        return True, "ok"


class PolicyEngine:
    def __init__(self, policies: list[dict]):
        """policies: list of raw policy dicts (from DB), sorted by priority desc."""
        self._policies = [PolicyDocument(p) for p in policies]

    @classmethod
    def from_scope(cls, scope: dict) -> "PolicyEngine":
        """Build engine from JWT scope (list of policy dicts)."""
        policies = scope.get("policies", [])
        return cls(policies)

    def evaluate(
        self,
        action: str,
        resource: str,
        *,
        daily_count: int = 0,
        ip_address: str | None = None,
        current_time: datetime | None = None,
    ) -> tuple[bool, str]:
        """
        Evaluate all policies. Returns (is_allowed, reason).
        - Explicit deny always wins.
        - At least one allow must match.
        - If no policy matches, default DENY.
        """
        matched_allow = False
        explicit_deny = False
        deny_reason = "No matching policy found — default deny"

        for policy in self._policies:
            if not policy.matches_resource(resource):
                continue
            if not policy.matches_action(action):
                continue

            # Check conditions
            ok, reason = policy.check_conditions(
                daily_count=daily_count,
                ip_address=ip_address,
                current_time=current_time,
            )

            if policy.effect == "deny":
                if ok:
                    explicit_deny = True
                    deny_reason = f"Explicit deny policy matched: {reason if reason != 'ok' else 'policy denied this action'}"
                    break
            elif policy.effect == "allow":
                if ok:
                    matched_allow = True
                else:
                    deny_reason = reason

        if explicit_deny:
            return False, deny_reason
        if matched_allow:
            return True, "allowed"
        return False, deny_reason

    def get_scope_summary(self) -> dict:
        """Return human-readable scope summary."""
        return {
            "policies": len(self._policies),
            "allow_policies": [
                {"resources": p.resources, "actions": p.actions}
                for p in self._policies
                if p.effect == "allow"
            ],
            "deny_policies": [
                {"resources": p.resources, "actions": p.actions}
                for p in self._policies
                if p.effect == "deny"
            ],
        }


def build_default_policy(resources: list[str], actions: list[str]) -> dict:
    """Helper to build a simple allow policy."""
    return {
        "effect": "allow",
        "resources": resources,
        "actions": actions,
        "conditions": {},
    }
