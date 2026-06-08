import random
import string
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models import (
    Prescription,
    PrescriptionItem,
    Drug,
    User,
    AuditLog,
    SupplementRecord,
    PrescriptionStatus,
    AuditOpinion,
    DrugCategory,
    UserRole
)
from app.schemas import (
    PrescriptionCreate,
    PharmacistReview,
    RemoteAudit,
    SupplementNoteCreate
)


def generate_prescription_no():
    return "RX" + datetime.now().strftime("%Y%m%d%H%M%S") + ''.join(random.choices(string.digits, k=4))


def _generate_pickup_code_str():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))


def log_audit(
    db: Session,
    prescription_id: int,
    operator_id: Optional[int],
    action: str,
    old_status: Optional[PrescriptionStatus] = None,
    new_status: Optional[PrescriptionStatus] = None,
    old_opinion: Optional[AuditOpinion] = None,
    new_opinion: Optional[AuditOpinion] = None,
    remark: Optional[str] = None
):
    operator = db.query(User).filter(User.id == operator_id).first() if operator_id else None
    log = AuditLog(
        prescription_id=prescription_id,
        operator_id=operator_id,
        operator_name=operator.name if operator else None,
        operator_role=operator.role if operator else None,
        action=action,
        old_status=old_status,
        new_status=new_status,
        old_opinion=old_opinion,
        new_opinion=new_opinion,
        remark=remark
    )
    db.add(log)
    db.commit()


def check_has_key_drug(items: List[PrescriptionItem]) -> bool:
    return any(item.drug_category == DrugCategory.KEY for item in items)


def create_prescription(db: Session, prescription_in: PrescriptionCreate) -> Prescription:
    prescription_no = prescription_in.prescription_no or generate_prescription_no()

    items = []
    for item_in in prescription_in.items:
        drug = db.query(Drug).filter(Drug.code == item_in.drug_code).first()
        item = PrescriptionItem(
            drug_id=drug.id if drug else None,
            drug_code=item_in.drug_code,
            drug_name=item_in.drug_name,
            drug_category=item_in.drug_category,
            specification=item_in.specification,
            dosage=item_in.dosage,
            frequency=item_in.frequency,
            quantity=item_in.quantity,
            unit=item_in.unit
        )
        items.append(item)

    has_key_drug = check_has_key_drug(items)

    prescription = Prescription(
        prescription_no=prescription_no,
        patient_id=prescription_in.patient_id,
        patient_name=prescription_in.patient_name,
        patient_id_card=prescription_in.patient_id_card,
        hospital=prescription_in.hospital,
        doctor_name=prescription_in.doctor_name,
        diagnosis=prescription_in.diagnosis,
        issue_date=prescription_in.issue_date,
        expire_date=prescription_in.expire_date,
        status=PrescriptionStatus.UPLOADED,
        has_key_drug=has_key_drug,
        items=items
    )

    db.add(prescription)
    db.commit()
    db.refresh(prescription)

    log_audit(
        db=db,
        prescription_id=prescription.id,
        operator_id=prescription_in.patient_id,
        action="处方上传",
        new_status=PrescriptionStatus.UPLOADED,
        remark=f"患者提交处方，含{'重点' if has_key_drug else '普通'}药品"
    )

    return prescription


def get_prescription(db: Session, prescription_id: int) -> Optional[Prescription]:
    return db.query(Prescription).filter(Prescription.id == prescription_id).first()


def get_prescription_by_no(db: Session, prescription_no: str) -> Optional[Prescription]:
    return db.query(Prescription).filter(Prescription.prescription_no == prescription_no).first()


def get_prescriptions(
    db: Session,
    patient_id: Optional[int] = None,
    status: Optional[PrescriptionStatus] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Prescription]:
    query = db.query(Prescription)
    if patient_id:
        query = query.filter(Prescription.patient_id == patient_id)
    if status:
        query = query.filter(Prescription.status == status)
    return query.order_by(Prescription.created_at.desc()).offset(skip).limit(limit).all()


