from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PrescriptionStatus, AuditOpinion
from app.schemas import (
    Prescription,
    PrescriptionCreate,
    PharmacistReview,
    RemoteAudit,
    ApiResponse
)
from app import crud

router = APIRouter(prefix="/api/prescriptions", tags=["处方管理"])


@router.post("", response_model=ApiResponse)
def upload_prescription(prescription_in: PrescriptionCreate, db: Session = Depends(get_db)):
    try:
        prescription = crud.create_prescription(db, prescription_in)
        return ApiResponse(
            code=200,
            message="处方上传成功",
            data={"prescription_id": prescription.id, "prescription_no": prescription.prescription_no}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=ApiResponse)
def list_prescriptions(
    patient_id: Optional[int] = None,
    status: Optional[PrescriptionStatus] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    prescriptions = crud.get_prescriptions(db, patient_id=patient_id, status=status, skip=skip, limit=limit)
    return ApiResponse(
        code=200,
        message="查询成功",
        data={"total": len(prescriptions), "items": [p.__dict__ for p in prescriptions]}
    )


@router.get("/{prescription_id}", response_model=ApiResponse)
def get_prescription(prescription_id: int, db: Session = Depends(get_db)):
    prescription = crud.get_prescription(db, prescription_id)
    if not prescription:
        raise HTTPException(status_code=404, detail="处方不存在")
    return ApiResponse(
        code=200,
        message="查询成功",
        data={"prescription": prescription.__dict__}
    )


@router.post("/{prescription_id}/pharmacist-review", response_model=ApiResponse)
def pharmacist_review(prescription_id: int, review_in: PharmacistReview, db: Session = Depends(get_db)):
    try:
        prescription = crud.pharmacist_review(db, prescription_id, review_in)
        return ApiResponse(
            code=200,
            message="药店药师复核完成",
            data={
                "prescription_id": prescription.id,
                "status": prescription.status,
                "opinion": prescription.pharmacist_opinion
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{prescription_id}/remote-audit", response_model=ApiResponse)
def remote_audit(prescription_id: int, audit_in: RemoteAudit, db: Session = Depends(get_db)):
    try:
        prescription = crud.remote_audit(db, prescription_id, audit_in)
        return ApiResponse(
            code=200,
            message="远程审方完成",
            data={
                "prescription_id": prescription.id,
                "status": prescription.status,
                "opinion": prescription.remote_auditor_opinion,
                "opinion_changed": True
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
