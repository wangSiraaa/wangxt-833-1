from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PrescriptionStatus
from app.schemas import ApiResponse
from app import crud

router = APIRouter(prefix="/api/audit", tags=["稽核查询"])


def _to_dict(obj):
    return {k: v for k, v in obj.__dict__.items() if not k.startswith('_')}


@router.get("/prescriptions", response_model=ApiResponse)
def audit_query(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    patient_name: Optional[str] = None,
    status: Optional[PrescriptionStatus] = None,
    has_key_drug: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    result = crud.get_audit_query(
        db,
        start_date=start_date,
        end_date=end_date,
        patient_name=patient_name,
        status=status,
        has_key_drug=has_key_drug,
        skip=skip,
        limit=limit
    )
    return ApiResponse(
        code=200,
        message="查询成功",
        data={
            "total": result["total"],
            "items": [_to_dict(p) for p in result["items"]]
        }
    )


@router.get("/prescriptions/{prescription_id}/logs", response_model=ApiResponse)
def get_audit_logs(prescription_id: int, db: Session = Depends(get_db)):
    logs = crud.get_audit_logs(db, prescription_id)
    return ApiResponse(
        code=200,
        message="查询成功",
        data={"total": len(logs), "items": [_to_dict(log) for log in logs]}
    )


@router.get("/prescriptions/{prescription_id}/opinion-history", response_model=ApiResponse)
def get_opinion_history(prescription_id: int, db: Session = Depends(get_db)):
    try:
        result = crud.get_audit_opinion_history(db, prescription_id)
        return ApiResponse(
            code=200,
            message="查询成功",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
