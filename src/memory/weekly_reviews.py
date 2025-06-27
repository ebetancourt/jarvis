import os
import json
from typing import Optional, List

from schema.weekly_review_models import WeeklyReviewSession
from core.settings import settings, DatabaseType
from memory.mongodb import get_mongo_saver
from memory.postgres import get_postgres_saver
from memory.sqlite import get_sqlite_saver

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "data")
JSON_PATH = os.path.join(DATA_DIR, "weekly_reviews.json")

# Choose backend based on settings
if getattr(settings, "DATABASE_TYPE", None) == "JSON":
    _backend = "json"
elif settings.DATABASE_TYPE == DatabaseType.MONGO:
    _backend = "mongo"
elif settings.DATABASE_TYPE == DatabaseType.POSTGRES:
    _backend = "postgres"
else:
    _backend = "sqlite"


def _load_json() -> dict:
    if not os.path.exists(JSON_PATH):
        return {}
    with open(JSON_PATH, "r") as f:
        return json.load(f)


def _save_json(data: dict) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(JSON_PATH, "w") as f:
        json.dump(data, f, indent=2, default=str)


async def save_weekly_review(session: WeeklyReviewSession) -> None:
    """Save a WeeklyReviewSession to the database or JSON file."""
    if _backend == "json":
        data = _load_json()
        data[session.session_id] = session.model_dump()
        _save_json(data)
        return
    if _backend == "mongo":
        async with get_mongo_saver() as saver:
            await saver.put(session.session_id, session.model_dump())
    elif _backend == "postgres":
        async with get_postgres_saver() as saver:
            await saver.put(session.session_id, session.model_dump())
    else:
        async with get_sqlite_saver() as saver:
            await saver.put(session.session_id, session.model_dump())


async def get_weekly_review(session_id: str) -> Optional[WeeklyReviewSession]:
    """Retrieve a WeeklyReviewSession by session_id."""
    if _backend == "json":
        data = _load_json()
        if session_id in data:
            return WeeklyReviewSession.model_validate(data[session_id])
        return None
    if _backend == "mongo":
        async with get_mongo_saver() as saver:
            d = await saver.get(session_id)
            if d:
                return WeeklyReviewSession.model_validate(d)
            return None
    elif _backend == "postgres":
        async with get_postgres_saver() as saver:
            d = await saver.get(session_id)
            if d:
                return WeeklyReviewSession.model_validate(d)
            return None
    else:
        async with get_sqlite_saver() as saver:
            d = await saver.get(session_id)
            if d:
                return WeeklyReviewSession.model_validate(d)
            return None


async def list_weekly_reviews(user_id: str) -> List[WeeklyReviewSession]:
    """List all WeeklyReviewSessions for a user, sorted by week_start descending."""
    if _backend == "json":
        data = _load_json()
        sessions = [
            WeeklyReviewSession.model_validate(d)
            for d in data.values()
            if d.get("user_id") == user_id
        ]
        return sorted(sessions, key=lambda s: s.week_start, reverse=True)
    if _backend == "mongo":
        async with get_mongo_saver() as saver:
            all_data = await saver.list()
            sessions = [
                WeeklyReviewSession.model_validate(d)
                for d in all_data
                if d.get("user_id") == user_id
            ]
            return sorted(sessions, key=lambda s: s.week_start, reverse=True)
    elif _backend == "postgres":
        async with get_postgres_saver() as saver:
            all_data = await saver.list()
            sessions = [
                WeeklyReviewSession.model_validate(d)
                for d in all_data
                if d.get("user_id") == user_id
            ]
            return sorted(sessions, key=lambda s: s.week_start, reverse=True)
    else:
        async with get_sqlite_saver() as saver:
            all_data = await saver.list()
            sessions = [
                WeeklyReviewSession.model_validate(d)
                for d in all_data
                if d.get("user_id") == user_id
            ]
            return sorted(sessions, key=lambda s: s.week_start, reverse=True)


async def delete_weekly_review(session_id: str) -> None:
    """Delete a WeeklyReviewSession by session_id."""
    if _backend == "json":
        data = _load_json()
        if session_id in data:
            del data[session_id]
            _save_json(data)
        return
    if _backend == "mongo":
        async with get_mongo_saver() as saver:
            await saver.delete(session_id)
    elif _backend == "postgres":
        async with get_postgres_saver() as saver:
            await saver.delete(session_id)
    else:
        async with get_sqlite_saver() as saver:
            await saver.delete(session_id)
