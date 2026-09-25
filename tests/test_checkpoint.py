"""
Unit tests for Context-Checkpoint Git-style DAG and branching engine.
"""

import unittest
from context_checkpoint.models import TurnRole
from context_checkpoint.context_tree import ContextTree


class TestContextCheckpoint(unittest.TestCase):

    def setUp(self):
        self.tree = ContextTree("System prompt init")

    def test_root_initialization(self):
        self.assertEqual(len(self.tree.commits), 1)
        self.assertIn("main", self.tree.branches)
        head = self.tree.head_commit_id
        self.assertIsNotNone(head)
        self.assertEqual(self.tree.commits[head].turn.role, TurnRole.SYSTEM)

    def test_linear_commits(self):
        c1 = self.tree.commit(TurnRole.USER, "Build app", "user requirement")
        c2 = self.tree.commit(TurnRole.ASSISTANT, "Code generated", "assistant response")
        self.assertEqual(c2.parent_id, c1.commit_id)
        self.assertGreater(c2.cumulative_tokens, c1.cumulative_tokens)

    def test_branching_and_divergence(self):
        c_base = self.tree.commit(TurnRole.USER, "Requirements", "base prompt")

        # Fork branch A
        self.tree.create_branch("branch_a", c_base.commit_id)
        self.tree.switch_branch("branch_a")
        ca1 = self.tree.commit(TurnRole.ASSISTANT, "Option A", "feat A")

        # Fork branch B
        self.tree.create_branch("branch_b", c_base.commit_id)
        self.tree.switch_branch("branch_b")
        cb1 = self.tree.commit(TurnRole.ASSISTANT, "Option B", "feat B")

        diff = self.tree.diff_branches("branch_a", "branch_b")
        self.assertEqual(diff.common_ancestor_id, c_base.commit_id)
        self.assertIn(ca1.commit_id, diff.commits_in_a)
        self.assertIn(cb1.commit_id, diff.commits_in_b)

    def test_checkout_messages_format(self):
        self.tree.commit(TurnRole.USER, "Do task", "user")
        self.tree.commit(TurnRole.TOOL, "Output", "tool", tool_name="bash")

        messages = self.tree.checkout_messages()
        self.assertEqual(len(messages), 3)  # system + user + tool
        self.assertEqual(messages[0]["role"], "system")
        self.assertEqual(messages[1]["role"], "user")
        self.assertEqual(messages[2]["role"], "tool")
        self.assertEqual(messages[2]["name"], "bash")

    def test_cherry_pick(self):
        # Create commit in branch A
        c_base = self.tree.commit(TurnRole.USER, "Start", "base")
        self.tree.create_branch("branch_a", c_base.commit_id)
        self.tree.switch_branch("branch_a")
        ca = self.tree.commit(TurnRole.ASSISTANT, "Valuable snippet", "snippet")

        # Switch back to main and cherry-pick
        self.tree.switch_branch("main")
        cp = self.tree.cherry_pick(ca.commit_id)
        self.assertEqual(cp.turn.content, "Valuable snippet")
        self.assertIn("cherry-pick", cp.message)
        self.assertGreater(self.tree.metrics.saved_reingestion_tokens, 0)


if __name__ == "__main__":
    unittest.main()
