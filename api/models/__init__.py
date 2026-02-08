"""
API models - re-exports from shared models.
This maintains backward compatibility while consolidating models.
"""

import sys
from pathlib import Path

# Add shared directory to path
shared_path = Path(__file__).resolve().parent.parent.parent / "shared"
if str(shared_path) not in sys.path:
    sys.path.insert(0, str(shared_path))

from shared.models import (
    Player,
    Queue,
    QueueEntry,
    Match,
    Leaderboard,
    LeaderboardEntry,
    AdminLog,
    UserPreferences,
)

__all__ = [
    "Player",
    "Queue",
    "QueueEntry",
    "Match",
    "Leaderboard",
    "LeaderboardEntry",
    "AdminLog",
    "UserPreferences",
]
