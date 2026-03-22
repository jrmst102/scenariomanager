"""Tests for compute and consensus modules."""

import pytest
from app.core.compute import compute_robustness, aggregate_assessments, get_agreement_level
from app.core.consensus import compute_kendalls_w

SCENARIOS = [
    {"id": "Q1", "name": "S1"},
    {"id": "Q2", "name": "S2"},
    {"id": "Q3", "name": "S3"},
    {"id": "Q4", "name": "S4"},
]

ALTERNATIVES = [
    {"id": "A", "name": "Alt A"},
    {"id": "B", "name": "Alt B"},
]


class TestComputeRobustness:
    def test_basic_ranking(self):
        """Higher average score ranks higher."""
        # Flat assessment dict (single participant's cells)
        assessments = {
            "A_Q1": {"score": 4}, "A_Q2": {"score": 4}, "A_Q3": {"score": 4}, "A_Q4": {"score": 4},
            "B_Q1": {"score": 2}, "B_Q2": {"score": 2}, "B_Q3": {"score": 2}, "B_Q4": {"score": 2},
        }
        result = compute_robustness(assessments, ALTERNATIVES, SCENARIOS)
        assert len(result) == 2
        assert result[0]["id"] == "A"
        assert result[0]["meanScore"] > result[1]["meanScore"]

    def test_empty_assessments(self):
        result = compute_robustness({}, ALTERNATIVES, SCENARIOS)
        assert len(result) == 2
        for item in result:
            assert item["meanScore"] == 0.0

    def test_fragility_tiebreak(self):
        """When mean scores are equal, lower fragility ranks higher."""
        assessments = {
            "A_Q1": {"score": 5}, "A_Q2": {"score": 1}, "A_Q3": {"score": 5}, "A_Q4": {"score": 1},
            "B_Q1": {"score": 3}, "B_Q2": {"score": 3}, "B_Q3": {"score": 3}, "B_Q4": {"score": 3},
        }
        result = compute_robustness(assessments, ALTERNATIVES, SCENARIOS)
        assert result[0]["id"] == "B"


class TestAggregateAssessments:
    def test_aggregation(self):
        all_assessments = {
            "u1": {"A_Q1": {"score": 3}, "A_Q2": {"score": 5}},
            "u2": {"A_Q1": {"score": 5}, "A_Q2": {"score": 3}},
        }
        result = aggregate_assessments(all_assessments, ALTERNATIVES, SCENARIOS)
        cell = result.get("A_Q1")
        assert cell is not None
        assert cell["mean"] == 4.0
        assert cell["median"] == 4.0


class TestAgreementLevel:
    def test_thresholds(self):
        assert get_agreement_level(0.5) == "strong"
        assert get_agreement_level(1.5) == "moderate"
        assert get_agreement_level(2.5) == "divergent"


class TestKendallsW:
    def test_perfect_agreement(self):
        """All raters agree perfectly => W ≈ 1."""
        rankings = [[1, 2, 3, 4], [1, 2, 3, 4], [1, 2, 3, 4]]
        result = compute_kendalls_w(rankings)
        assert result["W"] == pytest.approx(1.0, abs=0.01)
        assert "Strong" in result["interpretation"]

    def test_no_agreement(self):
        """Maximally conflicting rankings => low W."""
        rankings = [[1, 2, 3, 4], [4, 3, 2, 1]]
        result = compute_kendalls_w(rankings)
        assert result["W"] < 0.5

    def test_insufficient_data(self):
        """Single rater should return None / insufficient."""
        result = compute_kendalls_w([[1, 2, 3]])
        assert result["W"] is None
