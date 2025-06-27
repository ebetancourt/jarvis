import pytest
from schema.weekly_review_models import WeeklyReviewSession, WeeklyReviewEntry
from memory import weekly_reviews
from datetime import datetime


@pytest.mark.asyncio
async def test_save_and_get_weekly_review(temp_weekly_reviews_json, monkeypatch):
    monkeypatch.setattr(weekly_reviews, "JSON_PATH", temp_weekly_reviews_json)
    session = WeeklyReviewSession(
        user_id="user1",
        session_id="sess1",
        start_time=datetime.utcnow(),
        end_time=None,
        week_start=datetime(2024, 6, 1),
        week_end=datetime(2024, 6, 7),
        entries=[WeeklyReviewEntry(type="accomplishment", content="Did X")],
        summary="A good week",
        rules_version="v1",
        created_at=datetime.utcnow(),
        updated_at=None,
        metadata=None,
    )
    await weekly_reviews.save_weekly_review(session)
    loaded = await weekly_reviews.get_weekly_review("sess1")
    assert loaded is not None
    assert loaded.user_id == "user1"
    assert loaded.entries[0].content == "Did X"


@pytest.mark.asyncio
async def test_list_and_delete_weekly_reviews(temp_weekly_reviews_json, monkeypatch):
    monkeypatch.setattr(weekly_reviews, "JSON_PATH", temp_weekly_reviews_json)
    # Add two sessions
    for i in range(2):
        session = WeeklyReviewSession(
            user_id="user2",
            session_id=f"sess{i}",
            start_time=datetime.utcnow(),
            end_time=None,
            week_start=datetime(2024, 6, 1 + i * 7),
            week_end=datetime(2024, 6, 7 + i * 7),
            entries=[WeeklyReviewEntry(type="accomplishment", content=f"Did {i}")],
            summary=f"Week {i}",
            rules_version="v1",
            created_at=datetime.utcnow(),
            updated_at=None,
            metadata=None,
        )
        await weekly_reviews.save_weekly_review(session)
    sessions = await weekly_reviews.list_weekly_reviews("user2")
    assert len(sessions) == 2
    await weekly_reviews.delete_weekly_review("sess0")
    sessions = await weekly_reviews.list_weekly_reviews("user2")
    assert len(sessions) == 1
    assert sessions[0].session_id == "sess1"


@pytest.mark.asyncio
async def test_get_previous_weekly_review(temp_weekly_reviews_json, monkeypatch):
    monkeypatch.setattr(weekly_reviews, "JSON_PATH", temp_weekly_reviews_json)
    # Add two sessions, one before and one after
    session1 = WeeklyReviewSession(
        user_id="user3",
        session_id="sessA",
        start_time=datetime.utcnow(),
        end_time=None,
        week_start=datetime(2024, 5, 20),
        week_end=datetime(2024, 5, 26),
        entries=[WeeklyReviewEntry(type="accomplishment", content="A")],
        summary="First",
        rules_version="v1",
        created_at=datetime.utcnow(),
        updated_at=None,
        metadata=None,
    )
    session2 = WeeklyReviewSession(
        user_id="user3",
        session_id="sessB",
        start_time=datetime.utcnow(),
        end_time=None,
        week_start=datetime(2024, 5, 27),
        week_end=datetime(2024, 6, 2),
        entries=[WeeklyReviewEntry(type="accomplishment", content="B")],
        summary="Second",
        rules_version="v1",
        created_at=datetime.utcnow(),
        updated_at=None,
        metadata=None,
    )
    await weekly_reviews.save_weekly_review(session1)
    await weekly_reviews.save_weekly_review(session2)
    prev = await weekly_reviews.get_previous_weekly_review(
        "user3", datetime(2024, 5, 28)
    )
    assert prev is not None
    assert prev.session_id == "sessA"


@pytest.mark.asyncio
async def test_compare_weekly_reviews():
    entry1 = WeeklyReviewEntry(type="accomplishment", content="Did X")
    entry2 = WeeklyReviewEntry(type="accomplishment", content="Did Y")
    session1 = WeeklyReviewSession(
        user_id="user4",
        session_id="s1",
        start_time=datetime.utcnow(),
        end_time=None,
        week_start=datetime(2024, 6, 1),
        week_end=datetime(2024, 6, 7),
        entries=[entry1],
        summary="Summary 1",
        rules_version="v1",
        created_at=datetime.utcnow(),
        updated_at=None,
        metadata={"foo": 1},
    )
    session2 = WeeklyReviewSession(
        user_id="user4",
        session_id="s2",
        start_time=datetime.utcnow(),
        end_time=None,
        week_start=datetime(2024, 6, 8),
        week_end=datetime(2024, 6, 14),
        entries=[entry1, entry2],
        summary="Summary 2",
        rules_version="v1",
        created_at=datetime.utcnow(),
        updated_at=None,
        metadata={"foo": 2},
    )
    diffs = weekly_reviews.compare_weekly_reviews(session1, session2)
    assert "summary" in diffs
    assert "added_entries" in diffs
    assert "metadata" in diffs


@pytest.mark.asyncio
async def test_migrate_weekly_reviews_json_to_db(temp_weekly_reviews_json, monkeypatch):
    monkeypatch.setattr(weekly_reviews, "JSON_PATH", temp_weekly_reviews_json)
    # Save a session in JSON
    session = WeeklyReviewSession(
        user_id="user5",
        session_id="sessM",
        start_time=datetime.utcnow(),
        end_time=None,
        week_start=datetime(2024, 6, 1),
        week_end=datetime(2024, 6, 7),
        entries=[WeeklyReviewEntry(type="accomplishment", content="Did M")],
        summary="Migration test",
        rules_version="v1",
        created_at=datetime.utcnow(),
        updated_at=None,
        metadata=None,
    )
    await weekly_reviews.save_weekly_review(session)
    # Now migrate (should be a no-op since backend is JSON)
    migrated = await weekly_reviews.migrate_weekly_reviews_json_to_db(
        temp_weekly_reviews_json
    )
    assert migrated == 0
