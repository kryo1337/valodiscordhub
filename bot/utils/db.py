from typing import Optional, List, Tuple, Dict
from models.player import Player
from models.queue import Queue, QueueEntry
from models.match import Match
from models.leaderboard import Leaderboard, LeaderboardEntry
from models.preferences import UserPreferences
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv
from .api_client import api_client
import time
import asyncio

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")


async def get_player(discord_id: str) -> Optional[Player]:
    try:
        data = await api_client.get(f"/players/{discord_id}")
        return Player(**data)
    except (ValueError, ConnectionError, KeyError):
        return None


async def create_player(discord_id: str, riot_id: str, rank: str) -> Player:
    player_data = {"discord_id": discord_id, "riot_id": riot_id, "rank": rank}
    data = await api_client.post("/players/", player_data)
    return Player(**data)


async def update_player_rank(discord_id: str, rank: str) -> Optional[Player]:
    try:
        data = await api_client.patch(f"/players/{discord_id}", {"rank": rank})
        return Player(**data)
    except (ValueError, ConnectionError, KeyError):
        return None


async def get_player_stats(
    discord_id: str, rank_group: Optional[str] = None
) -> Optional[dict]:
    try:
        params = {"rank_group": rank_group} if rank_group else None
        data = await api_client.get(f"/stats/{discord_id}", params)
        return data
    except (ValueError, ConnectionError, KeyError):
        return None


async def get_queue(rank_group: str) -> Queue:
    try:
        data = await api_client.get(f"/queue/{rank_group}")
        queue = Queue(**data)

        if not queue.players:
            return queue

        player_ids = [p.discord_id for p in queue.players]
        bans, timeouts = await batch_check_players(player_ids)

        filtered_players = []
        seen_ids = set()
        for p in queue.players:
            if p.discord_id in seen_ids:
                continue
            if bans.get(p.discord_id, False):
                continue
            if timeouts.get(p.discord_id, False):
                continue
            seen_ids.add(p.discord_id)
            filtered_players.append(p)

        if len(filtered_players) != len(queue.players):
            queue.players = filtered_players
        return queue
    except (ValueError, ConnectionError, KeyError, TypeError):
        return Queue(rank_group=rank_group)


async def update_queue(rank_group: str, players: List[QueueEntry]) -> Queue:
    if players:
        player_ids = [p.discord_id for p in players]
        bans, timeouts = await batch_check_players(player_ids)

        players = [
            p
            for p in players
            if not bans.get(p.discord_id, False)
            and not timeouts.get(p.discord_id, False)
        ]

    queue = Queue(rank_group=rank_group, players=players)
    data = await api_client.put(f"/queue/{rank_group}", queue.model_dump(mode="json"))
    return Queue(**data)


async def clear_queue(rank_group: str) -> Queue:
    data = await api_client.delete(f"/queue/{rank_group}")
    return Queue(**data)


async def delete_test_bots() -> int:
    data = await api_client.delete("/players/test-bots")
    return data.get("deleted_count", 0)


async def add_to_queue(rank_group: str, discord_id: str) -> Queue:
    if await is_player_banned(discord_id):
        raise ValueError("You are banned from the queue system")
    if await is_player_timeout(discord_id):
        raise ValueError("You are in timeout and cannot join the queue")
    if await is_player_in_match(discord_id):
        raise ValueError(
            "You are currently in an active match and cannot join the queue"
        )

    queue = await get_queue(rank_group)
    if any(p.discord_id == discord_id for p in queue.players):
        raise ValueError("You are already in the queue")

    entry_data = {"discord_id": discord_id}
    data = await api_client.post(f"/queue/{rank_group}/join", entry_data)
    return Queue(**data)


async def remove_player_from_queue(rank_group: str, discord_id: str) -> Queue:
    entry_data = {"discord_id": discord_id}
    data = await api_client.post(f"/queue/{rank_group}/leave", entry_data)
    return Queue(**data)


def calculate_mmr_points(
    team1_avg: float, team2_avg: float, team1_won: bool, base_points: int = 25
) -> Tuple[int, int]:
    mmr_diff = team1_avg - team2_avg

    adjustment = int(mmr_diff / 60)

    if team1_won:
        team1_points = base_points - adjustment
        team2_points = -(base_points + adjustment)
    else:
        team1_points = -(base_points + adjustment)
        team2_points = base_points - adjustment

    team1_points = max(20, min(30, team1_points))
    team2_points = max(-30, min(-20, team2_points))

    return team1_points, team2_points


async def get_next_match_id() -> str:
    try:
        data = await api_client.get("/matches/next-id")
        return data["match_id"]
    except (ValueError, ConnectionError, KeyError):
        try:
            matches = await api_client.get("/matches/active")
            match_numbers = []
            for match in matches:
                match_id = match.get("match_id", "")
                if match_id.startswith("match_"):
                    try:
                        num = int(match_id.split("_")[1])
                        match_numbers.append(num)
                    except (IndexError, ValueError):
                        continue
            next_num = max(match_numbers, default=0) + 1
            return f"match_{next_num}"
        except (ValueError, ConnectionError, KeyError):
            return "match_1"


