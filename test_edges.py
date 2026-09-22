"""Tests for paradigm-edges."""
import unittest
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from edges import (
    EdgeCell, EDGE_TYPES, find_edges_for_paradigm, fnv1a_64,
)


class TestFNV1a(unittest.TestCase):
    def test_fleet_canary(self):
        self.assertEqual(fnv1a_64('café Δ 日本語'), '0x24a555471370b18d')


class TestEdgeTypes(unittest.TestCase):
    def test_all_known_types(self):
        expected = ['hallucination', 'logical_inconsistency', 'unsupported_claim', 'missing_capability', 'contradictory_answer', 'format_violation', 'overconfidence', 'context_loss']
        for et in expected:
            self.assertIn(et, EDGE_TYPES)


class TestEdgeCell(unittest.TestCase):
    def test_creation(self):
        cell = EdgeCell(
            cell_id='e1',
            paradigm='math',
            model='qwen',
            edge_type='hallucination',
            severity=7.0,
            description='Made up a theorem',
        )
        self.assertEqual(cell.severity, 7.0)
        self.assertEqual(cell.edge_type, 'hallucination')
    
    def test_hash_changes(self):
        c1 = EdgeCell('e1', 'math', 'qwen', 'hallucination', 7.0, 'desc1')
        c2 = EdgeCell('e2', 'math', 'qwen', 'hallucination', 7.0, 'desc2')
        self.assertNotEqual(c1.hash(), c2.hash())


if __name__ == '__main__':
    unittest.main(verbosity=2)
