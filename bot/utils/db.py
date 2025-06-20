from pymongo import MongoClient
import os
from typing import Optional, List
from db.models.player import Player
from db.models.queue import Queue, QueueEntry
from db.models.match import Match
from db.models.leaderboard import Leaderboard, LeaderboardEntry
from db.models.preferences import UserPreferences
from datetime import datetime, timezone

MONGO_URI = os.getenv("MONGODB_URI")

client = MongoClient(MONGO_URI)
db = client.valodiscordhub

db.user_preferences.create_index("discord_id", unique=True)

def get_player(discord_id: str) -> Optional[Player]:
    player_data = db.players.find_one({"discord_id": discord_id})
    if player_data:
        return Player(**player_data)
    return None

def create_player(discord_id: str, riot_id: str, rank: str) -> Player:
    player = Player(
        discord_id=discord_id,
        riot_id=riot_id,
        rank=rank
    )
    db.players.insert_one(player.model_dump())
    return player

def update_player_rank(discord_id: str, rank: str) -> Optional[Player]:
    result = db.players.find_one_and_update(
        {"discord_id": discord_id},
        {"$set": {"rank": rank}},
        return_document=True
    )
    if result:
        return Player(**result)
    return None

def get_queue(rank_group: str) -> Queue:
    queue_data = db.queues.find_one({"rank_group": rank_group})
    if queue_data:
        queue = Queue(**queue_data)
        original_players = queue.players
        
        filtered_players = [
            p for p in queue.players 
            if not is_player_banned(p.discord_id) and not is_player_timeout(p.discord_id)
        ]
        
        if len(filtered_players) != len(original_players):
            queue.players = filtered_players
            db.queues.update_one(
                {"rank_group": rank_group},
                {"$set": {"players": [p.model_dump() for p in filtered_players]}}
            )
        return queue
    return Queue(rank_group=rank_group)

def update_queue(rank_group: str, players: List[QueueEntry]) -> Queue:
    players = [
        p for p in players 
        if not is_player_banned(p.discord_id) and not is_player_timeout(p.discord_id)
    ]
    
    queue = Queue(rank_group=rank_group, players=players)
    db.queues.update_one(
        {"rank_group": rank_group},
        {"$set": queue.model_dump()},
        upsert=True
    )
    return queue

def add_to_queue(rank_group: str, discord_id: str) -> Queue:
    if is_player_banned(discord_id):
        raise ValueError("You are banned from the queue system")
    if is_player_timeout(discord_id):
        raise ValueError("You are in timeout and cannot join the queue")
        
    queue = get_queue(rank_group)
    if any(p.discord_id == discord_id for p in queue.players):
        raise ValueError("You are already in the queue")
    queue.players.append(QueueEntry(discord_id=discord_id))
    return update_queue(rank_group, queue.players)

def remove_player_from_queue(rank_group: str, discord_id: str) -> Queue:
    queue = get_queue(rank_group)
    if not any(p.discord_id == discord_id for p in queue.players):
        raise ValueError("You are not in the queue")
    queue.players = [p for p in queue.players if p.discord_id != discord_id]
    return update_queue(rank_group, queue.players)

def create_match(match_id: str, players_red: List[str], players_blue: List[str], 
                captain_red: str, captain_blue: str, lobby_master: str, rank_group: str) -> Match:
    match = Match(
        match_id=match_id,
        players_red=players_red,
        players_blue=players_blue,
        captain_red=captain_red,
        captain_blue=captain_blue,
        lobby_master=lobby_master,
        rank_group=rank_group
    )
    db.matches.insert_one(match.model_dump())
    return match

def update_match_teams(match_id: str, players_red: List[str], players_blue: List[str]) -> Optional[Match]:
    result = db.matches.find_one_and_update(
        {"match_id": match_id},
        {
            "$set": {
                "players_red": players_red,
                "players_blue": players_blue
            }
        },
        return_document=True
    )
    if result:
        return Match(**result)
    return None

def update_match_defense(match_id: str, defense_start: str) -> Optional[Match]:
    result = db.matches.find_one_and_update(
        {"match_id": match_id},
        {
            "$set": {
                "defense_start": defense_start
            }
        },
        return_document=True
    )
    if result:
        return Match(**result)
    return None

def update_match_result(match_id: str, red_score: int, blue_score: int, result: str) -> Optional[Match]:
    result = db.matches.find_one_and_update(
        {"match_id": match_id},
        {
            "$set": {
                "red_score": red_score,
                "blue_score": blue_score,
                "result": result,
                "ended_at": datetime.now(timezone.utc)
            }
        },
        return_document=True
    )
    if result:
        return Match(**result)
    return None

