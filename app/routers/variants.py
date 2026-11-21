from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ScheduleSlot, Variant
from app.schemas import ScheduleSlotRead, ScheduleVariantRequest, VariantRead, VariantUpdateRequest
from app.services.constraints import ConstraintViolationError, validate_variant_content

router = APIRouter(prefix="/api/variants", tags=["variant-review-and-scheduling"])


def _get_variant_or_404(variant_id: int, db: Session) -> Variant:
    variant = db.query(Variant).filter(Variant.id == variant_id).first()
    if not variant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Variant not found.")
    return variant


@router.get("/{variant_id}", response_model=VariantRead)
def get_variant(variant_id: int, db: Session = Depends(get_db)) -> Variant:
    return _get_variant_or_404(variant_id, db)


@router.put("/{variant_id}", response_model=VariantRead)
def edit_variant(
    variant_id: int,
    payload: VariantUpdateRequest,
    db: Session = Depends(get_db),
) -> Variant:
    variant = _get_variant_or_404(variant_id, db)

    if variant.status == "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot edit a variant that has already been published.",
        )

    try:
        validate_variant_content(variant.platform, payload.content)
    except ConstraintViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    variant.content = payload.content
    variant.status = "draft"
    db.commit()
    db.refresh(variant)
    return variant


@router.post("/{variant_id}/approve", response_model=VariantRead)
def approve_variant(variant_id: int, db: Session = Depends(get_db)) -> Variant:
    variant = _get_variant_or_404(variant_id, db)

    if variant.status == "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Variant is already published.",
        )

    try:
        validate_variant_content(variant.platform, variant.content)
    except ConstraintViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot approve invalid variant: {exc}",
        ) from exc

    variant.status = "approved"
    db.commit()
    db.refresh(variant)
    return variant


@router.post("/{variant_id}/reject", response_model=VariantRead)
def reject_variant(variant_id: int, db: Session = Depends(get_db)) -> Variant:
    variant = _get_variant_or_404(variant_id, db)

    if variant.status == "published":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reject a variant that has already been published.",
        )

    variant.status = "rejected"
    db.commit()
    db.refresh(variant)
    return variant


@router.post(
    "/{variant_id}/schedule",
    response_model=ScheduleSlotRead,
    status_code=status.HTTP_201_CREATED,
)
def schedule_variant(
    variant_id: int,
    payload: ScheduleVariantRequest,
    db: Session = Depends(get_db),
) -> ScheduleSlot:
    variant = _get_variant_or_404(variant_id, db)

    if variant.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Cannot schedule variant in '{variant.status}' status. "
                "Variant must be 'approved' before scheduling."
            ),
        )

    try:
        validate_variant_content(variant.platform, variant.content)
    except ConstraintViolationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Cannot schedule variant that fails constraints: {exc}",
        ) from exc

    dt = payload.scheduled_at
    if dt.tzinfo is None:
        normalized_utc = dt.replace(tzinfo=timezone.utc)
    else:
        normalized_utc = dt.astimezone(timezone.utc)

    iso_slot = normalized_utc.isoformat()
    idempotency_key = f"variant-{variant.id}-slot-{iso_slot}"

    existing = (
        db.query(ScheduleSlot)
        .filter(ScheduleSlot.idempotency_key == idempotency_key)
        .first()
    )
    if existing:
        return existing

    slot = ScheduleSlot(
        variant_id=variant.id,
        scheduled_at=normalized_utc,
        idempotency_key=idempotency_key,
        status="scheduled",
    )
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot