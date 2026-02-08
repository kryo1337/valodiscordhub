from pydantic import BaseModel, Field, validator
from typing import Literal


class UserPreferences(BaseModel):
    discord_id: str
    rank_group: Literal["iron-plat", "dia-asc", "imm-radiant"] = "imm-radiant"
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=5, le=50)

    @validator("page_size")
    def validate_page_size(cls, v):
        valid_sizes = [5, 10, 25, 50]
        if v not in valid_sizes:
            raise ValueError(f"page_size must be one of {valid_sizes}")
        return v
