---
name: aiogram catch-all handlers must scope to default_state
description: Unscoped text/regex handlers in aiogram routers can silently intercept input meant for other FSM flows, causing "no response" bugs.
---

In aiogram 3, dispatcher matches handlers across all included routers in registration order — it does NOT prioritize handlers whose state filter matches the current FSM state over handlers from an earlier-registered router that have no state filter at all.

A broad/catch-all filter (e.g. `F.text.regexp(...)` with no state condition) registered in a router that is `include_router`'d before another router will intercept matching messages system-wide, even while a user is mid-flow in an unrelated FSM state (e.g. admin add-card flow, broadcast text entry, etc). The result looks like total silence: the intended handler never runs, and the catch-all handler often does a lookup that finds nothing and returns without replying.

**Why:** Hit this exact bug — a "lookup service by pasted link/uuid" handler with a bare regex filter (`^[A-Za-z0-9\-_:/.]{6,}$`, no state scoping) was silently swallowing admin card numbers typed during the "add card" FSM flow, because its router was registered earlier in `main.py`.

**How to apply:** Any handler meant only for the "no active flow" case must explicitly filter on `default_state` (import from `aiogram.fsm.state`), e.g. `@router.message(default_state, F.text.regexp(...))`. Audit any other broad text/regexp filters the same way — grep for `@router.message(F.text` (or `F.photo`) calls with no state argument in codebases with many FSM flows.