def get_match(match_id: str) -> Optional[Match]:
    match_data = db.matches.find_one({"match_id": match_id})
    if match_data:
        return Match(**match_data)
    return None

def get_active_matches() -> List[Match]:
    matches = db.matches.find({"result": None})
    return [Match(**match) for match in matches]

def get_leaderboard(rank_group: str) -> Leaderboard:
    leaderboard_data = db.leaderboards.find_one({"rank_group": rank_group})
    if leaderboard_data:
        leaderboard = Leaderboard(**leaderboard_data)
        leaderboard.players = [
            player for player in leaderboard.players 
            if not is_player_banned(player.discord_id)
        ]
        return leaderboard
    return Leaderboard(rank_group=rank_group)

def update_leaderboard(rank_group: str, players: List[LeaderboardEntry]) -> Leaderboard:
    leaderboard = Leaderboard(rank_group=rank_group, players=players)
    db.leaderboards.update_one(
        {"rank_group": rank_group},
        {"$set": leaderboard.model_dump()},
        upsert=True
    )
    return leaderboard

def get_player_rank(rank_group: str, discord_id: str) -> Optional[LeaderboardEntry]:
    leaderboard = get_leaderboard(rank_group)
    for player in leaderboard.players:
        if player.discord_id == discord_id:
            return player
    return None

def get_leaderboard_page(rank_group: str, page: int = 1, page_size: int = 10) -> List[LeaderboardEntry]:
    leaderboard = get_leaderboard(rank_group)
    sorted_players = sorted(leaderboard.players, key=lambda x: x.points, reverse=True)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    return sorted_players[start_idx:end_idx]

def get_total_pages(rank_group: str, page_size: int = 10) -> int:
    leaderboard = get_leaderboard(rank_group)
    return (len(leaderboard.players) + page_size - 1) // page_size

def get_match_history(limit: Optional[int] = 10) -> List[Match]:
    query = {"ended_at": {"$exists": True}}
    sort = [("ended_at", 1)]
    
    if limit is not None:
        matches = db.matches.find(query, sort=sort, limit=limit)
    else:
        matches = db.matches.find(query, sort=sort)
        
    return [Match(**match) for match in matches]

def get_banned_players() -> List[dict]:
    return list(db.admin_logs.find(
        {"action": "ban", "target_discord_id": {"$exists": True}},
        {"target_discord_id": 1, "reason": 1, "timestamp": 1}
    ))

def get_timeout_players() -> List[dict]:
    return list(db.admin_logs.find(
        {"action": "timeout", "target_discord_id": {"$exists": True}},
        {"target_discord_id": 1, "reason": 1, "duration_minutes": 1, "timestamp": 1}
    ))

def is_player_banned(discord_id: str) -> bool:
    return bool(db.admin_logs.find_one(
        {"action": "ban", "target_discord_id": discord_id}
    ))

def is_player_timeout(discord_id: str) -> bool:
    timeout = db.admin_logs.find_one(
        {"action": "timeout", "target_discord_id": discord_id}
    )
    if not timeout:
        return False
    
    timeout_time = timeout["timestamp"]
    if timeout_time.tzinfo is None:
        timeout_time = timeout_time.replace(tzinfo=timezone.utc)
    duration = timeout["duration_minutes"]
    current_time = datetime.now(timezone.utc)
    
    time_diff = (current_time - timeout_time).total_seconds() / 60.0
    
    if time_diff >= duration:
        remove_admin_log("timeout", discord_id)
        return False
        
    return time_diff < duration

def add_admin_log(action: str, admin_discord_id: str, target_discord_id: Optional[str] = None, 
                 match_id: Optional[str] = None, reason: Optional[str] = None, 
                 duration_minutes: Optional[int] = None) -> None:
    log = {
        "action": action,
        "admin_discord_id": admin_discord_id,
        "target_discord_id": target_discord_id,
        "match_id": match_id,
        "reason": reason,
        "duration_minutes": duration_minutes,
        "timestamp": datetime.now(timezone.utc)
    }
    db.admin_logs.insert_one(log)

def remove_admin_log(action: str, target_discord_id: str) -> None:
    db.admin_logs.delete_one(
        {"action": action, "target_discord_id": target_discord_id}
    )

def save_user_preferences(prefs: UserPreferences) -> None:
    db.user_preferences.update_one(
        {"discord_id": prefs.discord_id},
        {"$set": prefs.model_dump()},
        upsert=True
    )

def get_user_preferences(discord_id: str) -> Optional[UserPreferences]:
    prefs_data = db.user_preferences.find_one({"discord_id": discord_id})
    if prefs_data:
        return UserPreferences(**prefs_data)
    return None