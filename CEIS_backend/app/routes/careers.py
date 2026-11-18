import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.career import CareerRole
from app.schemas.career import CareerRoleCreate, CareerRoleResponse
from app.core.security import get_current_admin

router = APIRouter(prefix="/careers", tags=["Careers & Roles"])

_memory_careers: list[CareerRole] = []


@router.get("", response_model=list[CareerRoleResponse])
async def list_careers(db: AsyncSession = Depends(get_db)):
    try:
        stmt = select(CareerRole).where(CareerRole.is_active.is_(True)).order_by(CareerRole.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())
    except Exception:
        return [c for c in _memory_careers if c.is_active]


@router.post("", response_model=CareerRoleResponse, status_code=status.HTTP_201_CREATED)
async def create_career_role(
    payload: CareerRoleCreate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    role = CareerRole(
        id=uuid.uuid4(),
        title=payload.title,
        department=payload.department,
        location=payload.location,
        employment_type=payload.employment_type,
        experience=payload.experience,
        description=payload.description,
        is_active=payload.is_active,
        created_at=now,
    )
    try:
        db.add(role)
        await db.commit()
        await db.refresh(role)
        return role
    except Exception:
        _memory_careers.insert(0, role)
        return role


@router.delete("/{id}")
async def delete_career_role(
    id: str,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        val_uuid = uuid.UUID(id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid career role ID")

    try:
        res = await db.execute(select(CareerRole).where(CareerRole.id == val_uuid))
        role = res.scalar_one_or_none()
        if role:
            await db.delete(role)
            await db.commit()
            return {"status": "deleted", "id": str(val_uuid)}
    except HTTPException:
        raise
    except Exception:
        pass

    global _memory_careers
    before = len(_memory_careers)
    _memory_careers = [c for c in _memory_careers if str(c.id) != id]
    if len(_memory_careers) < before:
        return {"status": "deleted", "id": id}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Career role not found")
