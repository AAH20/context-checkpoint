"""
context-checkpoint: Git-Style Deterministic Branching, Delta Caching & Time-Travel State for Long-Horizon Agent Contexts.
"""

from .models import (
    TurnRole,
    ContextTurn,
    ContextCommit,
    BranchRef,
    DiffSummary,
    CheckpointMetrics,
)
from .context_tree import ContextTree

__version__ = "0.1.0"
__all__ = [
    "TurnRole",
    "ContextTurn",
    "ContextCommit",
    "BranchRef",
    "DiffSummary",
    "CheckpointMetrics",
    "ContextTree",
]
