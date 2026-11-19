import re
from html import unescape
import requests
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Post, Variant
from app.schemas import (
    GenerateVariantsRequest,
    PostIngestRequest,
    PostRead,
    ValidateCandidateRequest,
    VariantRead,
)
from app.services.constraints import ConstraintViolationError, validate_variant_content
from app.services.generator import build_variants_for_post

router = APIRouter(prefix="/api", tags=["posts-and-variants"])


def _fetch_url_text(url: str) -> str:
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unable to fetch source_url: {exc}",
        ) from exc

    without_scripts = re.sub(
        r"<(script|style)[^>]*>.*?</\1>", " ", resp.text, flags=re.DOTALL | re.IGNORECASE
    )
    plain_text = re.sub(r"<[^>]+>", " ", without_scripts)
    cleaned = re.sub(r"\s+", " ", unescape(plain_text)).strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fetched URL returned no readable text.",
        )
    return cleaned


@router.post("/posts", response_model=PostRead, status_code=status.HTTP_201_CREATED)
def ingest_post(payload: PostIngestRequest, db: Session = Depends(get_db)) -> Post:
    if payload.markdown_content and payload.markdown_content.strip():
        source_type = "markdown"
        source_url = payload.source_url.strip() if payload.source_url else None
        content = payload.markdown_content.strip()
    else:
        assert payload.source_url is not None
        source_type = "url"
        source_url = payload.source_url.strip()
        content = _fetch_url_text(source_url)

    post = Post(
        source_type=source_type,
        source_url=source_url,
        title=payload.title.strip() if payload.title and payload.title.strip() else None,
        content=content,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return post


@router.get("/posts", response_model=list[PostRead])
def list_posts(db: Session = Depends(get_db)) -> list[Post]:
    return db.query(Post).order_by(Post.id.desc()).all()


@router.get("/posts/{post_id}", response_model=PostRead)
def get_post(post_id: int, db: Session = Depends(get_db)) -> Post:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    return post


@router.post(
    "/posts/{post_id}/generate",
    response_model=list[VariantRead],
    status_code=status.HTTP_201_CREATED,
)
def generate_variants(
    post_id: int,
    payload: GenerateVariantsRequest,
    db: Session = Depends(get_db),
) -> list[Variant]:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")

    try:
        generated = build_variants_for_post(
            title=post.title,
            stored_content=post.content,
            platforms=payload.platforms,
        )
    except (ConstraintViolationError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    created: list[Variant] = []
    for platform, text in generated.items():
        variant = Variant(
            post_id=post.id,
            platform=platform,
            content=text,
            status="draft",
        )
        db.add(variant)
        created.append(variant)

    db.commit()
    for v in created:
        db.refresh(v)
    return created


@router.get("/posts/{post_id}/variants", response_model=list[VariantRead])
def list_variants(post_id: int, db: Session = Depends(get_db)) -> list[Variant]:
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found.")
    return db.query(Variant).filter(Variant.post_id == post_id).all()


@router.post("/variants/validate-candidate")
def validate_candidate(payload: ValidateCandidateRequest) -> dict:
    try:
        validate_variant_content(payload.platform, payload.content)
    except ConstraintViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return {"valid": True, "platform": payload.platform}