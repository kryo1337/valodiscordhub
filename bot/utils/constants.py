"""
Constants for ValoDiscordHub bot.
Centralized location for hardcoded strings to improve maintainability.
"""

from enum import Enum


class RankGroup(str, Enum):
    IRON_PLAT = "iron-plat"
    DIA_ASC = "dia-asc"
    IMM_RADIANT = "imm-radiant"


ALL_RANK_GROUPS = [
    RankGroup.IRON_PLAT.value,
    RankGroup.DIA_ASC.value,
    RankGroup.IMM_RADIANT.value,
]


class Category(str, Enum):
    HUB = "Hub"
    STAFF = "Staff"
    MATCHES = "Matches"


class Channel(str, Enum):
    ADMIN_PANEL = "admin-panel"
    ADMIN_RANKS = "admin-ranks"
    LEADERBOARD = "leaderboard"
    RANK = "rank"
    HISTORY = "history"
    STATS = "stats"


class QueueChannel(str, Enum):
    QUEUE_IRON_PLAT = "queue-iron-plat"
    QUEUE_DIA_ASC = "queue-dia-asc"
    QUEUE_IMM_RADIANT = "queue-imm-radiant"


class QueueColors:
    IRON_PLAT = "blue"
    DIA_ASC = "green"
    IMM_RADIANT = "red"


class Command(str, Enum):
    TEST_QUEUE = "test_queue"
    SETUP_QUEUE = "setup_queue"
    CLEAR_QUEUE = "clear_queue"
    SET_RESULT = "set_result"
    SETUP_ADMIN = "setup_admin"
    BAN = "ban"
    TIMEOUT = "timeout"
    UNBAN = "unban"
    SET_RANK = "set_rank"
    SET_POINTS = "set_points"
    REFRESH_ALL = "refresh_all"
    SETUP_ALL = "setup_all"
    LIST_BANS = "list_bans"
    LIST_TIMEOUTS = "list_timeouts"
    RANK_TICKETS = "rank_tickets"


class QueueLimit:
    MAX_PLAYERS = 10


class MatchResult(str, Enum):
    RED = "red"
    BLUE = "blue"
    CANCELLED = "cancelled"


class Score:
    MIN = 0
    MAX = 13


class ProgressBar:
    FILLED = "▰"
    EMPTY = "▱"
    TOTAL_SEGMENTS = 10
