"""
Data models and tree definitions for Context-Checkpoint.
Git-Style Deterministic Branching, Delta Caching & Time-Travel State for Long-Horizon Agent Contexts.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any
import time


class TurnRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ContextTurn:
    turn_id: str
    role: TurnRole
    content: str
    tool_name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tokens_estimate: int = 0


@dataclass
class ContextCommit:
    commit_id: str
    parent_id: Optional[str]
    branch: str
    message: str
    turn: ContextTurn
    cumulative_tokens: int
    prefix_hash: str
    created_at: float = field(default_factory=time.time)


@dataclass
class BranchRef:
    name: str
    head_commit_id: str
    created_at: float = field(default_factory=time.time)


@dataclass
class DiffSummary:
    common_ancestor_id: Optional[str]
    commits_in_a: List[str]
    commits_in_b: List[str]
    divergent_tokens_a: int
    divergent_tokens_b: int


@dataclass
class CheckpointMetrics:
    total_commits: int = 0
    active_branches: int = 0
    cached_prefix_tokens: int = 0
    saved_reingestion_tokens: int = 0
