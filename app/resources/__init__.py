"""Filesystem assets the runtime reads: specialist and skill definitions.

These are content, not code. Keeping them out of the Python packages that read
them is what lets a registry point at a directory instead of climbing out of
its own package to find a sibling.
"""


from pathlib import Path


def resources_path(name: str) -> Path:
    """Return the directory holding one kind of runtime asset."""

    return Path(__file__).resolve().parent / name
