from pymongo import MongoClient
import os
from typing import Optional, List
from db.models.player import Player
from db.models.queue import Queue, QueueEntry

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

def remove_from_queue(rank_group: str, count: int = 10) -> List[QueueEntry]:
    queue = get_queue(rank_group)
    removed_players = queue.players[:count]
    queue.players = queue.players[count:]
    update_queue(rank_group, queue.players)
    return removed_players

def remove_player_from_queue(rank_group: str, discord_id: str) -> Queue:
    queue = get_queue(rank_group)
    queue.players = [p for p in queue.players if p.discord_id != discord_id]
    return update_queue(rank_group, queue.players) 