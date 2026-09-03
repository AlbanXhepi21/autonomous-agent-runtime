"""Tenant organizations ("workspaces") and memberships.

Deliberately a new top-level package rather than an extension of
``app.environment.workspace`` -- that module is the agent's sandboxed
*filesystem root* and is unrelated to the tenant boundary here, despite
sharing the word "workspace". The DB-level ``workspace_id`` columns already
present on ``data_sources``/``saved_reports``/``scheduled_reports`` are what
this package formalizes into a real table; nothing in this phase touches
those existing columns, and nothing here is wired into conversations, runs,
or artifacts yet.

Like ``app.identity``, this package describes what it consumes via
contracts and never imports ``app.agent`` or ``app.security`` -- the latter
governs a different kind of "permission" (agent tool capability, not
workspace role), and the two must never be conflated.
"""
