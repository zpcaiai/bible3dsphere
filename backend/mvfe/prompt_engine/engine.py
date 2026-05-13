"""
SELF-EVOLVING PROMPT SYSTEM
Computes drift, updates prompts, maintains registry.
"""
import json
import logging
import uuid
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class DriftMetrics:
    epsilon_pred: float  # prediction mismatch
    epsilon_attr: float  # wrong explanation of cause
    epsilon_loop: float  # unstable behavioral loop detection


@dataclass
class PromptVersion:
    id: str
    prompt_name: str
    version: int
    content: str
    is_active: bool
    performance_score: float
    created_at: str


class PromptEngine:
    """
    Self-evolving prompt system.
    - Computes drift between predicted and observed patterns
    - Updates prompts based on drift signals
    - Maintains version registry with rollback support
    """

    # Conservative update thresholds
    DRIFT_THRESHOLD = 0.15  # Only update if drift > threshold
    MAX_UPDATE_DELTA = 0.1  # Maximum change per update cycle

    def __init__(self, db_pool=None):
        self._db_pool = db_pool
        self._registry: Dict[str, List[PromptVersion]] = {}
        self._predictions: Dict[str, dict] = {}  # user_id -> last prediction

    def compute_drift(
        self,
        user_id: str,
        predicted_emotion: dict,
        observed_emotion: dict,
        predicted_decision: dict,
        observed_decision: dict,
    ) -> DriftMetrics:
        """
        Compare predicted vs observed behavior patterns.
        Returns epsilon values for prediction, attribution, and loop detection.
        """
        # epsilon_pred: mismatch between predicted and observed emotion intensity
        pred_intensity = predicted_emotion.get("intensity", 0.5)
        obs_intensity = observed_emotion.get("intensity", 0.5)
        epsilon_pred = abs(pred_intensity - obs_intensity)

        # epsilon_attr: wrong explanation of cause (driver mismatch)
        pred_fear = predicted_decision.get("drivers", {}).get("fear", 0.5)
        obs_fear = observed_decision.get("drivers", {}).get("fear", 0.5)
        pred_love = predicted_decision.get("drivers", {}).get("love", 0.3)
        obs_love = observed_decision.get("drivers", {}).get("love", 0.3)
        epsilon_attr = (abs(pred_fear - obs_fear) + abs(pred_love - obs_love)) / 2

        # epsilon_loop: detect unstable loops (repeated similar patterns)
        epsilon_loop = self._detect_loop_instability(user_id, observed_emotion)

        metrics = DriftMetrics(
            epsilon_pred=round(epsilon_pred, 4),
            epsilon_attr=round(epsilon_attr, 4),
            epsilon_loop=round(epsilon_loop, 4),
        )
        logger.info(
            f"[prompt-engine] drift user={user_id[:8]} "
            f"ε_pred={metrics.epsilon_pred} ε_attr={metrics.epsilon_attr} ε_loop={metrics.epsilon_loop}"
        )
        return metrics

    def update_prompt(self, prompt_name: str, drift: DriftMetrics, current_content: str) -> Optional[str]:
        """
        Modify prompt based on drift signals.
        Conservative update rules:
        - Only update if drift exceeds threshold
        - NEVER make system more deterministic
        - ALWAYS preserve uncertainty
        """
        total_drift = (drift.epsilon_pred + drift.epsilon_attr + drift.epsilon_loop) / 3

        if total_drift < self.DRIFT_THRESHOLD:
            logger.info(f"[prompt-engine] drift below threshold ({total_drift:.3f} < {self.DRIFT_THRESHOLD}), no update")
            return None

        # Generate update hints (not full rewrite)
        updates = []
        if drift.epsilon_pred > 0.2:
            updates.append("Widen emotional intensity range estimates. Avoid anchoring to previous patterns.")
        if drift.epsilon_attr > 0.2:
            updates.append("Consider alternative causal explanations. Weight multiple drivers more equally.")
        if drift.epsilon_loop > 0.3:
            updates.append("Reduce pattern-matching confidence. Allow for behavioral novelty.")

        if not updates:
            return None

        # Append update instructions (conservative - only add, never remove)
        suffix = "\n\n[SYSTEM CALIBRATION - Auto-applied]\n" + "\n".join(f"- {u}" for u in updates)
        new_content = current_content + suffix

        # Store new version
        self._store_version(prompt_name, new_content)

        logger.info(f"[prompt-engine] updated prompt '{prompt_name}' with {len(updates)} calibrations")
        return new_content

    def get_active_prompt(self, prompt_name: str) -> Optional[str]:
        """Get the currently active version of a prompt."""
        if prompt_name in self._registry and self._registry[prompt_name]:
            active = [p for p in self._registry[prompt_name] if p.is_active]
            if active:
                return active[-1].content
        return None

    def rollback(self, prompt_name: str) -> Optional[str]:
        """Rollback to previous version."""
        versions = self._registry.get(prompt_name, [])
        if len(versions) < 2:
            return None
        # Deactivate current
        versions[-1].is_active = False
        # Activate previous
        versions[-2].is_active = True
        logger.info(f"[prompt-engine] rolled back '{prompt_name}' to version {versions[-2].version}")
        return versions[-2].content

    def _store_version(self, prompt_name: str, content: str):
        """Store a new prompt version."""
        versions = self._registry.get(prompt_name, [])
        # Deactivate all previous
        for v in versions:
            v.is_active = False

        new_version = PromptVersion(
            id=str(uuid.uuid4()),
            prompt_name=prompt_name,
            version=len(versions) + 1,
            content=content,
            is_active=True,
            performance_score=0.0,
            created_at=datetime.utcnow().isoformat(),
        )
        versions.append(new_version)
        self._registry[prompt_name] = versions

        # Persist to DB if available
        if self._db_pool:
            self._persist_version(new_version)

    def _persist_version(self, pv: PromptVersion):
        """Persist prompt version to database."""
        conn = self._db_pool.getconn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO mvfe_prompt_registry (id, prompt_name, version, content, is_active, created_at)
                       VALUES (%s, %s, %s, %s, %s, %s)
                       ON CONFLICT (prompt_name, version) DO UPDATE SET
                         content = EXCLUDED.content, is_active = EXCLUDED.is_active""",
                    (pv.id, pv.prompt_name, pv.version, pv.content, pv.is_active, pv.created_at),
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.warning(f"[prompt-engine] persist failed: {e}")
        finally:
            self._db_pool.putconn(conn)

    def _detect_loop_instability(self, user_id: str, current_emotion: dict) -> float:
        """Detect if user is stuck in a behavioral loop."""
        prev = self._predictions.get(user_id)
        if not prev:
            self._predictions[user_id] = current_emotion
            return 0.0

        # Compare to last observation — high similarity = potential loop
        prev_type = prev.get("primary_emotion", "")
        curr_type = current_emotion.get("primary_emotion", "")
        same_emotion = 1.0 if prev_type == curr_type else 0.0

        prev_intensity = prev.get("intensity", 0.5)
        curr_intensity = current_emotion.get("intensity", 0.5)
        intensity_similarity = 1.0 - abs(prev_intensity - curr_intensity)

        loop_score = 0.6 * same_emotion + 0.4 * intensity_similarity

        self._predictions[user_id] = current_emotion
        return round(loop_score, 4)

    def to_dict(self, metrics: DriftMetrics) -> dict:
        return asdict(metrics)