def pharmacist_review(
    db: Session,
    prescription_id: int,
    review_in: PharmacistReview,
    _skip_expiry_check: bool = False
) -> Prescription:
    prescription = get_prescription(db, prescription_id)
    if not prescription:
        raise ValueError("处方不存在")

    if prescription.status != PrescriptionStatus.UPLOADED:
        raise ValueError("处方状态不正确，无法进行药店药师复核")

    if not _skip_expiry_check and prescription.is_expired():
        prescription.status = PrescriptionStatus.EXPIRED
        db.commit()
        log_audit(
            db=db,
            prescription_id=prescription_id,
            operator_id=review_in.pharmacist_id,
            action="处方过期",
            old_status=prescription.status,
            new_status=PrescriptionStatus.EXPIRED,
            remark="处方已过期，无法复核"
        )
        raise ValueError("处方已过期，无法取药")

    old_status = prescription.status
    old_opinion = prescription.pharmacist_opinion

    prescription.pharmacist_opinion = review_in.opinion
    prescription.pharmacist_remark = review_in.remark
    prescription.pharmacist_id = review_in.pharmacist_id
    prescription.pharmacist_review_time = datetime.utcnow()

    if review_in.opinion == AuditOpinion.REJECTED:
        prescription.status = PrescriptionStatus.REJECTED
    else:
        prescription.status = PrescriptionStatus.PHARMACIST_REVIEWED

    db.commit()
    db.refresh(prescription)

    log_audit(
        db=db,
        prescription_id=prescription_id,
        operator_id=review_in.pharmacist_id,
        action="药店药师复核",
        old_status=old_status,
        new_status=prescription.status,
        old_opinion=old_opinion,
        new_opinion=review_in.opinion,
        remark=review_in.remark
    )

    return prescription


def remote_audit(
    db: Session,
    prescription_id: int,
    audit_in: RemoteAudit,
    _skip_expiry_check: bool = False
) -> Prescription:
    prescription = get_prescription(db, prescription_id)
    if not prescription:
        raise ValueError("处方不存在")

    if prescription.status not in [PrescriptionStatus.PHARMACIST_REVIEWED, PrescriptionStatus.REMOTE_AUDITED]:
        raise ValueError("处方状态不正确，无法进行远程审方")

    if not _skip_expiry_check and prescription.is_expired():
        prescription.status = PrescriptionStatus.EXPIRED
        db.commit()
        log_audit(
            db=db,
            prescription_id=prescription_id,
            operator_id=audit_in.remote_auditor_id,
            action="处方过期",
            old_status=prescription.status,
            new_status=PrescriptionStatus.EXPIRED,
            remark="处方已过期，无法审方"
        )
        raise ValueError("处方已过期，无法取药")

    old_opinion = prescription.remote_auditor_opinion
    old_status = prescription.status

    if audit_in.opinion == old_opinion:
        raise ValueError("远程审方必须改变审方意见，不能与原意见相同")

    prescription.remote_auditor_opinion = audit_in.opinion
    prescription.remote_auditor_remark = audit_in.remark
    prescription.remote_auditor_id = audit_in.remote_auditor_id
    prescription.remote_audit_time = datetime.utcnow()

    if audit_in.opinion == AuditOpinion.REJECTED:
        prescription.status = PrescriptionStatus.REJECTED
    else:
        prescription.status = PrescriptionStatus.REMOTE_AUDITED

    db.commit()
    db.refresh(prescription)

    log_audit(
        db=db,
        prescription_id=prescription_id,
        operator_id=audit_in.remote_auditor_id,
        action="远程审方",
        old_status=old_status,
        new_status=prescription.status,
        old_opinion=old_opinion,
        new_opinion=audit_in.opinion,
        remark=audit_in.remark
    )

    return prescription


def generate_pickup_code(db: Session, prescription_id: int) -> dict:
    prescription = get_prescription(db, prescription_id)
    if not prescription:
        raise ValueError("处方不存在")

    if prescription.is_expired():
        prescription.status = PrescriptionStatus.EXPIRED
        db.commit()
        log_audit(
            db=db,
            prescription_id=prescription_id,
            operator_id=None,
            action="处方过期",
            old_status=prescription.status,
            new_status=PrescriptionStatus.EXPIRED,
            remark="处方已过期，无法生成取药码"
        )
        raise ValueError("处方已过期，无法取药")

    if prescription.has_key_drug and prescription.remote_auditor_opinion != AuditOpinion.APPROVED:
        raise ValueError("重点药品处方必须经过远程审方通过后才能生成取药码")

    if not prescription.has_key_drug and prescription.pharmacist_opinion != AuditOpinion.APPROVED:
        raise ValueError("处方必须经药店药师复核通过后才能生成取药码")

    if prescription.status in [PrescriptionStatus.PICKED_UP, PrescriptionStatus.REJECTED, PrescriptionStatus.EXPIRED]:
        raise ValueError(f"处方状态为{prescription.status}，无法生成取药码")

    if prescription.pickup_code:
        return {
            "prescription_id": prescription.id,
            "prescription_no": prescription.prescription_no,
            "pickup_code": prescription.pickup_code,
            "pickup_code_expire": prescription.pickup_code_expire,
            "patient_name": prescription.patient_name
        }

    old_status = prescription.status
    pickup_code = _generate_pickup_code_str()
    pickup_code_expire = datetime.utcnow() + timedelta(hours=24)

    prescription.pickup_code = pickup_code
    prescription.pickup_code_expire = pickup_code_expire
    prescription.status = PrescriptionStatus.PICKUP_CODE_GENERATED

    db.commit()
    db.refresh(prescription)

    log_audit(
        db=db,
        prescription_id=prescription_id,
        operator_id=None,
        action="生成取药码",
        old_status=old_status,
        new_status=PrescriptionStatus.PICKUP_CODE_GENERATED,
        remark=f"取药码{pickup_code}，有效期至{pickup_code_expire}"
    )

    return {
        "prescription_id": prescription.id,
        "prescription_no": prescription.prescription_no,
        "pickup_code": pickup_code,
        "pickup_code_expire": pickup_code_expire,
        "patient_name": prescription.patient_name
    }


