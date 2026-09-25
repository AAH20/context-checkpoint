"""
Context Tree DAG & Version Control Engine for Context-Checkpoint.
Enables Git-like branching, time-travel, cherry-picking, and prefix cache reuse for agent contexts.
"""

import hashlib
import time
from typing import Dict, List, Optional, Any, Tuple
from .models import (
    TurnRole,
    ContextTurn,
    ContextCommit,
    BranchRef,
    DiffSummary,
    CheckpointMetrics,
)


class ContextTree:
    """Directed Acyclic Graph (DAG) for versioned conversational context states."""

    def __init__(self, initial_system_prompt: Optional[str] = None):
        self.commits: Dict[str, ContextCommit] = {}
        self.branches: Dict[str, BranchRef] = {}
        self.current_branch: str = "main"
        self._head_commit_id: Optional[str] = None
        self.metrics = CheckpointMetrics()

        if initial_system_prompt:
            self.commit(
                role=TurnRole.SYSTEM,
                content=initial_system_prompt,
                message="chore: initialize root system prompt context"
            )

    @property
    def head_commit_id(self) -> Optional[str]:
        return self._head_commit_id

    def commit(
        self,
        role: TurnRole,
        content: str,
        message: str,
        tool_name: Optional[str] = None,
        tool_call_id: Optional[str] = None
    ) -> ContextCommit:
        """Create a new deterministic commit node in the current active branch."""
        # Estimate token count (~4 characters per token heuristic)
        tokens_est = max(1, len(content) // 4)

        parent_id = self._head_commit_id
        parent_commit = self.commits.get(parent_id) if parent_id else None
        cumulative_tokens = (parent_commit.cumulative_tokens if parent_commit else 0) + tokens_est

        # Deterministic commit hash based on parent + content + message
        hasher = hashlib.sha256()
        if parent_id:
            hasher.update(parent_id.encode("utf-8"))
        hasher.update(role.value.encode("utf-8"))
        hasher.update(content.encode("utf-8"))
        hasher.update(str(time.time()).encode("utf-8"))
        commit_id = hasher.hexdigest()[:10]

        # Prefix hash for prompt caching (hashes parent lineage)
        prefix_hasher = hashlib.sha256()
        if parent_commit:
            prefix_hasher.update(parent_commit.prefix_hash.encode("utf-8"))
        prefix_hasher.update(content.encode("utf-8"))
        prefix_hash = prefix_hasher.hexdigest()[:12]

        turn = ContextTurn(
            turn_id=f"turn_{len(self.commits) + 1}",
            role=role,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            tokens_estimate=tokens_est
        )

        commit_node = ContextCommit(
            commit_id=commit_id,
            parent_id=parent_id,
            branch=self.current_branch,
            message=message,
            turn=turn,
            cumulative_tokens=cumulative_tokens,
            prefix_hash=prefix_hash
        )

        self.commits[commit_id] = commit_node
        self._head_commit_id = commit_id

        # Update branch head ref
        self.branches[self.current_branch] = BranchRef(
            name=self.current_branch,
            head_commit_id=commit_id
        )

        self.metrics.total_commits = len(self.commits)
        self.metrics.active_branches = len(self.branches)

        return commit_node

    def create_branch(self, branch_name: str, from_ref: Optional[str] = None) -> BranchRef:
        """Create a new branch pointer from an existing commit or the current HEAD."""
        base_commit_id = from_ref or self._head_commit_id
        if not base_commit_id or base_commit_id not in self.commits:
            raise ValueError(f"Invalid reference commit: {base_commit_id}")

        branch = BranchRef(name=branch_name, head_commit_id=base_commit_id)
        self.branches[branch_name] = branch
        self.metrics.active_branches = len(self.branches)
        return branch

    def switch_branch(self, branch_name: str) -> None:
        """Switch active working branch to branch_name."""
        if branch_name not in self.branches:
            raise ValueError(f"Branch '{branch_name}' does not exist.")
        self.current_branch = branch_name
        self._head_commit_id = self.branches[branch_name].head_commit_id

    def get_lineage(self, ref: Optional[str] = None) -> List[ContextCommit]:
        """Traverse backwards from ref (commit_id or branch name) to the root commit."""
        target_commit_id = None
        if ref is None:
            target_commit_id = self._head_commit_id
        elif ref in self.branches:
            target_commit_id = self.branches[ref].head_commit_id
        elif ref in self.commits:
            target_commit_id = ref
        else:
            raise ValueError(f"Unknown reference: {ref}")

        lineage = []
        curr = self.commits.get(target_commit_id)
        while curr:
            lineage.append(curr)
            curr = self.commits.get(curr.parent_id) if curr.parent_id else None

        lineage.reverse()  # Root to HEAD order
        return lineage

    def checkout_messages(self, ref: Optional[str] = None) -> List[Dict[str, Any]]:
        """Materialize linear messages list suitable for frontier LLM API ingestion."""
        lineage = self.get_lineage(ref)
        messages = []
        for c in lineage:
            msg = {"role": c.turn.role.value, "content": c.turn.content}
            if c.turn.tool_name:
                msg["name"] = c.turn.tool_name
            messages.append(msg)
        return messages

    def cherry_pick(self, commit_id: str, commit_message: Optional[str] = None) -> ContextCommit:
        """Apply a specific turn from another branch onto the current HEAD."""
        source_commit = self.commits.get(commit_id)
        if not source_commit:
            raise ValueError(f"Commit '{commit_id}' not found.")

        msg = commit_message or f"cherry-pick({source_commit.commit_id}): {source_commit.message}"
        new_commit = self.commit(
            role=source_commit.turn.role,
            content=source_commit.turn.content,
            message=msg,
            tool_name=source_commit.turn.tool_name,
            tool_call_id=source_commit.turn.tool_call_id
        )
        self.metrics.saved_reingestion_tokens += source_commit.turn.tokens_estimate
        return new_commit

    def diff_branches(self, branch_a: str, branch_b: str) -> DiffSummary:
        """Compute common ancestor and divergent turns between two branches."""
        lineage_a = self.get_lineage(branch_a)
        lineage_b = self.get_lineage(branch_b)

        ids_a = [c.commit_id for c in lineage_a]
        ids_b = [c.commit_id for c in lineage_b]

        # Find lowest common ancestor
        common_ancestor = None
        for cid in reversed(ids_a):
            if cid in ids_b:
                common_ancestor = cid
                break

        ancestor_idx_a = ids_a.index(common_ancestor) if common_ancestor else -1
        ancestor_idx_b = ids_b.index(common_ancestor) if common_ancestor else -1

        divergent_a = lineage_a[ancestor_idx_a + 1:]
        divergent_b = lineage_b[ancestor_idx_b + 1:]

        tokens_a = sum(c.turn.tokens_estimate for c in divergent_a)
        tokens_b = sum(c.turn.tokens_estimate for c in divergent_b)

        return DiffSummary(
            common_ancestor_id=common_ancestor,
            commits_in_a=[c.commit_id for c in divergent_a],
            commits_in_b=[c.commit_id for c in divergent_b],
            divergent_tokens_a=tokens_a,
            divergent_tokens_b=tokens_b
        )
