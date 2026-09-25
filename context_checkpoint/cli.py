"""
CLI interface and interactive demonstration runner for Context-Checkpoint.
"""

import sys
import json
import argparse
from .models import TurnRole
from .context_tree import ContextTree


def run_demo():
    print("=" * 74)
    print("  CONTEXT-CHECKPOINT: Git-Style Context Version Control for Frontier AI")
    print("  Optimized for Long-Horizon Reasoning in Claude Opus 5.5 & Gemini 3.8 Flash")
    print("=" * 74)

    # 1. Root Context Tree Initialization
    tree = ContextTree(
        initial_system_prompt="You are an autonomous engineering agent specializing in distributed systems."
    )

    c1 = tree.commit(
        role=TurnRole.USER,
        content="Build a high-throughput transaction ledger with idempotent replay capabilities.",
        message="feat(prompt): initial user specification and constraints"
    )

    c2 = tree.commit(
        role=TurnRole.ASSISTANT,
        content="Scaffolded PostgreSQL schema with transaction logs, sequence locks, and ACID guarantees.",
        message="feat(arch): database schema and sequence lock scaffolding"
    )

    print("\n[STEP 1] BASELINE LINEAGE COMMITTED (main branch)")
    print(f"  Head Commit: {c2.commit_id} ({c2.message})")
    print(f"  Cumulative Tokens: {c2.cumulative_tokens} | Prefix Hash: {c2.prefix_hash}")

    # 2. Branching into two speculative trajectories
    print("\n[STEP 2] FORKING SPECULATIVE EXPLORATION BRANCHES")
    tree.create_branch("feature/graphql", from_ref=c2.commit_id)
    tree.create_branch("feature/grpc", from_ref=c2.commit_id)
    print("  Created branch 'feature/graphql' at common ancestor commit " + c2.commit_id)
    print("  Created branch 'feature/grpc' at common ancestor commit " + c2.commit_id)

    # Explore feature/graphql
    tree.switch_branch("feature/graphql")
    tree.commit(
        role=TurnRole.ASSISTANT,
        content="Implemented GraphQL query schema with Strawberry and Apollo Federation.",
        message="feat(graphql): schema definitions"
    )
    c_validator = tree.commit(
        role=TurnRole.ASSISTANT,
        content="def validate_amount(val): return val > 0 and val < 1_000_000 # Zero-bug validator",
        message="feat(util): robust ledger amount validator helper"
    )
    tree.commit(
        role=TurnRole.TOOL,
        content="Error 500: Circular dependency between GraphQL schema resolvers and SQLAlchemy models.",
        message="error(tool): circular dependency crash in graphql resolver",
        tool_name="test_runner"
    )
    print(f"  [Branch: feature/graphql] Reached turn 6 (Encountered circular dependency deadlock)")

    # Explore feature/grpc
    tree.switch_branch("feature/grpc")
    tree.commit(
        role=TurnRole.ASSISTANT,
        content="Implemented Protobuf protocol specs with gRPC streaming RPCs.",
        message="feat(grpc): protobuf definitions and gRPC service stub"
    )
    tree.commit(
        role=TurnRole.TOOL,
        content="Tests Passed: 18/18 gRPC integration tests passed with 0.12ms p99 latency.",
        message="test(grpc): 100% tests pass on gRPC architecture",
        tool_name="test_runner"
    )
    print(f"  [Branch: feature/grpc] Reached turn 5 (All 18 tests passed cleanly)")

    # 3. Diff Branches
    print("\n[STEP 3] BRANCH DIVERGENCE ANALYSIS")
    diff = tree.diff_branches("feature/graphql", "feature/grpc")
    print(f"  Common Ancestor: {diff.common_ancestor_id}")
    print(f"  GraphQL Divergent Commits: {len(diff.commits_in_a)} ({diff.divergent_tokens_a} tokens)")
    print(f"  gRPC Divergent Commits   : {len(diff.commits_in_b)} ({diff.divergent_tokens_b} tokens)")

    # 4. Cherry-Pick Valuable Milestone from Dead Branch
    print("\n[STEP 4] CHERRY-PICKING COMPONENT INTO WINNING BRANCH")
    print(f"  Cherry-picking validator commit {c_validator.commit_id} from feature/graphql into feature/grpc...")
    cp_commit = tree.cherry_pick(c_validator.commit_id)
    print(f"  >> Cherry-picked to {cp_commit.commit_id}: {cp_commit.message}")
    print(f"  >> Tokens Saved via Delta Reuse: {tree.metrics.saved_reingestion_tokens} tokens")

    # 5. Materialize Clean Message Payload for Frontier Model
    messages = tree.checkout_messages("feature/grpc")
    print(f"\n[STEP 5] MATERIALIZED MESSAGES FOR FRONTIER MODEL INGESTION ({len(messages)} turns)")
    for i, m in enumerate(messages, 1):
        print(f"  [{i}] ({m['role']}) {m['content'][:60]}...")

    print("\n" + "=" * 74)
    print("  CONTEXT-CHECKPOINT VERSION SUMMARY")
    print(f"  Total Tree Commits  : {tree.metrics.total_commits}")
    print(f"  Active Branches     : {tree.metrics.active_branches}")
    print(f"  Prefix Cache Reuse  : 100% Shared Ancestor Prefix")
    print("=" * 74 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="context-checkpoint: Git-Style Context Version Control for Frontier AI"
    )
    subparsers = parser.add_subparsers(dest="command")
    demo_parser = subparsers.add_parser("demo", help="Run interactive context checkpoint demonstration")

    args = parser.parse_args()
    if args.command == "demo" or len(sys.argv) == 1:
        run_demo()


if __name__ == "__main__":
    main()
