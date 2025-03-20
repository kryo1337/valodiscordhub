from pymongo import MongoClient
import os
from typing import Optional
from db.models.player import Player

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