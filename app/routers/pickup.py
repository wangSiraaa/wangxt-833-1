from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import ApiResponse, VerificationRequest
from app import crud

router = APIRouter(prefix="/api/pickup", tags=["取药管理"])


@router.post("/{prescription_id}/generate-code", response_model=ApiResponse)
def generate_pickup_code(prescription_id: int, db: Session = Depends(get_db)):
    try:
        result = crud.generate_pickup_code(db, prescription_id)
        return ApiResponse(
            code=200,
            message="取药码生成成功",
            data=result
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/verify", response_model=ApiResponse)
def verify_pickup_code(verification_in: VerificationRequest, db: Session = Depends(get_db)):
    try:
        prescription = crud.verify_pickup_code(db, verification_in.pickup_code)
        return ApiResponse(
            code=200,
            message="核销成功",
            data={
                "prescription_id": prescription.id,
                "prescription_no": prescription.prescription_no,
                "patient_name": prescription.patient_name,
                "status": prescription.status,
                "picked_up_time": prescription.picked_up_time
            }
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
