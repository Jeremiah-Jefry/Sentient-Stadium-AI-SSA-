"""Match state reasoning — tracks match phase and its influence on crowd behaviour."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from app.features.ai_intelligence.models.enums import MatchPhase

logger = logging.getLogger(__name__)

# Minutes thresholds for phase transitions
HALFTIME_START: int = 45
HALFTIME_END: int = 60
FULL_TIME: int = 90
EXTRA_TIME_END: int = 120

# Phase-specific crowd behaviour modifiers
_PRE_MATCH_MODS = {
    "movement_intensity": 0.8,
    "density_surge": 0.4,
    "exit_demand": 0.1,
    "medical_alertness": 0.4,
    "security_alertness": 0.5,
    "patience_factor": 0.6,
}
_KICKOFF_MODS = {
    "movement_intensity": 0.3,
    "density_surge": 0.1,
    "exit_demand": 0.05,
    "medical_alertness": 0.3,
    "security_alertness": 0.3,
    "patience_factor": 0.8,
}
_FIRST_HALF_MODS = {
    "movement_intensity": 0.2,
    "density_surge": 0.1,
    "exit_demand": 0.05,
    "medical_alertness": 0.3,
    "security_alertness": 0.3,
    "patience_factor": 0.8,
}
_HALFTIME_MODS = {
    "movement_intensity": 0.9,
    "density_surge": 0.6,
    "exit_demand": 0.7,
    "medical_alertness": 0.5,
    "security_alertness": 0.5,
    "patience_factor": 0.5,
}
_SECOND_HALF_MODS = {
    "movement_intensity": 0.2,
    "density_surge": 0.1,
    "exit_demand": 0.05,
    "medical_alertness": 0.4,
    "security_alertness": 0.4,
    "patience_factor": 0.7,
}
_GOAL_SCORED_MODS = {
    "movement_intensity": 0.9,
    "density_surge": 0.8,
    "exit_demand": 0.1,
    "medical_alertness": 0.6,
    "security_alertness": 0.7,
    "patience_factor": 0.3,
}
_PENALTY_MODS = {
    "movement_intensity": 0.1,
    "density_surge": 0.2,
    "exit_demand": 0.02,
    "medical_alertness": 0.7,
    "security_alertness": 0.8,
    "patience_factor": 0.2,
}
_POST_MATCH_MODS = {
    "movement_intensity": 1.0,
    "density_surge": 0.5,
    "exit_demand": 1.0,
    "medical_alertness": 0.6,
    "security_alertness": 0.7,
    "patience_factor": 0.3,
}

_PHASE_MODIFIERS: dict[MatchPhase, dict[str, float]] = {
    MatchPhase.PRE_MATCH: _PRE_MATCH_MODS,
    MatchPhase.KICKOFF: _KICKOFF_MODS,
    MatchPhase.FIRST_HALF: _FIRST_HALF_MODS,
    MatchPhase.HALFTIME: _HALFTIME_MODS,
    MatchPhase.SECOND_HALF: _SECOND_HALF_MODS,
    MatchPhase.EXTRA_TIME: _SECOND_HALF_MODS,
    MatchPhase.PENALTY_SHOOTOUT: _PENALTY_MODS,
    MatchPhase.POST_MATCH: _POST_MATCH_MODS,
    MatchPhase.RAIN_DELAY: _PRE_MATCH_MODS,
    MatchPhase.EVACUATION: _POST_MATCH_MODS,
}


@dataclass(slots=True)
class BehaviorModifiers:
    """Multipliers derived from the current match state."""

    movement_intensity: float = 1.0
    density_surge: float = 0.0
    exit_demand: float = 0.0
    medical_alertness: float = 0.5
    security_alertness: float = 0.5
    patience_factor: float = 0.5


class MatchContextTracker:
    """Tracks current match state and its influence on crowd behaviour.

    Updates are event-driven (goal scored, card shown, etc.) and
    predict the next likely phase transition so downstream systems
    can prepare.
    """

    def __init__(self) -> None:
        self._current_phase: MatchPhase = MatchPhase.PRE_MATCH
        self._match_time_minutes: int = 0
        self._home_score: int = 0
        self._away_score: int = 0
        self._is_extra_time: bool = False
        self._is_penalty_shootout: bool = False
        self._event_history: list[dict] = []
        self._goal_events: int = 0

    def update_from_event(self, event: dict) -> None:
        """Update match state from incoming events."""
        event_type = event.get("type", "")

        if event_type == "GoalScored":
            team = event.get("team", "home")
            if team == "home":
                self._home_score += 1
            else:
                self._away_score += 1
            self._goal_events += 1
            self._event_history.append(event)
            logger.info(
                "Goal scored: home=%d away=%d", self._home_score, self._away_score,
            )

        elif event_type == "HalfTime":
            self._current_phase = MatchPhase.HALFTIME
            self._match_time_minutes = HALFTIME_START
            self._event_history.append(event)

        elif event_type == "SecondHalfStart":
            self._current_phase = MatchPhase.SECOND_HALF
            self._match_time_minutes = HALFTIME_END
            self._event_history.append(event)

        elif event_type == "FullTime":
            if self._is_extra_time:
                self._current_phase = MatchPhase.POST_MATCH
            elif event.get("extra_time_applicable", False):
                self._is_extra_time = True
                self._current_phase = MatchPhase.EXTRA_TIME
            else:
                score_diff = abs(self._home_score - self._away_score)
                if score_diff == 0 and event.get("penalty_applicable", True):
                    self._is_penalty_shootout = True
                    self._current_phase = MatchPhase.PENALTY_SHOOTOUT
                else:
                    self._current_phase = MatchPhase.POST_MATCH
            self._event_history.append(event)

        elif event_type == "PenaltyShootoutEnd":
            self._current_phase = MatchPhase.POST_MATCH
            self._is_penalty_shootout = False
            self._event_history.append(event)

        elif event_type == "Kickoff":
            self._current_phase = MatchPhase.KICKOFF
            self._match_time_minutes = 0
            self._event_history.append(event)

        elif event_type == "MinuteUpdate":
            self._match_time_minutes = int(event.get("minute", self._match_time_minutes))
            if (self._match_time_minutes > HALFTIME_START
                    and self._match_time_minutes <= HALFTIME_END):
                self._current_phase = MatchPhase.HALFTIME
            elif self._match_time_minutes > HALFTIME_END and self._match_time_minutes <= FULL_TIME:
                self._current_phase = MatchPhase.SECOND_HALF
            elif self._match_time_minutes > FULL_TIME and self._is_extra_time:
                self._current_phase = MatchPhase.EXTRA_TIME
            self._event_history.append(event)

    def get_behavior_modifiers(self) -> dict:
        """Return crowd behavior modifiers based on current match phase."""
        base = dict(_PHASE_MODIFIERS.get(self._current_phase, _PRE_MATCH_MODS))

        score_diff = abs(self._home_score - self._away_score)
        if self._goal_events > 0:
            tension_boost = min(self._goal_events * 0.05, 0.15)
            base["security_alertness"] = min(1.0, base["security_alertness"] + tension_boost)

        if score_diff <= 1 and self._match_time_minutes > 75:
            base["patience_factor"] = max(0.1, base["patience_factor"] - 0.2)
            base["medical_alertness"] = min(1.0, base["medical_alertness"] + 0.15)

        return base

    def predict_phase_transition(self, minutes_ahead: int) -> MatchPhase | None:
        """Predict likely match phase transition within given timeframe."""
        future_minute = self._match_time_minutes + minutes_ahead

        if self._current_phase == MatchPhase.PRE_MATCH:
            if future_minute >= 0:
                return MatchPhase.KICKOFF

        if self._current_phase in (MatchPhase.KICKOFF, MatchPhase.FIRST_HALF):
            if future_minute >= HALFTIME_START:
                return MatchPhase.HALFTIME

        if self._current_phase == MatchPhase.HALFTIME:
            if future_minute >= HALFTIME_END:
                return MatchPhase.SECOND_HALF

        if self._current_phase == MatchPhase.SECOND_HALF:
            if future_minute >= FULL_TIME:
                if self._is_extra_time:
                    return MatchPhase.EXTRA_TIME
                return MatchPhase.POST_MATCH

        if self._current_phase == MatchPhase.EXTRA_TIME:
            if future_minute >= EXTRA_TIME_END:
                score_diff = abs(self._home_score - self._away_score)
                if score_diff == 0:
                    return MatchPhase.PENALTY_SHOOTOUT
                return MatchPhase.POST_MATCH

        if self._current_phase == MatchPhase.PENALTY_SHOOTOUT:
            return MatchPhase.POST_MATCH

        return None

    @property
    def current_phase(self) -> MatchPhase:
        return self._current_phase

    @property
    def scores(self) -> dict[str, int]:
        return {"home": self._home_score, "away": self._away_score}

    @property
    def match_time_minutes(self) -> int:
        return self._match_time_minutes

    @property
    def score_diff(self) -> int:
        return self._home_score - self._away_score

    @property
    def stats(self) -> dict:
        return {
            "current_phase": self._current_phase.value,
            "match_time": self._match_time_minutes,
            "scores": self.scores,
            "goal_events": self._goal_events,
            "event_count": len(self._event_history),
        }
