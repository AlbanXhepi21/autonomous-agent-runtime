"""Types shared between the runtime and the packages it drives.

Nothing here may import from another ``app`` package except ``app.core``. That
constraint is what lets ``llm``, ``security`` and ``memory`` describe what they
consume without importing the runtime that consumes them, which would otherwise
make each of those packages impossible to test or extract on its own.
"""