async def create_match(
    match_id: str,
    players_red: List[str],
    players_blue: List[str],
    captain_red: str,
    captain_blue: str,
    lobby_master: str,
    rank_group: str,
) -> Match:
    match_data = {
        "match_id": match_id,
        "players_red": players_red,
        "players_blue": players_blue,
        "captain_red": captain_red,
        "captain_blue": captain_blue,
        "lobby_master": lobby_master,
        "rank_group": rank_group,
    }
    data = await api_client.post("/matches/", match_data)
    return Match(**data)


async def update_match_teams(
    match_id: str, players_red: List[str], players_blue: List[str]
) -> Optional[Match]:
    try:
        data = await api_client.patch(
            f"/matches/{match_id}",
            {"players_red": players_red, "players_blue": players_blue},
        )
        return Match(**data)
    except (ValueError, ConnectionError, KeyError):
        return None


async def update_match_defense(match_id: str, defense_start: str) -> Optional[Match]:
    try:
        data = await api_client.patch(
            f"/matches/{match_id}", {"defense_start": defense_start}
        )
        return Match(**data)
    except (ValueError, ConnectionError, KeyError):
        return None


async def update_match_maps(
    match_id: str, banned_maps: List[str], selected_map: str
) -> Optional[Match]:
    try:
        data = await api_client.patch(
            f"/matches/{match_id}",
            {"banned_maps": banned_maps, "selected_map": selected_map},
        )
        return Match(**data)
    except (ValueError, ConnectionError, KeyError):
        return None


async def update_match_result(
    match_id: str, red_score: int, blue_score: int, result: str
) -> Optional[Match]:
    try:
        update_data = {
            "red_score": red_score,
            "blue_score": blue_score,
            "result": result,
            "ended_at": datetime.now(timezone.utc).isoformat(),
        }
        data = await api_client.patch(f"/matches/{match_id}", update_data)
        return Match(**data)
    except (ValueError, ConnectionError, KeyError):
        return None


async def get_match(match_id: str) -> Optional[Match]:
    try:
        data = await api_client.get(f"/matches/{match_id}")
        return Match(**data)
    except (ValueError, ConnectionError, KeyError):
        return None


async def get_active_matches() -> List[Match]:
    global _ACTIVE_MATCHES_CACHE, _ACTIVE_MATCHES_CACHE_TIME
    now = time.monotonic()
    if now - _ACTIVE_MATCHES_CACHE_TIME < _ACTIVE_MATCHES_CACHE_TTL_SECONDS:
        return _ACTIVE_MATCHES_CACHE

    try:
        data = await api_client.get("/matches/active")
        _ACTIVE_MATCHES_CACHE = [Match(**match) for match in data]
        _ACTIVE_MATCHES_CACHE_TIME = now
        return _ACTIVE_MATCHES_CACHE
    except Exception:
        return _ACTIVE_MATCHES_CACHE


async def is_player_in_match(discord_id: str) -> bool:
    try:
        active_matches = await get_active_matches()
        for match in active_matches:
            if match.players_red and discord_id in match.players_red:
                return True
            if match.players_blue and discord_id in match.players_blue:
                return True
        return False
    except (ValueError, ConnectionError, KeyError, TypeError):
        return False


async def get_leaderboard(rank_group: str) -> Leaderboard:
    try:
        data = await api_client.get(f"/leaderboard/{rank_group}")
        leaderboard = Leaderboard(**data)
        leaderboard.players = [
            player
            for player in leaderboard.players
            if not await is_player_banned(player.discord_id)
        ]
        return leaderboard
    except (ValueError, ConnectionError, KeyError, TypeError):
        return Leaderboard(rank_group=rank_group)


async def update_leaderboard(
    rank_group: str, players: List[LeaderboardEntry]
) -> Leaderboard:
    leaderboard = Leaderboard(rank_group=rank_group, players=players)
    data = await api_client.put(
        f"/leaderboard/{rank_group}", leaderboard.model_dump(mode="json")
    )
    return Leaderboard(**data)


async def get_player_rank(
    rank_group: str, discord_id: str
) -> Optional[LeaderboardEntry]:
    leaderboard = await get_leaderboard(rank_group)
    for player in leaderboard.players:
        if player.discord_id == discord_id:
            return player
    return None


async def get_leaderboard_page(
    rank_group: str, page: int = 1, page_size: int = 10
) -> List[LeaderboardEntry]:
    leaderboard = await get_leaderboard(rank_group)
    sorted_players = sorted(leaderboard.players, key=lambda x: x.points, reverse=True)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    return sorted_players[start_idx:end_idx]


async def get_total_pages(rank_group: str, page_size: int = 10) -> int:
    leaderboard = await get_leaderboard(rank_group)
    return (len(leaderboard.players) + page_size - 1) // page_size


async def get_match_history(limit: Optional[int] = 10) -> List[Match]:
    try:
        params = {"limit": limit} if limit is not None else {}
        data = await api_client.get("/history/matches", params)
        return [Match(**match) for match in data]
    except (ValueError, ConnectionError, KeyError, TypeError):
        return []


async def get_player_match_history(
    discord_id: str, limit: Optional[int] = 10
) -> List[Match]:
    try:
        params = {"limit": limit} if limit is not None else {}
        data = await api_client.get(f"/history/matches/player/{discord_id}", params)
        return [Match(**match) for match in data]
    except (ValueError, ConnectionError, KeyError, TypeError):
        return []


async def get_banned_players() -> List[dict]:
    try:
        data = await api_client.get("/admin/bans")
        return data
    except (ValueError, ConnectionError, KeyError, TypeError):
        return []


async def get_timeout_players() -> List[dict]:
    try:
        data = await api_client.get("/admin/timeouts")
        return data
    except (ValueError, ConnectionError, KeyError, TypeError):
        return []


_BAN_CACHE: Dict[str, Tuple[bool, float]] = {}
_TIMEOUT_CACHE: Dict[str, Tuple[bool, float]] = {}
_SANCTION_TTL_SECONDS = 60.0

_ACTIVE_MATCHES_CACHE: List[Match] = []
_ACTIVE_MATCHES_CACHE_TIME: float = 0.0
_ACTIVE_MATCHES_CACHE_TTL_SECONDS = 30.0


async def batch_check_players(
    discord_ids: List[str],
) -> Tuple[Dict[str, bool], Dict[str, bool]]:
    now = time.monotonic()
    bans = {}
    timeouts = {}

    uncached_ids = []
    for discord_id in discord_ids:
        ban_cached = _BAN_CACHE.get(discord_id)
        timeout_cached = _TIMEOUT_CACHE.get(discord_id)

        if ban_cached and now < ban_cached[1]:
            bans[discord_id] = ban_cached[0]
        else:
            uncached_ids.append(discord_id)

        if timeout_cached and now < timeout_cached[1]:
            timeouts[discord_id] = timeout_cached[0]

    if uncached_ids:
        try:
            data = await api_client.post(
                "/admin/check-batch", {"discord_ids": uncached_ids}
            )
            for discord_id in uncached_ids:
                if discord_id in data.get("bans", {}):
                    bans[discord_id] = bool(data["bans"][discord_id])
                    _BAN_CACHE[discord_id] = (
                        bans[discord_id],
                        now + _SANCTION_TTL_SECONDS,
                    )

                if discord_id in data.get("timeouts", {}):
                    timeouts[discord_id] = bool(data["timeouts"][discord_id])
                    _TIMEOUT_CACHE[discord_id] = (
                        timeouts[discord_id],
                        now + _SANCTION_TTL_SECONDS,
                    )
        except (ValueError, ConnectionError, KeyError):
            pass

    return bans, timeouts


async def is_player_banned(discord_id: str) -> bool:
    now = time.monotonic()
    cached = _BAN_CACHE.get(discord_id)
    if cached and (now < cached[1]):
        return cached[0]
    try:
        data = await api_client.get(f"/admin/check-ban/{discord_id}")
        _BAN_CACHE[discord_id] = (bool(data), now + _SANCTION_TTL_SECONDS)
        return bool(data)
    except (ValueError, ConnectionError):
        return cached[0] if cached else False


async def is_player_timeout(discord_id: str) -> bool:
    now = time.monotonic()
    cached = _TIMEOUT_CACHE.get(discord_id)
    if cached and (now < cached[1]):
        return cached[0]
    try:
        data = await api_client.get(f"/admin/check-timeout/{discord_id}")
        _TIMEOUT_CACHE[discord_id] = (bool(data), now + _SANCTION_TTL_SECONDS)
        return bool(data)
    except (ValueError, ConnectionError):
        return cached[0] if cached else False


async def add_admin_log(
    action: str,
    admin_discord_id: str,
    target_discord_id: Optional[str] = None,
    match_id: Optional[str] = None,
    reason: Optional[str] = None,
    duration_minutes: Optional[int] = None,
) -> None:
    log_data = {
        "action": action,
        "admin_discord_id": admin_discord_id,
        "target_discord_id": target_discord_id,
        "match_id": match_id,
        "reason": reason,
        "duration_minutes": duration_minutes,
    }

    if action == "ban":
        await api_client.post("/admin/ban", log_data)
    elif action == "timeout":
        await api_client.post("/admin/timeout", log_data)
    elif action == "unban":
        await api_client.post("/admin/unban", log_data)


async def remove_admin_log(action: str, target_discord_id: str) -> None:
    try:
        await api_client.delete(f"/admin/logs/{action}/{target_discord_id}")
    except (ValueError, ConnectionError):
        pass


async def save_user_preferences(prefs: UserPreferences) -> None:
    try:
        await api_client.patch(f"/preferences/{prefs.discord_id}", prefs.dict())
    except (ValueError, ConnectionError):
        pass


async def get_user_preferences(discord_id: str) -> Optional[UserPreferences]:
    try:
        data = await api_client.get(f"/preferences/{discord_id}")
        return UserPreferences(**data)
    except (ValueError, ConnectionError, KeyError):
        return None
