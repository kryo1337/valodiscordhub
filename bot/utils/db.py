from typing import Optional, List
from models.player import Player
from models.queue import Queue, QueueEntry
from models.match import Match
from models.leaderboard import Leaderboard, LeaderboardEntry
from models.preferences import UserPreferences
from datetime import datetime, timezone
from dotenv import load_dotenv
from .api_client import api_client

load_dotenv()

async def get_player(discord_id: str) -> Optional[Player]:
    try:
        data = await api_client.get(f"/players/{discord_id}")
        return Player(**data)
    except Exception:
        return None

async def create_player(discord_id: str, riot_id: str, rank: str) -> Player:
    player_data = {
        "discord_id": discord_id,
        "riot_id": riot_id,
        "rank": rank
    }
    data = await api_client.post("/players/", player_data)
    return Player(**data)

async def update_player_rank(discord_id: str, rank: str) -> Optional[Player]:
    try:
        data = await api_client.patch(f"/players/{discord_id}", {"rank": rank})
        return Player(**data)
    except Exception:
        return None

async def get_queue(rank_group: str) -> Queue:
    try:
        data = await api_client.get(f"/queue/{rank_group}")
        queue = Queue(**data)
        filtered_players = [
            p for p in queue.players 
            if not await is_player_banned(p.discord_id) and not await is_player_timeout(p.discord_id)
        ]
        if len(filtered_players) != len(queue.players):
            queue.players = filtered_players
        return queue
    except Exception:
        return Queue(rank_group=rank_group)

async def update_queue(rank_group: str, players: List[QueueEntry]) -> Queue:
    players = [
        p for p in players 
        if not await is_player_banned(p.discord_id) and not await is_player_timeout(p.discord_id)
    ]
    
    queue = Queue(rank_group=rank_group, players=players)
    data = await api_client.put(f"/queue/{rank_group}", queue.dict())
    return Queue(**data)

async def add_to_queue(rank_group: str, discord_id: str) -> Queue:
    if await is_player_banned(discord_id):
        raise ValueError("You are banned from the queue system")
    if await is_player_timeout(discord_id):
        raise ValueError("You are in timeout and cannot join the queue")
        
    queue = await get_queue(rank_group)
    if any(p.discord_id == discord_id for p in queue.players):
        raise ValueError("You are already in the queue")
    
    entry_data = {"discord_id": discord_id}
    data = await api_client.post(f"/queue/{rank_group}/join", entry_data)
    return Queue(**data)

async def remove_player_from_queue(rank_group: str, discord_id: str) -> Queue:
    queue = await get_queue(rank_group)
    if not any(p.discord_id == discord_id for p in queue.players):
        raise ValueError("You are not in the queue")
    
    entry_data = {"discord_id": discord_id}
    data = await api_client.post(f"/queue/{rank_group}/leave", entry_data)
    return Queue(**data)

async def create_match(match_id: str, players_red: List[str], players_blue: List[str], 
                captain_red: str, captain_blue: str, lobby_master: str, rank_group: str) -> Match:
    match_data = {
        "match_id": match_id,
        "players_red": players_red,
        "players_blue": players_blue,
        "captain_red": captain_red,
        "captain_blue": captain_blue,
        "lobby_master": lobby_master,
        "rank_group": rank_group
    }
    data = await api_client.post("/matches/", match_data)
    return Match(**data)

async def update_match_teams(match_id: str, players_red: List[str], players_blue: List[str]) -> Optional[Match]:
    try:
        data = await api_client.patch(f"/matches/{match_id}", {
            "players_red": players_red,
            "players_blue": players_blue
        })
        return Match(**data)
    except Exception:
        return None

async def update_match_defense(match_id: str, defense_start: str) -> Optional[Match]:
    try:
        data = await api_client.patch(f"/matches/{match_id}", {
            "defense_start": defense_start
        })
        return Match(**data)
    except Exception:
        return None

async def update_match_result(match_id: str, red_score: int, blue_score: int, result: str) -> Optional[Match]:
    try:
        update_data = {
            "red_score": red_score,
            "blue_score": blue_score,
            "result": result,
            "ended_at": datetime.now(timezone.utc).isoformat()
        }
        data = await api_client.patch(f"/matches/{match_id}", update_data)
        return Match(**data)
    except Exception:
        return None

async def get_match(match_id: str) -> Optional[Match]:
    try:
        data = await api_client.get(f"/matches/{match_id}")
        return Match(**data)
    except Exception:
        return None

async def get_active_matches() -> List[Match]:
    try:
        data = await api_client.get("/matches/active")
        return [Match(**match) for match in data]
    except Exception:
        return []

async def get_leaderboard(rank_group: str) -> Leaderboard:
    try:
        data = await api_client.get(f"/leaderboard/{rank_group}")
        leaderboard = Leaderboard(**data)
        leaderboard.players = [
            player for player in leaderboard.players 
            if not await is_player_banned(player.discord_id)
        ]
        return leaderboard
    except Exception:
        return Leaderboard(rank_group=rank_group)

async def update_leaderboard(rank_group: str, players: List[LeaderboardEntry]) -> Leaderboard:
    leaderboard = Leaderboard(rank_group=rank_group, players=players)
    data = await api_client.put(f"/leaderboard/{rank_group}", leaderboard.dict())
    return Leaderboard(**data)

async def get_player_rank(rank_group: str, discord_id: str) -> Optional[LeaderboardEntry]:
    leaderboard = await get_leaderboard(rank_group)
    for player in leaderboard.players:
        if player.discord_id == discord_id:
            return player
    return None

async def get_leaderboard_page(rank_group: str, page: int = 1, page_size: int = 10) -> List[LeaderboardEntry]:
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
        data = await api_client.get("/matches/history", params)
        return [Match(**match) for match in data]
    except Exception:
        return []

async def get_banned_players() -> List[dict]:
    try:
        data = await api_client.get("/admin/bans")
        return data
    except Exception:
        return []

async def get_timeout_players() -> List[dict]:
    try:
        data = await api_client.get("/admin/timeouts")
        return data
    except Exception:
        return []

async def is_player_banned(discord_id: str) -> bool:
    try:
        data = await api_client.get(f"/admin/check-ban/{discord_id}")
        return data
    except Exception:
        return False

async def is_player_timeout(discord_id: str) -> bool:
    try:
        data = await api_client.get(f"/admin/check-timeout/{discord_id}")
        return data
    except Exception:
        return False

async def add_admin_log(action: str, admin_discord_id: str, target_discord_id: Optional[str] = None, 
                 match_id: Optional[str] = None, reason: Optional[str] = None, 
                 duration_minutes: Optional[int] = None) -> None:
    log_data = {
        "action": action,
        "admin_discord_id": admin_discord_id,
        "target_discord_id": target_discord_id,
        "match_id": match_id,
        "reason": reason,
        "duration_minutes": duration_minutes
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
    except Exception:
        pass

async def save_user_preferences(prefs: UserPreferences) -> None:
    try:
        await api_client.patch(f"/preferences/{prefs.discord_id}", prefs.dict())
    except Exception:
        pass

async def get_user_preferences(discord_id: str) -> Optional[UserPreferences]:
    try:
        data = await api_client.get(f"/preferences/{discord_id}")
        return UserPreferences(**data)
    except Exception:
        return None