from pymongo import MongoClient
import os
from typing import Optional, List
from db.models.player import Player
from db.models.queue import Queue, QueueEntry
from db.models.match import Match
from db.models.leaderboard import Leaderboard, LeaderboardEntry
from datetime import datetime, timezone

MONGO_URI = os.getenv("MONGODB_URI")

client = MongoClient(MONGO_URI)
db = client.valodiscordhub

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
        return Queue(**queue_data)
    return Queue(rank_group=rank_group)

def update_queue(rank_group: str, players: List[QueueEntry]) -> Queue:
    queue = Queue(rank_group=rank_group, players=players)
    db.queues.update_one(
        {"rank_group": rank_group},
        {"$set": queue.model_dump()},
        upsert=True
    )
    return queue

def add_to_queue(rank_group: str, discord_id: str) -> Queue:
    queue = get_queue(rank_group)
    queue.players.append(QueueEntry(discord_id=discord_id))
    return update_queue(rank_group, queue.players)

def remove_player_from_queue(rank_group: str, discord_id: str) -> Queue:
    queue = get_queue(rank_group)
    queue.players = [p for p in queue.players if p.discord_id != discord_id]
    return update_queue(rank_group, queue.players)

def create_match(match_id: str, players_red: List[str], players_blue: List[str], 
                captain_red: str, captain_blue: str, lobby_master: str) -> Match:
    match = Match(
        match_id=match_id,
        players_red=players_red,
        players_blue=players_blue,
        captain_red=captain_red,
        captain_blue=captain_blue,
        lobby_master=lobby_master
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
        return Leaderboard(**leaderboard_data)
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

def get_players_by_rank_group(rank_group: str) -> List[Player]:
    if rank_group == "iron-plat":
        ranks = ["Iron", "Bronze", "Silver", "Gold", "Platinum"]
    elif rank_group == "dia-asc":
        ranks = ["Diamond", "Ascendant"]
    elif rank_group == "imm-radiant":
        ranks = ["Immortal", "Radiant"]
    else:
        return []
    
    players = db.players.find({"rank": {"$in": ranks}})
    return [Player(**player) for player in players] 