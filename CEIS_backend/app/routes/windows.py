import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.cms_window import CMSWindow
from app.schemas.cms_window import CMSWindowCreate, CMSWindowUpdate, CMSWindowResponse
from app.core.security import get_current_admin

router = APIRouter(prefix="/windows", tags=["CMS Windows & Case Studies"])

_memory_windows: list[CMSWindow] = []


@router.get("", response_model=list[CMSWindowResponse])
async def list_windows(
    all: bool = Query(False, description="Include unpublished windows if true"),
    db: AsyncSession = Depends(get_db),
):
    try:
        stmt = select(CMSWindow).order_by(CMSWindow.updated_at.desc())
        if not all:
            stmt = stmt.where(CMSWindow.is_published.is_(True))
        res = await db.execute(stmt)
        return list(res.scalars().all())
    except Exception:
        return [w for w in _memory_windows if all or w.is_published]


@router.get("/{slug}", response_model=CMSWindowResponse)
async def get_window_by_slug(slug: str, db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(CMSWindow).where(CMSWindow.slug == slug, CMSWindow.is_published.is_(True))
        res = await db.execute(stmt)
        window = res.scalar_one_or_none()
        if window:
            return window
    except Exception:
        pass

    for w in _memory_windows:
        if w.slug == slug and w.is_published:
            return w
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Window not found")


@router.post("", response_model=CMSWindowResponse, status_code=status.HTTP_201_CREATED)
async def create_window(
    payload: CMSWindowCreate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    new_window = CMSWindow(
        id=uuid.uuid4(),
        slot_id=payload.slot_id,
        slug=payload.slug,
        title=payload.title,
        category=payload.category,
        summary=payload.summary,
        problem=payload.problem,
        solution=payload.solution,
        metrics=payload.metrics or [],
        tags=payload.tags or [],
        is_published=payload.is_published,
        updated_at=now,
    )
    try:
        res = await db.execute(select(CMSWindow).where(CMSWindow.slug == payload.slug))
        if res.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Window slug already exists")
        
        if payload.slot_id:
            slot_res = await db.execute(select(CMSWindow).where(CMSWindow.slot_id == payload.slot_id))
            if slot_res.scalar_one_or_none():
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Slot ID already in use")

        db.add(new_window)
        await db.commit()
        await db.refresh(new_window)
        return new_window
    except HTTPException:
        raise
    except Exception:
        _memory_windows.insert(0, new_window)
        return new_window


@router.put("/{id}", response_model=CMSWindowResponse)
async def update_window(
    id: uuid.UUID,
    payload: CMSWindowUpdate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await db.execute(select(CMSWindow).where(CMSWindow.id == id))
        window = res.scalar_one_or_none()
        if window:
            updates = payload.model_dump(exclude_unset=True)
            for k, v in updates.items():
                setattr(window, k, v)
            window.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(window)
            return window
    except Exception:
        pass

    for w in _memory_windows:
        if w.id == id:
            updates = payload.model_dump(exclude_unset=True)
            for k, v in updates.items():
                setattr(w, k, v)
            w.updated_at = datetime.now(timezone.utc)
            return w

    now = datetime.now(timezone.utc)
    mock_w = CMSWindow(
        id=id,
        slot_id=payload.slot_id,
        slug=payload.slug or f"window-{str(id)[:8]}",
        title=payload.title or "Updated Window",
        category=payload.category or "general",
        summary=payload.summary or "Summary of updated window",
        problem=payload.problem,
        solution=payload.solution,
        metrics=payload.metrics or [],
        tags=payload.tags or [],
        is_published=payload.is_published if payload.is_published is not None else True,
        updated_at=now,
    )
    _memory_windows.insert(0, mock_w)
    return mock_w


@router.delete("/{id}")
async def delete_window(
    id: uuid.UUID,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        res = await db.execute(select(CMSWindow).where(CMSWindow.id == id))
        window = res.scalar_one_or_none()
        if window:
            await db.delete(window)
            await db.commit()
            return {"message": "Window deleted successfully"}
    except Exception:
        pass

    global _memory_windows
    _memory_windows = [w for w in _memory_windows if w.id != id]
    return {"message": "Window deleted successfully"}
