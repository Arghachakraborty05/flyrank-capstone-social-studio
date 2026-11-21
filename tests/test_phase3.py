from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.main import app


def _make_client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    SessionTesting = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = SessionTesting()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def test_unapproved_draft_and_rejected_variants_cannot_be_scheduled():
    client = _make_client()
    try:
        post_resp = client.post(
            "/api/posts",
            json={"title": "Async Workers", "markdown_content": "Durable queues prevent lost jobs."},
        )
        assert post_resp.status_code == 201
        post_id = post_resp.json()["id"]

        gen_resp = client.post(
            f"/api/posts/{post_id}/generate",
            json={"platforms": ["telegram", "mock_x"]},
        )
        assert gen_resp.status_code == 201
        variants = gen_resp.json()
        draft_variant = variants[0]
        reject_variant = variants[1]

        run_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()

        draft_sched = client.post(
            f"/api/variants/{draft_variant['id']}/schedule",
            json={"scheduled_at": run_at},
        )
        assert 400 <= draft_sched.status_code < 500
        assert "approved" in draft_sched.json()["detail"].lower()

        rej_resp = client.post(f"/api/variants/{reject_variant['id']}/reject")
        assert rej_resp.status_code == 200
        assert rej_resp.json()["status"] == "rejected"

        rej_sched = client.post(
            f"/api/variants/{reject_variant['id']}/schedule",
            json={"scheduled_at": run_at},
        )
        assert 400 <= rej_sched.status_code < 500
        assert "approved" in rej_sched.json()["detail"].lower()
    finally:
        app.dependency_overrides.clear()


def test_edit_revalidates_and_approved_variant_can_be_scheduled():
    client = _make_client()
    try:
        post_resp = client.post(
            "/api/posts",
            json={"title": "Idempotency Keys", "markdown_content": "Safe retries protect state."},
        )
        post_id = post_resp.json()["id"]

        gen_resp = client.post(
            f"/api/posts/{post_id}/generate",
            json={"platforms": ["telegram", "mock_x"]},
        )
        x_variant = next(v for v in gen_resp.json() if v["platform"] == "mock_x")

        bad_edit = client.put(
            f"/api/variants/{x_variant['id']}",
            json={"content": "Short text #one #two #three #four"},
        )
        assert bad_edit.status_code == 422
        assert "max_hashtags" in bad_edit.json()["detail"]

        good_edit = client.put(
            f"/api/variants/{x_variant['id']}",
            json={"content": "Idempotency keys prevent duplicate sends. #Backend"},
        )
        assert good_edit.status_code == 200
        assert good_edit.json()["status"] == "draft"

        app_resp = client.post(f"/api/variants/{x_variant['id']}/approve")
        assert app_resp.status_code == 200
        assert app_resp.json()["status"] == "approved"

        run_at = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        sched_resp = client.post(
            f"/api/variants/{x_variant['id']}/schedule",
            json={"scheduled_at": run_at},
        )
        assert sched_resp.status_code == 201
        assert sched_resp.json()["status"] == "scheduled"
    finally:
        app.dependency_overrides.clear()