def verify_pickup_code(db: Session, pickup_code: str) -> Prescription:
    prescription = db.query(Prescription).filter(Prescription.pickup_code == pickup_code).first()
    if not prescription:
        raise ValueError("取药码无效")

    if prescription.is_expired():
        prescription.status = PrescriptionStatus.EXPIRED
        db.commit()
        log_audit(
            db=db,
            prescription_id=prescription.id,
            operator_id=None,
            action="处方过期",
            old_status=prescription.status,
            new_status=PrescriptionStatus.EXPIRED,
            remark="处方已过期，无法核销"
        )
        raise ValueError("处方已过期，无法取药")

    if datetime.utcnow() > prescription.pickup_code_expire:
        raise ValueError("取药码已过期")

    if prescription.status != PrescriptionStatus.PICKUP_CODE_GENERATED:
        raise ValueError(f"处方状态为{prescription.status}，无法核销")

    old_status = prescription.status
    prescription.status = PrescriptionStatus.PICKED_UP
    prescription.picked_up_time = datetime.utcnow()

    db.commit()
    db.refresh(prescription)

    log_audit(
        db=db,
        prescription_id=prescription.id,
        operator_id=None,
        action="取药核销",
        old_status=old_status,
        new_status=PrescriptionStatus.PICKED_UP,
        remark=f"取药码{pickup_code}核销成功"
    )

    return prescription


def get_audit_logs(db: Session, prescription_id: int) -> List[AuditLog]:
    return db.query(AuditLog).filter(
        AuditLog.prescription_id == prescription_id
    ).order_by(AuditLog.created_at.desc()).all()


def get_audit_query(
    db: Session,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    patient_name: Optional[str] = None,
    status: Optional[PrescriptionStatus] = None,
    has_key_drug: Optional[bool] = None,
    skip: int = 0,
    limit: int = 100
) -> dict:
    query = db.query(Prescription)

    if start_date:
        query = query.filter(Prescription.created_at >= start_date)
    if end_date:
        query = query.filter(Prescription.created_at <= end_date)
    if patient_name:
        query = query.filter(Prescription.patient_name.like(f"%{patient_name}%"))
    if status:
        query = query.filter(Prescription.status == status)
    if has_key_drug is not None:
        query = query.filter(Prescription.has_key_drug == has_key_drug)

    total = query.count()
    items = query.order_by(Prescription.created_at.desc()).offset(skip).limit(limit).all()

    return {"total": total, "items": items}


def _serialize_audit_log(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "prescription_id": log.prescription_id,
        "operator_id": log.operator_id,
        "operator_name": log.operator_name,
        "operator_role": log.operator_role.value if log.operator_role else None,
        "action": log.action,
        "old_status": log.old_status.value if log.old_status else None,
        "new_status": log.new_status.value if log.new_status else None,
        "old_opinion": log.old_opinion.value if log.old_opinion else None,
        "new_opinion": log.new_opinion.value if log.new_opinion else None,
        "remark": log.remark,
        "created_at": log.created_at.isoformat() if log.created_at else None
    }


