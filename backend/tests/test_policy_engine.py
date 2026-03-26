"""Unit tests for the policy engine."""

import pytest
from datetime import datetime, timezone

from app.services.policy_engine import PolicyEngine, PolicyDocument


def make_engine(policies: list[dict]) -> PolicyEngine:
    return PolicyEngine(policies)


def test_allow_wildcard():
    engine = make_engine([{"effect": "allow", "resources": ["*"], "actions": ["*"]}])
    allowed, reason = engine.evaluate("read", "file:doc.pdf")
    assert allowed is True


def test_deny_explicit():
    engine = make_engine([
        {"effect": "allow", "resources": ["*"], "actions": ["*"]},
        {"effect": "deny", "resources": ["secret:*"], "actions": ["*"]},
    ])
    allowed, reason = engine.evaluate("read", "secret:key")
    assert allowed is False
    assert "deny" in reason.lower()


def test_no_matching_policy_defaults_deny():
    engine = make_engine([
        {"effect": "allow", "resources": ["email:*"], "actions": ["send"]},
    ])
    allowed, reason = engine.evaluate("delete", "file:important")
    assert allowed is False


def test_glob_resource_matching():
    engine = make_engine([
        {"effect": "allow", "resources": ["email:*"], "actions": ["*"]},
    ])
    allowed, _ = engine.evaluate("send", "email:user@example.com")
    assert allowed is True

    allowed, _ = engine.evaluate("send", "file:whatever")
    assert allowed is False


def test_max_daily_condition():
    engine = make_engine([
        {
            "effect": "allow",
            "resources": ["*"],
            "actions": ["*"],
            "conditions": {"max_daily": 5},
        }
    ])
    # Under limit
    allowed, _ = engine.evaluate("read", "file:x", daily_count=4)
    assert allowed is True

    # At limit
    allowed, reason = engine.evaluate("read", "file:x", daily_count=5)
    assert allowed is False
    assert "Daily limit" in reason


def test_time_window_condition():
    engine = make_engine([
        {
            "effect": "allow",
            "resources": ["*"],
            "actions": ["*"],
            "conditions": {"time_window": {"start": "09:00", "end": "17:00"}},
        }
    ])

    in_window = datetime(2026, 3, 26, 12, 0, tzinfo=timezone.utc)
    allowed, _ = engine.evaluate("read", "file:x", current_time=in_window)
    assert allowed is True

    out_of_window = datetime(2026, 3, 26, 22, 0, tzinfo=timezone.utc)
    allowed, reason = engine.evaluate("read", "file:x", current_time=out_of_window)
    assert allowed is False
    assert "time window" in reason.lower()


def test_ip_allowlist_condition():
    engine = make_engine([
        {
            "effect": "allow",
            "resources": ["*"],
            "actions": ["*"],
            "conditions": {"ip_allowlist": ["10.0.0.0/8", "192.168.1.0/24"]},
        }
    ])

    allowed, _ = engine.evaluate("read", "x", ip_address="10.1.2.3")
    assert allowed is True

    allowed, reason = engine.evaluate("read", "x", ip_address="8.8.8.8")
    assert allowed is False
    assert "not in allowlist" in reason


def test_scope_from_jwt():
    scope = {
        "policies": [
            {"effect": "allow", "resources": ["email:*"], "actions": ["read", "send"]},
        ]
    }
    engine = PolicyEngine.from_scope(scope)
    allowed, _ = engine.evaluate("send", "email:hello@test.com")
    assert allowed is True

    allowed, _ = engine.evaluate("delete", "email:hello@test.com")
    assert allowed is False


def test_scope_summary():
    engine = make_engine([
        {"effect": "allow", "resources": ["*"], "actions": ["read"]},
        {"effect": "deny", "resources": ["admin:*"], "actions": ["*"]},
    ])
    summary = engine.get_scope_summary()
    assert summary["policies"] == 2
    assert len(summary["allow_policies"]) == 1
    assert len(summary["deny_policies"]) == 1
