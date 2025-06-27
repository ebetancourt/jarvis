from typing import Optional, List

from schema.weekly_review_models import WeeklyReviewSession
from core.settings import settings, DatabaseType
from memory.mongodb import get_mongo_saver
from memory.postgres import get_postgres_saver
from memory.sqlite import get_sqlite_saver

# Choose backend based on settings
if settings.DATABASE_TYPE == DatabaseType.MONGO:
    _get_saver = get_mongo_saver
elif settings.DATABASE_TYPE == DatabaseType.POSTGRES:
    _get_saver = get_postgres_saver
else:
    _get_saver = get_sqlite_saver


async def save_weekly_review(session: WeeklyReviewSession) -> None:
    """Save a WeeklyReviewSession to the database."""
    async with _get_saver() as saver:
        await saver.put(session.session_id, session.model_dump())


async def get_weekly_review(session_id: str) -> Optional[WeeklyReviewSession]:
    """Retrieve a WeeklyReviewSession by session_id."""
    async with _get_saver() as saver:
        data = await saver.get(session_id)
        if data:
            return WeeklyReviewSession.model_validate(data)
        return None


async def list_weekly_reviews(user_id: str) -> List[WeeklyReviewSession]:
    """List all WeeklyReviewSessions for a user, sorted by week_start descending."""
    async with _get_saver() as saver:
        # This assumes the saver supports .list() and filtering; otherwise, this is a stub.
        all_data = await saver.list()
        sessions = [
            WeeklyReviewSession.model_validate(d)
            for d in all_data
            if d.get("user_id") == user_id
        ]
        return sorted(sessions, key=lambda s: s.week_start, reverse=True)


async def delete_weekly_review(session_id: str) -> None:
    """Delete a WeeklyReviewSession by session_id."""
    async with _get_saver() as saver:
        await saver.delete(session_id)
