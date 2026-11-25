"""Tier-2 (destructive) plan->execute confirmation tokens.

A destructive operation is a two-step dance for both humans and LLM callers:
  1) POST .../plan           -> returns {token, expires_in, literal, summary, risks}
  2) POST .../execute {token, literal}  -> runs it, once, if the token is fresh and the
     caller echoes back the exact literal confirmation string.
This is the API equivalent of typing a literal phrase into a danger-zone dialog. Tokens
are single-use, short-lived, and never auto-retried on failure.
"""
from __future__ import annotations

import secrets
import time
from dataclasses import dataclass

TTL = 120.0  # seconds


@dataclass
class Plan:
    token: str
    literal: str
    op: str
    created: float
    payload: dict
    min_delay: float = 0.0  # mandatory server-enforced cooldown before execute (seconds)


class Tier2Registry:
    def __init__(self):
        self._plans: dict[str, Plan] = {}

    def plan(self, op: str, literal: str, payload: dict | None = None,
             min_delay_seconds: float = 0.0) -> dict:
        self._gc()
        token = secrets.token_urlsafe(18)
        min_delay = max(0.0, float(min_delay_seconds))
        self._plans[token] = Plan(token, literal, op, time.monotonic(), payload or {}, min_delay)
        out = {"token": token, "literal": literal, "op": op,
               "expires_in": int(TTL), "confirm_how": f"echo literal '{literal}' with this token"}
        if min_delay > 0:
            # Advertised so clients (and LLM callers reading this response) know the
            # execute WILL be refused server-side until the cooldown elapses.
            out["min_delay_seconds"] = min_delay
        return out

    def take(self, op: str, token: str, literal: str) -> Plan:
        self._gc()
        plan = self._plans.get(token)
        if plan is None:
            raise KeyError("unknown or expired token - request a fresh plan")
        if plan.op != op:
            raise KeyError(f"token is for op '{plan.op}', not '{op}'")
        # Mandatory cooldown: enforced BEFORE the literal check and BEFORE the token is
        # consumed, so an early attempt neither executes nor burns the token (the caller
        # can retry once the delay elapses, within the TTL window).
        remaining = plan.min_delay - (time.monotonic() - plan.created)
        if remaining > 0:
            raise ValueError(f"cooldown not elapsed: {remaining:.1f}s remaining of the "
                             f"{plan.min_delay:.0f}s mandatory delay before execute")
        if literal != plan.literal:
            raise ValueError(f"literal confirmation mismatch (expected exactly: {plan.literal})")
        del self._plans[token]  # single use
        return plan

    def _gc(self) -> None:
        now = time.monotonic()
        for tok in [t for t, p in self._plans.items() if now - p.created > TTL]:
            self._plans.pop(tok, None)


REGISTRY = Tier2Registry()
