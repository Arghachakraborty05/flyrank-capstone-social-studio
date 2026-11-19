from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app


def test_phase2_ingestion_generation_and_validation(tmp_path):
    db_file = tmp_path / "test_phase2.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False},
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    try:
        # 1. Ingest post
        ingest_resp = client.post(
            "/api/posts",
            json={
                "title": "Why Idempotency Matters",
                "markdown_content": "Retries after timeouts should never duplicate side effects.",
            },
        )
        assert ingest_resp.status_code == 201
        post_data = ingest_resp.json()
        post_id = post_data["id"]

        # 2. Generate two distinct variants
        gen_resp = client.post(
            f"/api/posts/{post_id}/generate",
            json={"platforms": ["telegram", "mock_x"]},
        )
        assert gen_resp.status_code == 201
        variants = gen_resp.json()
        assert len(variants) == 2
        by_platform = {v["platform"]: v["content"] for v in variants}
        assert by_platform["telegram"] != by_platform["mock_x"]
        assert len(by_platform["mock_x"]) <= 280

        # 3. Block invalid hashtag count with named rule
        bad_tags_resp = client.post(
            "/api/variants/validate-candidate",
            json={
                "platform": "mock_x",
                "content": "Too many tags #a #b #c #d",
            },
        )
        assert bad_tags_resp.status_code == 422
        assert "max_hashtags" in bad_tags_resp.json()["detail"]

        # 4. Block content exceeding max_length on mock_x with named rule
        oversized_content = "x" * 281
        bad_length_resp = client.post(
            "/api/variants/validate-candidate",
            json={
                "platform": "mock_x",
                "content": oversized_content,
            },
        )
        assert bad_length_resp.status_code == 422
        assert "max_length" in bad_length_resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()