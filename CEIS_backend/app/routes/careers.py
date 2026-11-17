import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, status
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
        role_id=payload.role_id,
        title=payload.title,
        department=payload.department,
        location=payload.location,
        type=payload.type,
        experience=payload.experience,
        description=payload.description,
        requirements=payload.requirements or [],
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
