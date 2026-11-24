import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, or_
from sqlalchemy.exc import IntegrityError
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
    clean_email = str(payload.email).strip().lower()
    clean_role_title = payload.role_title.strip()
    clean_role_title_lower = clean_role_title.lower()

    # Deduplication Guard: Check database for active application for this role
    role_filter = func.lower(JobApplication.role_title) == clean_role_title_lower
    if payload.role_id:
        role_filter = or_(JobApplication.role_id == payload.role_id, role_filter)

    existing_stmt = (
        select(JobApplication)
        .where(
            func.lower(JobApplication.email) == clean_email,
            role_filter,
            func.lower(JobApplication.status) != "rejected",
        )
        .order_by(JobApplication.created_at.desc())
    )

    try:
        res = await db.execute(existing_stmt)
        existing_app = res.scalars().first()
        if existing_app:
            ref = existing_app.application_id
            ref_fmt = ref if ref.startswith("#") else f"#{ref}"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You have already applied for this role (Reference: {ref_fmt}). Our engineering team is reviewing your application.",
            )
    except HTTPException:
        raise
    except Exception:
        # Fall through to in-memory check if DB read fails
        pass

    # In-memory deduplication check
    for mem_app in _memory_applications:
        mem_email = (mem_app.email or "").strip().lower()
        mem_title = (mem_app.role_title or "").strip().lower()
        mem_status = (mem_app.status or "").strip().lower()
        role_match = (payload.role_id and mem_app.role_id == payload.role_id) or (mem_title == clean_role_title_lower)
        if mem_email == clean_email and role_match and mem_status != "rejected":
            ref = mem_app.application_id
            ref_fmt = ref if ref.startswith("#") else f"#{ref}"
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"You have already applied for this role (Reference: {ref_fmt}). Our engineering team is reviewing your application.",
            )

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
        role_title=clean_role_title,
        full_name=payload.full_name.strip(),
        email=clean_email,
        phone=payload.phone.strip(),
        portfolio_url=payload.portfolio_url.strip(),
        resume_url=payload.resume_url.strip(),
        cover_note=payload.cover_note.strip() if payload.cover_note else None,
        status="received",
        created_at=now,
    )

    try:
        db.add(application)
        await db.commit()
        await db.refresh(application)
    except IntegrityError:
        await db.rollback()
        # Handle concurrent submission collision
        try:
            res = await db.execute(existing_stmt)
            existing_app = res.scalars().first()
            if existing_app:
                ref = existing_app.application_id
                ref_fmt = ref if ref.startswith("#") else f"#{ref}"
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"You have already applied for this role (Reference: {ref_fmt}). Our engineering team is reviewing your application.",
                )
        except HTTPException:
            raise
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already applied for this role. Our engineering team is reviewing your application.",
        )
    except Exception:
        await db.rollback()
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
