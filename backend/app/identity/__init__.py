"""User identity, authentication, sessions, and recovery/verification tokens.

Deliberately separate from ``app.security``, which governs what an agent tool
call may do at runtime (filesystem writes, command execution) -- an unrelated
kind of "permission" that this package must never be confused with. This
package describes what it consumes via contracts and never imports
``app.agent``, following the same discipline already enforced for
``app.llm``, ``app.security`` and ``app.memory``.
"""
