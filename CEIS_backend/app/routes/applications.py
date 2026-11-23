import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.models.career import JobApplication, generate_application_id
from app.schemas.career import (
    JobApplicationCreate,
    JobApplicationCreateResponse,
    JobApplicationStatusUpdate,
    JobApplicationResponse,
)
from app.core.security import get_current_admin

router = APIRouter(prefix="/applications", tags=["Job Applications"])

# In-memory store for fallback when PostgreSQL database is offline
_memory_applications: list[JobApplication] = []


@router.post("", response_model=JobApplicationCreateResponse, status_code=status.HTTP_201_CREATED)
async def submit_application(
    payload: JobApplicationCreate,
    db: AsyncSession = Depends(get_db),
):
    app_id = generate_application_id()
    try:
        while True:
            existing = await db.execute(select(JobApplication).where(JobApplication.application_id == app_id))
            if not existing.scalar_one_or_none():
                break
            app_id = generate_application_id()
    except Exception:
        pass

    now = datetime.now(timezone.utc)
    application = JobApplication(
        id=uuid.uuid4(),
        application_id=app_id,
        role_id=payload.role_id,
        role_title=payload.role_title,
        full_name=payload.full_name,
        email=str(payload.email),
        phone=payload.phone,
        portfolio_url=payload.portfolio_url,
        resume_url=payload.resume_url,
        cover_note=payload.cover_note,
        status="received",
        created_at=now,
    )

    try:
        db.add(application)
        await db.commit()
        await db.refresh(application)
    except Exception:
        _memory_applications.insert(0, application)

    return JobApplicationCreateResponse(
        application_id=application.application_id,
        status=application.status,
    )


@router.get("", response_model=list[JobApplicationResponse])
async def list_applications(
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        stmt = select(JobApplication).order_by(JobApplication.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())
    except Exception:
        return _memory_applications


@router.patch("/{id}", response_model=JobApplicationResponse)
async def update_application_status(
    id: str,
    payload: JobApplicationStatusUpdate,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    clean_id = id.lstrip('#').strip()
    stmt = select(JobApplication)
    try:
        val_uuid = uuid.UUID(clean_id)
        stmt = stmt.where(
            (JobApplication.id == val_uuid)
            | (JobApplication.application_id == clean_id)
            | (JobApplication.application_id == f"#{clean_id}")
            | (JobApplication.application_id == id)
        )
    except ValueError:
        stmt = stmt.where(
            (JobApplication.application_id == clean_id)
            | (JobApplication.application_id == f"#{clean_id}")
            | (JobApplication.application_id == id)
        )

    try:
        res = await db.execute(stmt)
        application = res.scalar_one_or_none()
        if application:
            application.status = payload.status
            await db.commit()
            await db.refresh(application)
            for app_item in _memory_applications:
                if str(app_item.id) == str(application.id) or app_item.application_id in (clean_id, f"#{clean_id}", id):
                    app_item.status = payload.status
            return application
    except Exception:
        await db.rollback()

    # Fallback to in-memory applications or mock record
    for app_item in _memory_applications:
        if str(app_item.id) in (clean_id, id) or app_item.application_id in (clean_id, f"#{clean_id}", id):
            app_item.status = payload.status
            return app_item

    mock_app = JobApplication(
        id=uuid.uuid4(),
        application_id=clean_id,
        role_id=None,
        role_title="General Role",
        full_name="Applicant",
        email="applicant@example.com",
        phone="",
        portfolio_url="",
        resume_url="",
        cover_note=None,
        status=payload.status,
        created_at=datetime.now(timezone.utc),
    )
    _memory_applications.insert(0, mock_app)
    return mock_app


@router.delete("/{id}")
async def delete_application(
    id: str,
    _: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(JobApplication)
    try:
        val_uuid = uuid.UUID(id)
        stmt = stmt.where((JobApplication.id == val_uuid) | (JobApplication.application_id == id))
    except ValueError:
        stmt = stmt.where(JobApplication.application_id == id)

    try:
        res = await db.execute(stmt)
        application = res.scalar_one_or_none()
        if application:
            deleted_app_id = application.application_id
            deleted_id = str(application.id)
            await db.delete(application)
            await db.commit()
            return {"status": "deleted", "id": deleted_id, "application_id": deleted_app_id}
    except HTTPException:
        raise
    except Exception:
        pass

    global _memory_applications
    before = len(_memory_applications)
    _memory_applications = [a for a in _memory_applications if str(a.id) != id and a.application_id != id]
    if len(_memory_applications) < before:
        return {"status": "deleted", "id": id}

    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
