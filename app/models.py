import enum
from datetime import datetime, timedelta
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.types import Enum as SQLEnum

from app.database import Base


class PrescriptionStatus(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PHARMACIST_REVIEWED = "PHARMACIST_REVIEWED"
    REMOTE_AUDITED = "REMOTE_AUDITED"
    PICKUP_CODE_GENERATED = "PICKUP_CODE_GENERATED"
    PICKED_UP = "PICKED_UP"
    EXPIRED = "EXPIRED"
    REJECTED = "REJECTED"


class AuditOpinion(str, enum.Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    NEED_REVIEW = "NEED_REVIEW"


class DrugCategory(str, enum.Enum):
    NORMAL = "NORMAL"
    KEY = "KEY"


class UserRole(str, enum.Enum):
    PATIENT = "PATIENT"
    PHARMACIST = "PHARMACIST"
    REMOTE_AUDITOR = "REMOTE_AUDITOR"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    name = Column(String(100))
    role = Column(SQLEnum(UserRole))
    created_at = Column(DateTime, default=datetime.utcnow)


class Drug(Base):
    __tablename__ = "drugs"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True)
    name = Column(String(200))
    category = Column(SQLEnum(DrugCategory), default=DrugCategory.NORMAL)
    specification = Column(String(200))
    manufacturer = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)


class Prescription(Base):
    __tablename__ = "prescriptions"

    id = Column(Integer, primary_key=True, index=True)
    prescription_no = Column(String(50), unique=True, index=True)
    patient_id = Column(Integer, ForeignKey("users.id"))
    patient_name = Column(String(100))
    patient_id_card = Column(String(50))
    hospital = Column(String(200))
    doctor_name = Column(String(100))
    diagnosis = Column(String(500))
    issue_date = Column(DateTime)
    expire_date = Column(DateTime)
    status = Column(SQLEnum(PrescriptionStatus), default=PrescriptionStatus.UPLOADED)
    has_key_drug = Column(Boolean, default=False)
    pharmacist_opinion = Column(SQLEnum(AuditOpinion), default=AuditOpinion.PENDING)
    pharmacist_remark = Column(Text)
    pharmacist_id = Column(Integer, ForeignKey("users.id"))
    pharmacist_review_time = Column(DateTime)
    remote_auditor_opinion = Column(SQLEnum(AuditOpinion), default=AuditOpinion.PENDING)
    remote_auditor_remark = Column(Text)
    remote_auditor_id = Column(Integer, ForeignKey("users.id"))
    remote_audit_time = Column(DateTime)
    pickup_code = Column(String(20), unique=True, index=True)
    pickup_code_expire = Column(DateTime)
    picked_up_time = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    patient = relationship("User", foreign_keys=[patient_id], backref="patient_prescriptions")
    pharmacist = relationship("User", foreign_keys=[pharmacist_id], backref="pharmacist_prescriptions")
    remote_auditor = relationship("User", foreign_keys=[remote_auditor_id], backref="auditor_prescriptions")
    items = relationship("PrescriptionItem", back_populates="prescription", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="prescription", cascade="all, delete-orphan")

    def is_expired(self):
        return datetime.utcnow() > self.expire_date


class PrescriptionItem(Base):
    __tablename__ = "prescription_items"

    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"))
    drug_id = Column(Integer, ForeignKey("drugs.id"))
    drug_code = Column(String(50))
    drug_name = Column(String(200))
    drug_category = Column(SQLEnum(DrugCategory), default=DrugCategory.NORMAL)
    specification = Column(String(200))
    dosage = Column(String(200))
    frequency = Column(String(200))
    quantity = Column(Integer)
    unit = Column(String(20))
    created_at = Column(DateTime, default=datetime.utcnow)

    prescription = relationship("Prescription", back_populates="items")
    drug = relationship("Drug")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    prescription_id = Column(Integer, ForeignKey("prescriptions.id"))
    operator_id = Column(Integer, ForeignKey("users.id"))
    operator_name = Column(String(100))
    operator_role = Column(SQLEnum(UserRole))
    action = Column(String(100))
    old_status = Column(SQLEnum(PrescriptionStatus))
    new_status = Column(SQLEnum(PrescriptionStatus))
    old_opinion = Column(SQLEnum(AuditOpinion))
    new_opinion = Column(SQLEnum(AuditOpinion))
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    prescription = relationship("Prescription", back_populates="audit_logs")
    operator = relationship("User", foreign_keys=[operator_id])
