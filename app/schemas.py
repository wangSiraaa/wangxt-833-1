from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from app.models import (
    PrescriptionStatus,
    AuditOpinion,
    DrugCategory,
    UserRole
)


class UserBase(BaseModel):
    username: str
    name: str
    role: UserRole


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class DrugBase(BaseModel):
    code: str
    name: str
    category: DrugCategory = DrugCategory.NORMAL
    specification: Optional[str] = None
    manufacturer: Optional[str] = None


class DrugCreate(DrugBase):
    pass


class Drug(DrugBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PrescriptionItemBase(BaseModel):
    drug_code: str
    drug_name: str
    drug_category: DrugCategory = DrugCategory.NORMAL
    specification: Optional[str] = None
    dosage: str
    frequency: str
    quantity: int
    unit: str


class PrescriptionItemCreate(PrescriptionItemBase):
    pass


class PrescriptionItem(PrescriptionItemBase):
    id: int
    prescription_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class PrescriptionBase(BaseModel):
    prescription_no: str
    patient_name: str
    patient_id_card: str
    hospital: str
    doctor_name: str
    diagnosis: str
    issue_date: datetime
    expire_date: datetime


class PrescriptionCreate(PrescriptionBase):
    patient_id: Optional[int] = None
    items: List[PrescriptionItemCreate]


class PrescriptionUpdate(BaseModel):
    pass


class PharmacistReview(BaseModel):
    pharmacist_id: int
    opinion: AuditOpinion
    remark: Optional[str] = None


class RemoteAudit(BaseModel):
    remote_auditor_id: int
    opinion: AuditOpinion
    remark: Optional[str] = None


class Prescription(PrescriptionBase):
    id: int
    patient_id: Optional[int] = None
    status: PrescriptionStatus
    has_key_drug: bool
    pharmacist_opinion: Optional[AuditOpinion] = None
    pharmacist_remark: Optional[str] = None
    pharmacist_id: Optional[int] = None
    pharmacist_review_time: Optional[datetime] = None
    remote_auditor_opinion: Optional[AuditOpinion] = None
    remote_auditor_remark: Optional[str] = None
    remote_auditor_id: Optional[int] = None
    remote_audit_time: Optional[datetime] = None
    pickup_code: Optional[str] = None
    pickup_code_expire: Optional[datetime] = None
    picked_up_time: Optional[datetime] = None
    items: List[PrescriptionItem] = []
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PickupCodeResponse(BaseModel):
    prescription_id: int
    prescription_no: str
    pickup_code: str
    pickup_code_expire: datetime
    patient_name: str


class VerificationRequest(BaseModel):
    pickup_code: str


class AuditLogBase(BaseModel):
    prescription_id: int
    action: str
    remark: Optional[str] = None


class AuditLog(AuditLogBase):
    id: int
    operator_id: Optional[int] = None
    operator_name: Optional[str] = None
    operator_role: Optional[UserRole] = None
    old_status: Optional[PrescriptionStatus] = None
    new_status: Optional[PrescriptionStatus] = None
    old_opinion: Optional[AuditOpinion] = None
    new_opinion: Optional[AuditOpinion] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SupplementNoteCreate(BaseModel):
    missing_reason: str
    supplement_deadline: datetime
    handler_id: int
    remark: Optional[str] = None


class SupplementNote(BaseModel):
    id: int
    prescription_id: int
    missing_reason: str
    supplement_deadline: datetime
    handler_id: Optional[int] = None
    handler_name: Optional[str] = None
    remark: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ApiResponse(BaseModel):
    code: int
    message: str
    data: Optional[dict] = None


class AuditQueryResponse(BaseModel):
    total: int
    items: List[Prescription]
