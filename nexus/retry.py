import random

def calculate_backoff(attempt: int, base_seconds: float = 1.0, max_seconds: float = 60.0) -> float:
    """
    Calculates exponential backoff with full jitter to avoid thundering herd problem.
    """
    factor = 2 ** attempt
    backoff = min(max_seconds, base_seconds * factor)
    # Full jitter: random sleep between 0 and backoff
    return random.uniform(0.5 * backoff, backoff)
