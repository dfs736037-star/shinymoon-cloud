from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


class SnapshotPayload(BaseModel):
    version: int
    pui: dict[str, Any]

    @field_validator("pui")
    @classmethod
    def pui_not_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value:
            raise ValueError("snapshot.pui must not be empty")
        return value


class ConfigCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    description: str = Field(default="", max_length=256)
    author_username: str = Field(min_length=1, max_length=64)
    author_xuid: str = Field(min_length=1, max_length=32)
    script_build: str = Field(default="", max_length=16)
    cfg_version: int = Field(default=1, ge=1)
    snapshot: dict[str, Any]

    @field_validator("name")
    @classmethod
    def name_has_word_char(cls, value: str) -> str:
        if not any(ch.isalnum() for ch in value):
            raise ValueError("name must contain at least one alphanumeric character")
        return value

    @field_validator("snapshot")
    @classmethod
    def validate_snapshot(cls, value: dict[str, Any]) -> dict[str, Any]:
        SnapshotPayload.model_validate(value)
        return value


class ConfigDeleteRequest(BaseModel):
    id: str = Field(min_length=36, max_length=36)


class ConfigListItem(BaseModel):
    id: str
    name: str
    description: str
    author_username: str
    author_xuid: str
    script_build: str
    cfg_version: int
    downloads: int
    created_at: datetime
    updated_at: datetime


class ConfigListResponse(BaseModel):
    items: list[ConfigListItem]
    total: int
    limit: int
    offset: int


class ConfigDetailResponse(ConfigListItem):
    snapshot: dict[str, Any]


class ConfigCreateResponse(BaseModel):
    id: str
    name: str


class MessageResponse(BaseModel):
    ok: bool
    message: str = ""


SortField = Literal["created_at", "downloads"]
