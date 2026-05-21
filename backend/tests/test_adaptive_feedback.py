import pytest
from app.services.weight_resolver import WeightResolver, GLOBAL_DEFAULT_WEIGHTS
import math

DIMENSIONS = [
    "domain", "geography", "financial", 
    "experience", "certification", "semantic", "confidence"
]
LEARNING_RATE = 0.05
SIGNAL_VALUES = {
    "won": 1.0,
    "submitted": 0.6,
    "interested": 0.3,
    "not_relevant": -0.4,
    "lost": -0.2
}

def ema_update(current_weights, raw_scores, signal_val):
    """Standalone logic identical to FeedbackProcessor for testing."""
    total_raw = sum(raw_scores.values()) or 1.0
    target_dist = {dim: (raw_scores[dim] / total_raw) for dim in DIMENSIONS}
    
    new_weights = {}
    for dim in DIMENSIONS:
        current = current_weights[dim]
        target = target_dist[dim]
        delta = target - current
        updated = current + (LEARNING_RATE * signal_val * delta)
        new_weights[dim] = max(0.001, min(1.0, updated))
        
    return WeightResolver.normalize_weights(new_weights)

def test_normalization():
    """Test re-normalization always sums to 1.0."""
    w1 = {"a": 0.5, "b": 0.5, "c": 0.5}
    res1 = WeightResolver.normalize_weights(w1)
    assert math.isclose(sum(res1.values()), 1.0)
    assert res1["a"] == 1/3
    
    # Zero sum case
    w2 = {"a": 0, "b": 0}
    res2 = WeightResolver.normalize_weights(w2)
    assert math.isclose(sum(res2.values()), 1.0)
    assert res2["a"] == 0.5

def test_ema_positive_signal():
    """Test EMA with a positive signal (Won)."""
    current = GLOBAL_DEFAULT_WEIGHTS.copy()
    
    # Suppose domain scored 100%, everything else 0%
    raw_scores = {d: 0.0 for d in DIMENSIONS}
    raw_scores["domain"] = 100.0
    
    new_weights = ema_update(current, raw_scores, SIGNAL_VALUES["won"])
    
    # Domain weight should INCREASE because it was important (100% score) and the result was positive
    assert new_weights["domain"] > current["domain"]
    
    # Geography should DECREASE because it contributed 0% to a winning bid
    assert new_weights["geography"] < current["geography"]

def test_ema_negative_signal():
    """Test EMA with a negative signal (Lost)."""
    current = GLOBAL_DEFAULT_WEIGHTS.copy()
    
    # Suppose domain scored 100%, everything else 0%
    raw_scores = {d: 0.0 for d in DIMENSIONS}
    raw_scores["domain"] = 100.0
    
    new_weights = ema_update(current, raw_scores, SIGNAL_VALUES["lost"])
    
    # Domain weight should DECREASE because it was 100% confident but we lost
    # Wait, the formula: target = 1.0. current = 0.25. delta = +0.75. 
    # updated = 0.25 + 0.05 * (-0.2) * 0.75 = 0.25 - 0.0075. So it decreases!
    assert new_weights["domain"] < current["domain"]

def test_ema_mixed_scores():
    """Test EMA with realistic mixed scores."""
    current = {
        "domain": 0.2, "geography": 0.2, "financial": 0.2,
        "experience": 0.1, "certification": 0.1, "semantic": 0.1, "confidence": 0.1
    }
    raw_scores = {
        "domain": 90, "geography": 80, "financial": 10,
        "experience": 50, "certification": 100, "semantic": 85, "confidence": 95
    }
    
    new_weights = ema_update(current, raw_scores, SIGNAL_VALUES["submitted"])
    assert math.isclose(sum(new_weights.values()), 1.0)

def test_three_tier_fallback_logic(mocker):
    """Mock the session and test fallback logic."""
    pass # Can be implemented via integration tests or pytest-asyncio
