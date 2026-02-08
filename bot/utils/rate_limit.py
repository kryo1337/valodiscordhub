from datetime import datetime, timezone
from typing import Dict, Optional
from collections import defaultdict


class RateLimiter:
    def __init__(self):
        self._cooldowns: Dict[str, Dict[str, datetime]] = defaultdict(dict)
        self._default_cooldowns = {
            "queue": 5,
            "rank": 300,
            "stats": 60,
        }

    def is_rate_limited(self, user_id: str, command: str) -> tuple[bool, Optional[int]]:
        if command not in self._default_cooldowns:
            return False, None

        cooldown = self._default_cooldowns[command]
        last_used = self._cooldowns[command].get(user_id)

        if not last_used:
            return False, None

        time_diff = (datetime.now(timezone.utc) - last_used).total_seconds()
        if time_diff < cooldown:
            return True, int(cooldown - time_diff)

        return False, None

    def update_cooldown(self, user_id: str, command: str) -> None:
        if command in self._default_cooldowns:
            self._cooldowns[command][user_id] = datetime.now(timezone.utc)

    def clear_cooldown(self, user_id: str, command: str) -> None:
        if command in self._cooldowns:
            self._cooldowns[command].pop(user_id, None)


rate_limiter = RateLimiter()
