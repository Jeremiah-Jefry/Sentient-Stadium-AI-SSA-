"""Tests for match context state machine."""
from __future__ import annotations

from app.features.ai_intelligence.context.match_context import (
    HALFTIME_END,
    MatchContextTracker,
)
from app.features.ai_intelligence.models.enums import MatchPhase


class TestMatchContextTracker:
    """Tests for the MatchContextTracker state machine."""

    def test_initial_state_pre_match(self) -> None:
        """Initial state should be PRE_MATCH."""
        tracker = MatchContextTracker()
        assert tracker.current_phase == MatchPhase.PRE_MATCH
        assert tracker.match_time_minutes == 0
        assert tracker.scores == {"home": 0, "away": 0}

    def test_goal_event_transitions(self) -> None:
        """Goal events should update scores."""
        tracker = MatchContextTracker()
        tracker.update_from_event({"type": "GoalScored", "team": "home"})
        assert tracker.scores["home"] == 1
        assert tracker.scores["away"] == 0
        assert tracker.score_diff == 1

        tracker.update_from_event({"type": "GoalScored", "team": "away"})
        assert tracker.scores["home"] == 1
        assert tracker.scores["away"] == 1
        assert tracker.score_diff == 0

    def test_halftime_modifiers(self) -> None:
        """Halftime should increase exit demand."""
        tracker = MatchContextTracker()
        tracker.update_from_event({"type": "HalfTime"})
        modifiers = tracker.get_behavior_modifiers()
        assert modifiers["exit_demand"] >= 0.5, (
            f"Expected high exit demand at halftime, got {modifiers['exit_demand']}"
        )
        assert tracker.current_phase == MatchPhase.HALFTIME

    def test_behavior_modifiers_bounded(self) -> None:
        """All modifiers should be between 0.0 and 1.0."""
        tracker = MatchContextTracker()
        phases_to_test = [
            MatchPhase.PRE_MATCH,
            MatchPhase.KICKOFF,
            MatchPhase.FIRST_HALF,
            MatchPhase.HALFTIME,
            MatchPhase.SECOND_HALF,
            MatchPhase.EXTRA_TIME,
            MatchPhase.PENALTY_SHOOTOUT,
            MatchPhase.POST_MATCH,
        ]
        for phase in phases_to_test:
            tracker._current_phase = phase
            modifiers = tracker.get_behavior_modifiers()
            for key, value in modifiers.items():
                assert 0.0 <= value <= 1.0, (
                    f"Modifier {key}={value} out of bounds for phase {phase}"
                )

    def test_phase_transition_prediction(self) -> None:
        """Should predict phase transitions based on time."""
        tracker = MatchContextTracker()
        transition = tracker.predict_phase_transition(60)
        assert transition == MatchPhase.KICKOFF

    def test_kickoff_to_halftime(self) -> None:
        """Kickoff should transition to halftime when minute exceeds 45."""
        tracker = MatchContextTracker()
        tracker.update_from_event({"type": "Kickoff"})
        tracker.update_from_event({"type": "MinuteUpdate", "minute": 46})
        assert tracker.current_phase == MatchPhase.HALFTIME

    def test_second_half_start(self) -> None:
        """SecondHalfStart should set phase correctly."""
        tracker = MatchContextTracker()
        tracker.update_from_event({"type": "HalfTime"})
        tracker.update_from_event({"type": "SecondHalfStart"})
        assert tracker.current_phase == MatchPhase.SECOND_HALF
        assert tracker.match_time_minutes == HALFTIME_END

    def test_full_time_tied_goes_to_penalties(self) -> None:
        """FullTime with tied score and penalty_applicable should go to penalties."""
        tracker = MatchContextTracker()
        tracker.update_from_event({"type": "Kickoff"})
        tracker.update_from_event({"type": "GoalScored", "team": "home"})
        tracker.update_from_event({"type": "GoalScored", "team": "away"})
        tracker.update_from_event({
            "type": "FullTime",
            "extra_time_applicable": False,
            "penalty_applicable": True,
        })
        assert tracker.current_phase == MatchPhase.PENALTY_SHOOTOUT

    def test_full_time_tied_no_penalties(self) -> None:
        """FullTime with tied score and no penalty_applicable should go to POST_MATCH."""
        tracker = MatchContextTracker()
        tracker.update_from_event({
            "type": "FullTime",
            "extra_time_applicable": False,
            "penalty_applicable": False,
        })
        assert tracker.current_phase == MatchPhase.POST_MATCH

    def test_full_time_with_extra_time(self) -> None:
        """FullTime with extra_time_applicable should go to EXTRA_TIME."""
        tracker = MatchContextTracker()
        tracker.update_from_event({
            "type": "FullTime",
            "extra_time_applicable": True,
        })
        assert tracker.current_phase == MatchPhase.EXTRA_TIME

    def test_penalty_shootout_end(self) -> None:
        """PenaltyShootoutEnd should transition to POST_MATCH."""
        tracker = MatchContextTracker()
        tracker._current_phase = MatchPhase.PENALTY_SHOOTOUT
        tracker.update_from_event({"type": "PenaltyShootoutEnd"})
        assert tracker.current_phase == MatchPhase.POST_MATCH

    def test_kickoff_sets_time_to_zero(self) -> None:
        """Kickoff should reset match time to 0."""
        tracker = MatchContextTracker()
        tracker.update_from_event({"type": "MinuteUpdate", "minute": 30})
        assert tracker.match_time_minutes == 30
        tracker.update_from_event({"type": "Kickoff"})
        assert tracker.match_time_minutes == 0
        assert tracker.current_phase == MatchPhase.KICKOFF

    def test_late_match_tension(self) -> None:
        """Close score after minute 75 should reduce patience."""
        tracker = MatchContextTracker()
        tracker._current_phase = MatchPhase.SECOND_HALF
        tracker._match_time_minutes = 80
        tracker._home_score = 1
        tracker._away_score = 1
        modifiers = tracker.get_behavior_modifiers()
        assert modifiers["patience_factor"] < 0.6

    def test_goal_events_boost_security(self) -> None:
        """Multiple goals should boost security alertness."""
        tracker = MatchContextTracker()
        for _ in range(5):
            tracker.update_from_event({"type": "GoalScored", "team": "home"})
        modifiers = tracker.get_behavior_modifiers()
        assert modifiers["security_alertness"] >= 0.5

    def test_stats(self) -> None:
        """Stats should return correct summary."""
        tracker = MatchContextTracker()
        tracker.update_from_event({"type": "GoalScored", "team": "home"})
        stats = tracker.stats
        assert stats["current_phase"] == "pre_match"
        assert stats["goal_events"] == 1
        assert stats["event_count"] == 1
        assert stats["scores"]["home"] == 1
