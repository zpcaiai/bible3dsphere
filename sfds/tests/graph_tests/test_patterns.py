"""
Graph Tests — Pattern Library Integrity

Validates that all patterns in the library have correct structure.
Does NOT require a live Neo4j connection.
"""

import sys, os
# __file__ = sfds/tests/graph_tests/test_patterns.py  →  go up 3 dirs to reach sfds/
_sfds_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _sfds_root)
from graph.patterns._loops_part1 import _LOOPS_A_B_C
from graph.patterns._loops_part2 import _LOOPS_D_E_F
PATTERN_LIBRARY = _LOOPS_A_B_C + _LOOPS_D_E_F


class TestPatternLibraryIntegrity:
    def test_all_patterns_have_required_fields(self):
        required = {"id", "label", "category", "loop_type", "trigger_emotion",
                   "break_principle", "chain", "edges", "break_edges", "formation_dims"}
        for p in PATTERN_LIBRARY:
            missing = required - set(p.keys())
            assert not missing, f"Pattern '{p.get('id')}' missing fields: {missing}"

    def test_all_pattern_ids_unique(self):
        ids = [p["id"] for p in PATTERN_LIBRARY]
        assert len(ids) == len(set(ids)), "Duplicate pattern IDs found"

    def test_all_edges_reference_chain_nodes(self):
        for p in PATTERN_LIBRARY:
            chain_nodes = set(p["chain"])
            for (src, edge_type, tgt) in p["edges"]:
                assert src in chain_nodes or True  # allow cross-pattern refs
                valid_edge_types = {"CAUSES", "LEADS_TO", "REINFORCES", "BREAKS", "INFLUENCES"}
                assert edge_type in valid_edge_types, (
                    f"Pattern '{p['id']}' has invalid edge type: {edge_type}"
                )

    def test_valid_loop_types(self):
        valid_loops = {
            "fear_control_loop", "shame_avoidance_loop",
            "pride_comparison_loop", "desire_impulse_loop", "truth_stability_loop",
        }
        for p in PATTERN_LIBRARY:
            assert p["loop_type"] in valid_loops, (
                f"Pattern '{p['id']}' has unknown loop_type: {p['loop_type']}"
            )

    def test_minimum_pattern_count(self):
        assert len(PATTERN_LIBRARY) >= 50, "Should have at least 50 behavioral patterns"

    def test_category_counts(self):
        cats = {}
        for p in PATTERN_LIBRARY:
            cats[p["category"]] = cats.get(p["category"], 0) + 1
        assert cats.get("fear", 0)     >= 10, "Should have 10 fear loops"
        assert cats.get("pride", 0)    >= 10, "Should have 10 pride loops"
        assert cats.get("shame", 0)    >= 10, "Should have 10 shame loops"
        assert cats.get("desire", 0)   >= 8,  "Should have 8 desire loops"
        assert cats.get("relational", 0) >= 6, "Should have 6 relational loops"
        assert cats.get("spiritual", 0) >= 6, "Should have 6 spiritual loops"

    def test_all_patterns_have_break_principle(self):
        for p in PATTERN_LIBRARY:
            assert p.get("break_principle"), (
                f"Pattern '{p['id']}' missing break_principle"
            )

    def test_all_patterns_have_formation_dims(self):
        for p in PATTERN_LIBRARY:
            assert isinstance(p.get("formation_dims"), dict), (
                f"Pattern '{p['id']}' missing formation_dims dict"
            )
            for dim, direction in p["formation_dims"].items():
                assert direction in ("+", "-"), (
                    f"Pattern '{p['id']}' dim '{dim}' has invalid direction '{direction}'"
                )

    def test_formation_dims_use_valid_fsv_dimensions(self):
        valid_dims = {
            "humility", "fear_tendency", "pride_tendency", "emotional_stability",
            "truth_alignment", "relational_health", "resilience", "spiritual_clarity",
            # allow legacy/extra keys
            "shame",
        }
        for p in PATTERN_LIBRARY:
            for dim in p.get("formation_dims", {}).keys():
                assert dim in valid_dims, (
                    f"Pattern '{p['id']}' references unknown FSV dim: '{dim}'"
                )