def get_audit_opinion_history(db: Session, prescription_id: int) -> dict:
    prescription = get_prescription(db, prescription_id)
    if not prescription:
        raise ValueError("处方不存在")

    logs = get_audit_logs(db, prescription_id)
    supplement_records = get_supplement_records(db, prescription_id)

    pharmacist_logs = [
        log for log in logs
        if log.operator_role == UserRole.PHARMACIST and log.old_opinion is not None
    ]
    remote_auditor_logs = [
        log for log in logs
        if log.operator_role == UserRole.REMOTE_AUDITOR and log.old_opinion is not None
    ]

    return {
        "prescription_id": prescription.id,
        "prescription_no": prescription.prescription_no,
        "patient_name": prescription.patient_name,
        "has_key_drug": prescription.has_key_drug,
        "status": prescription.status.value if prescription.status else None,
        "pharmacist_opinion": prescription.pharmacist_opinion.value if prescription.pharmacist_opinion else None,
        "pharmacist_remark": prescription.pharmacist_remark,
        "pharmacist_review_time": prescription.pharmacist_review_time.isoformat() if prescription.pharmacist_review_time else None,
        "remote_auditor_opinion": prescription.remote_auditor_opinion.value if prescription.remote_auditor_opinion else None,
        "remote_auditor_remark": prescription.remote_auditor_remark,
        "remote_audit_time": prescription.remote_audit_time.isoformat() if prescription.remote_audit_time else None,
        "pharmacist_history": [_serialize_audit_log(log) for log in pharmacist_logs],
        "remote_auditor_history": [_serialize_audit_log(log) for log in remote_auditor_logs],
        "supplement_records": [_serialize_supplement_record(r) for r in supplement_records]
    }


def create_user(db: Session, username: str, name: str, role: UserRole) -> User:
    user = User(username=username, name=name, role=role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_drug(
    db: Session,
    code: str,
    name: str,
    category: DrugCategory,
    specification: str = None,
    manufacturer: str = None
) -> Drug:
    drug = Drug(
        code=code,
        name=name,
        category=category,
        specification=specification,
        manufacturer=manufacturer
    )
    db.add(drug)
    db.commit()
    db.refresh(drug)
    return drug


def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_drug(db: Session, drug_code: str) -> Optional[Drug]:
    return db.query(Drug).filter(Drug.code == drug_code).first()


def add_supplement_note(
    db: Session,
    prescription_id: int,
    note_in: SupplementNoteCreate
) -> SupplementRecord:
    prescription = get_prescription(db, prescription_id)
    if not prescription:
        raise ValueError("处方不存在")

    if prescription.status == PrescriptionStatus.PICKED_UP:
        raise ValueError("处方已核销，无法补录说明")

    if prescription.status == PrescriptionStatus.EXPIRED or prescription.is_expired():
        if prescription.status != PrescriptionStatus.EXPIRED:
            prescription.status = PrescriptionStatus.EXPIRED
            db.commit()
            log_audit(
                db=db,
                prescription_id=prescription_id,
                operator_id=None,
                action="处方过期",
                old_status=prescription.status,
                new_status=PrescriptionStatus.EXPIRED,
                remark="处方已过期，无法补录说明"
            )
        raise ValueError("处方已过期，无法补录说明")

    if prescription.status != PrescriptionStatus.UPLOADED:
        raise ValueError(f"处方状态为{prescription.status.value}，仅待审方（UPLOADED）状态的处方可补录说明")

    handler = get_user(db, note_in.handler_id)
    if not handler:
        raise ValueError("处理人不存在")

    if handler.role not in [UserRole.PHARMACIST, UserRole.REMOTE_AUDITOR]:
        raise ValueError("处理人必须是药师或远程审方人员")

    record = SupplementRecord(
        prescription_id=prescription_id,
        missing_reason=note_in.missing_reason,
        supplement_deadline=note_in.supplement_deadline,
        handler_id=note_in.handler_id,
        handler_name=handler.name,
        remark=note_in.remark
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    log_audit(
        db=db,
        prescription_id=prescription_id,
        operator_id=note_in.handler_id,
        action="临时补录说明",
        old_status=prescription.status,
        new_status=prescription.status,
        remark=f"缺失原因：{note_in.missing_reason}，补交时间：{note_in.supplement_deadline.strftime('%Y-%m-%d %H:%M:%S')}"
    )

    return record


def get_supplement_records(db: Session, prescription_id: int) -> List[SupplementRecord]:
    return db.query(SupplementRecord).filter(
        SupplementRecord.prescription_id == prescription_id
    ).order_by(SupplementRecord.created_at.desc()).all()


def _serialize_supplement_record(record: SupplementRecord) -> dict:
    return {
        "id": record.id,
        "prescription_id": record.prescription_id,
        "missing_reason": record.missing_reason,
        "supplement_deadline": record.supplement_deadline.isoformat() if record.supplement_deadline else None,
        "handler_id": record.handler_id,
        "handler_name": record.handler_name,
        "remark": record.remark,
        "created_at": record.created_at.isoformat() if record.created_at else None
    }
