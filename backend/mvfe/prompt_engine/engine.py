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
    MAX_UPDATES_PER_DAY = 3  # Rate limiter — prevent runaway evolution
    ENTROPY_FLOOR = 0.2  # Minimum uncertainty — prevents overfitting

    # Total error weights (α + β + γ = 1.0)
    W_PRED = 0.4   # prediction error weight
    W_ATTR = 0.3   # attribution error weight
    W_LOOP = 0.3   # loop stability error weight

    def __init__(self, db_pool=None):
        self._db_pool = db_pool
        self._registry: Dict[str, List[PromptVersion]] = {}
        self._predictions: Dict[str, dict] = {}  # user_id -> last prediction
        self._update_counts: Dict[str, int] = {}  # date_str -> count

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

        # Compute weighted total error: E_total = α·ε_pred + β·ε_attr + γ·ε_loop
        total_error = (
            self.W_PRED * epsilon_pred
            + self.W_ATTR * epsilon_attr
            + self.W_LOOP * epsilon_loop
        )

        metrics = DriftMetrics(
            epsilon_pred=round(epsilon_pred, 4),
            epsilon_attr=round(epsilon_attr, 4),
            epsilon_loop=round(epsilon_loop, 4),
        )
        logger.info(
            f"[prompt-engine] drift user={user_id[:8]} "
            f"ε_pred={metrics.epsilon_pred} ε_attr={metrics.epsilon_attr} ε_loop={metrics.epsilon_loop} "
            f"E_total={total_error:.4f}"
        )

        # Persist drift event for system memory
        self._persist_drift_event(user_id, metrics, total_error)

        return metrics

    def update_prompt(self, prompt_name: str, drift: DriftMetrics, current_content: str) -> Optional[str]:
        """
        Modify prompt based on drift signals using 4 pseudo-gradient directions.
        Controls:
        - Rate limiter (max 3/day)
        - Entropy floor (minimum uncertainty)
        - Semantic stability (no personality labels, deterministic predictions)
        """
        # 1. Compute weighted total error
        total_error = (
            self.W_PRED * drift.epsilon_pred
            + self.W_ATTR * drift.epsilon_attr
            + self.W_LOOP * drift.epsilon_loop
        )

        if total_error < self.DRIFT_THRESHOLD:
            logger.info(f"[prompt-engine] E_total below threshold ({total_error:.3f} < {self.DRIFT_THRESHOLD}), no update")
            return None

        # 2. Rate limiter check
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self._update_counts.get(today, 0) >= self.MAX_UPDATES_PER_DAY:
            logger.warning(f"[prompt-engine] rate limit reached ({self.MAX_UPDATES_PER_DAY}/day), skipping update")
            return None

        # 3. Entropy floor — check current prompt uncertainty
        entropy = self._compute_entropy(current_content)
        if entropy < self.ENTROPY_FLOOR:
            logger.warning(f"[prompt-engine] entropy below floor ({entropy:.3f}), injecting randomness")
            current_content = self._inject_entropy(current_content)

        # 4. Four pseudo-gradient directions (structured prompt transformation)
        gradients = self._compute_gradients(drift, current_content)
        if not gradients:
            return None

        # 5. Apply transformations (only append, never remove)
        suffix = "\n\n[SYSTEM CALIBRATION v{} - Auto-applied]\n".format(
            len(self._registry.get(prompt_name, [])) + 1
        )
        suffix += "\n".join(f"- {g}" for g in gradients)
        new_content = current_content + suffix

        # 6. Semantic stability check — block forbidden patterns
        if self._has_forbidden_patterns(new_content):
            logger.error("[prompt-engine] update blocked: forbidden semantic pattern detected")
            return None

        # 7. Store new version and increment rate counter
        self._store_version(prompt_name, new_content)
        self._update_counts[today] = self._update_counts.get(today, 0) + 1

        logger.info(
            f"[prompt-engine] updated '{prompt_name}' with {len(gradients)} gradients, "
            f"E_total={total_error:.3f}, updates_today={self._update_counts[today]}/{self.MAX_UPDATES_PER_DAY}"
        )
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

    def _compute_gradients(self, drift: DriftMetrics, content: str) -> list[str]:
        """
        Compute 4 structured pseudo-gradient directions based on error signals.
        These are NOT mathematical gradients — they are structural modification rules.
        """
        gradients = []

        # 1️⃣ Reduce Overconfidence Gradient
        # IF confidence ↑ AND error ↑ → soften language, add uncertainty
        if drift.epsilon_pred > 0.2:
            gradients.append(
                "Reduce deterministic language. Use probabilistic framing (may, might, appears, suggests)."
            )

        # 2️⃣ Simplify Attribution Gradient
        # IF attribution error high → reduce psychological constructs
        if drift.epsilon_attr > 0.2:
            gradients.append(
                "Move from causal explanations to possible factors. Avoid over-attribution of single drivers."
            )

        # 3️⃣ Stabilize Loop Gradient
        # IF loop unstable → reduce pattern-matching depth
        if drift.epsilon_loop > 0.3:
            gradients.append(
                "Shorten feedback cycle window. Reduce causal graph depth. Allow behavioral novelty."
            )

        # 4️⃣ Correct Attention Bias Gradient
        # Detect if prompt over-weights specific attention domains
        attention_domains = ["career", "relationship", "finance", "identity", "spirituality", "health"]
        domain_counts = {d: content.lower().count(d) for d in attention_domains}
        max_domain = max(domain_counts, key=domain_counts.get, default="")
        if domain_counts.get(max_domain, 0) > 3:
            gradients.append(
                f"Rebalance attention domain coverage. Reduce emphasis on '{max_domain}' to avoid bias."
            )

        return gradients

    def _compute_entropy(self, content: str) -> float:
        """Estimate prompt uncertainty via word distribution entropy."""
        import math
        words = content.lower().split()
        if not words:
            return 0.0
        from collections import Counter
        counts = Counter(words)
        total = len(words)
        entropy = 0.0
        for count in counts.values():
            p = count / total
            entropy -= p * math.log2(p)
        return round(entropy / math.log2(len(set(words)) + 1), 4) if len(set(words)) > 1 else 0.0

    def _inject_entropy(self, content: str) -> str:
        """Inject randomness when prompt becomes too deterministic."""
        uncertainty_phrases = [
            "Multiple interpretations are always possible.",
            "This is one of several valid readings.",
            "Consider that the pattern may be situational, not persistent.",
        ]
        return content + "\n- " + uncertainty_phrases[hash(content) % len(uncertainty_phrases)]

    def _has_forbidden_patterns(self, content: str) -> bool:
        """
        Semantic stability constraint.
        Block personality labels, deterministic predictions, moral judgments.
        """
        forbidden = [
            "you are a", "your personality is", "you are the type of",
            "will definitely", "will inevitably", "always will",
            "moral failure", "character flaw", "good person", "bad person",
        ]
        lower = content.lower()
        for pattern in forbidden:
            if pattern in lower:
                logger.warning(f"[prompt-engine] forbidden pattern detected: '{pattern}'")
                return True
        return False

    def _persist_drift_event(self, user_id: str, metrics: DriftMetrics, total_error: float):
        """Log drift event for system memory and tracking."""
        if not self._db_pool:
            return
        conn = self._db_pool.getconn()
        try:
            with conn.cursor() as cur:
                triggered = total_error >= self.DRIFT_THRESHOLD
                cur.execute(
                    """INSERT INTO mvfe_drift_events
                       (user_id, epsilon_pred, epsilon_attr, epsilon_loop, total_error, triggered_update, timestamp)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        user_id,
                        metrics.epsilon_pred,
                        metrics.epsilon_attr,
                        metrics.epsilon_loop,
                        round(total_error, 4),
                        triggered,
                        datetime.utcnow().isoformat(),
                    ),
                )
                conn.commit()
        except Exception as e:
            conn.rollback()
            logger.warning(f"[prompt-engine] drift event persist failed: {e}")
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
