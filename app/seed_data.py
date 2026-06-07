from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models import UserRole, DrugCategory, PrescriptionStatus, AuditOpinion
from app import crud
from app.schemas import (
    PrescriptionCreate,
    PrescriptionItemCreate,
    PharmacistReview,
    RemoteAudit
)


def init_seed_data(db: Session):
    print("开始初始化种子数据...")

    if db.query(crud.User).count() == 0:
        print("  - 创建用户数据...")
        patient1 = crud.create_user(db, "patient001", "张三", UserRole.PATIENT)
        patient2 = crud.create_user(db, "patient002", "李四", UserRole.PATIENT)
        patient3 = crud.create_user(db, "patient003", "王五", UserRole.PATIENT)
        pharmacist = crud.create_user(db, "pharmacist001", "李药师", UserRole.PHARMACIST)
        remote_auditor = crud.create_user(db, "auditor001", "王审方师", UserRole.REMOTE_AUDITOR)
        print(f"    - 患者: {patient1.name}, {patient2.name}, {patient3.name}")
        print(f"    - 药店药师: {pharmacist.name}")
        print(f"    - 远程审方师: {remote_auditor.name}")
    else:
        patient1 = crud.get_user(db, 1)
        patient2 = crud.get_user(db, 2)
        patient3 = crud.get_user(db, 3)
        pharmacist = crud.get_user(db, 4)
        remote_auditor = crud.get_user(db, 5)

    if db.query(crud.Drug).count() == 0:
        print("  - 创建药品数据...")
        drug1 = crud.create_drug(db, "DRUG001", "阿莫西林胶囊", DrugCategory.NORMAL, "0.5g*24粒", "华北制药")
        drug2 = crud.create_drug(db, "DRUG002", "布洛芬缓释胶囊", DrugCategory.NORMAL, "0.3g*20粒", "中美史克")
        drug3 = crud.create_drug(db, "DRUG003", "氨酚待因片", DrugCategory.KEY, "每片含对乙酰氨基酚500mg+磷酸可待因8.4mg", "国药集团")
        drug4 = crud.create_drug(db, "DRUG004", "盐酸曲马多缓释片", DrugCategory.KEY, "100mg*10片", "萌蒂制药")
        drug5 = crud.create_drug(db, "DRUG005", "头孢克肟分散片", DrugCategory.NORMAL, "0.1g*6片", "白云山制药")
        print(f"    - 普通药品: {drug1.name}, {drug2.name}, {drug5.name}")
        print(f"    - 重点药品(麻醉/精神类): {drug3.name}, {drug4.name}")

    if db.query(crud.Prescription).count() == 0:
        print("  - 创建处方数据（覆盖正常和失败场景）...")

        now = datetime.utcnow()

        rx1 = crud.create_prescription(db, PrescriptionCreate(
            prescription_no="RX202606010001",
            patient_id=patient1.id,
            patient_name=patient1.name,
            patient_id_card="110101199001011234",
            hospital="北京协和医院",
            doctor_name="张医生",
            diagnosis="上呼吸道感染",
            issue_date=now - timedelta(days=2),
            expire_date=now + timedelta(days=5),
            items=[
                PrescriptionItemCreate(
                    drug_code="DRUG001", drug_name="阿莫西林胶囊", drug_category=DrugCategory.NORMAL,
                    specification="0.5g*24粒", dosage="每次1粒", frequency="每日3次", quantity=2, unit="盒"
                )
            ]
        ))

        rx2 = crud.create_prescription(db, PrescriptionCreate(
            prescription_no="RX202606010002",
            patient_id=patient1.id,
            patient_name=patient1.name,
            patient_id_card="110101199001011234",
            hospital="北京协和医院",
            doctor_name="张医生",
            diagnosis="术后镇痛",
            issue_date=now - timedelta(days=1),
            expire_date=now + timedelta(days=6),
            items=[
                PrescriptionItemCreate(
                    drug_code="DRUG003", drug_name="氨酚待因片", drug_category=DrugCategory.KEY,
                    specification="每片含对乙酰氨基酚500mg+磷酸可待因8.4mg",
                    dosage="每次1片", frequency="每日3次", quantity=1, unit="盒"
                )
            ]
        ))

        rx3 = crud.create_prescription(db, PrescriptionCreate(
            prescription_no="RX202606010003",
            patient_id=patient2.id,
            patient_name=patient2.name,
            patient_id_card="110101199102022345",
            hospital="北京大学第一医院",
            doctor_name="王医生",
            diagnosis="中度疼痛",
            issue_date=now - timedelta(days=3),
            expire_date=now + timedelta(days=4),
            items=[
                PrescriptionItemCreate(
                    drug_code="DRUG004", drug_name="盐酸曲马多缓释片", drug_category=DrugCategory.KEY,
                    specification="100mg*10片", dosage="每次1片", frequency="每日2次", quantity=2, unit="盒"
                ),
                PrescriptionItemCreate(
                    drug_code="DRUG002", drug_name="布洛芬缓释胶囊", drug_category=DrugCategory.NORMAL,
                    specification="0.3g*20粒", dosage="每次1粒", frequency="每日2次", quantity=1, unit="盒"
                )
            ]
        ))

        rx4 = crud.create_prescription(db, PrescriptionCreate(
            prescription_no="RX202606010004",
            patient_id=patient2.id,
            patient_name=patient2.name,
            patient_id_card="110101199102022345",
            hospital="北京大学第一医院",
            doctor_name="王医生",
            diagnosis="发热",
            issue_date=now - timedelta(days=10),
            expire_date=now - timedelta(days=3),
            items=[
                PrescriptionItemCreate(
                    drug_code="DRUG002", drug_name="布洛芬缓释胶囊", drug_category=DrugCategory.NORMAL,
                    specification="0.3g*20粒", dosage="每次1粒", frequency="每日2次", quantity=1, unit="盒"
                )
            ]
        ))

        rx5 = crud.create_prescription(db, PrescriptionCreate(
            prescription_no="RX202606010005",
            patient_id=patient3.id,
            patient_name=patient3.name,
            patient_id_card="110101199203033456",
            hospital="中国人民解放军总医院",
            doctor_name="李医生",
            diagnosis="急性支气管炎",
            issue_date=now - timedelta(days=1),
            expire_date=now + timedelta(days=6),
            items=[
                PrescriptionItemCreate(
                    drug_code="DRUG005", drug_name="头孢克肟分散片", drug_category=DrugCategory.NORMAL,
                    specification="0.1g*6片", dosage="每次1片", frequency="每日2次", quantity=2, unit="盒"
                )
            ]
        ))

        print(f"    - 处方1: 普通药品处方（{rx1.prescription_no}）- 待药店药师复核")
        print(f"    - 处方2: 重点药品处方（{rx2.prescription_no}）- 待药店药师复核")
        print(f"    - 处方3: 重点+普通药品混合处方（{rx3.prescription_no}）- 待药店药师复核")
        print(f"    - 处方4: 已过期处方（{rx4.prescription_no}）- 过期场景")
        print(f"    - 处方5: 普通药品处方（{rx5.prescription_no}）- 将模拟完整流程")

        print("  - 推进处方状态流转...")

        crud.pharmacist_review(db, rx1.id, PharmacistReview(
            pharmacist_id=pharmacist.id,
            opinion=AuditOpinion.APPROVED,
            remark="药品清单核对无误，用法用量正确"
        ))
        print(f"    - 处方1: 药店药师已复核通过 → 可生成取药码")

        crud.pharmacist_review(db, rx2.id, PharmacistReview(
            pharmacist_id=pharmacist.id,
            opinion=AuditOpinion.APPROVED,
            remark="重点药品处方，需远程审方"
        ))
        print(f"    - 处方2: 药店药师已复核通过 → 等待远程审方")

        crud.pharmacist_review(db, rx3.id, PharmacistReview(
            pharmacist_id=pharmacist.id,
            opinion=AuditOpinion.NEED_REVIEW,
            remark="含重点管制药品，建议远程审方重点审核"
        ))
        print(f"    - 处方3: 药店药师已提请复审 → 等待远程审方")

        crud.pharmacist_review(db, rx5.id, PharmacistReview(
            pharmacist_id=pharmacist.id,
            opinion=AuditOpinion.APPROVED,
            remark="处方信息完整，药品适宜"
        ))
        crud.generate_pickup_code(db, rx5.id)
        print(f"    - 处方5: 药店药师复核通过 → 取药码已生成 → 已完成全流程")

        crud.remote_audit(db, rx3.id, RemoteAudit(
            remote_auditor_id=remote_auditor.id,
            opinion=AuditOpinion.APPROVED,
            remark="远程审方通过：重点药品适应症相符，用法用量适宜"
        ))
        print(f"    - 处方3: 远程审方师改意见（PENDING→APPROVED）→ 可生成取药码")

        crud.remote_audit(db, rx3.id, RemoteAudit(
            remote_auditor_id=remote_auditor.id,
            opinion=AuditOpinion.NEED_REVIEW,
            remark="需补充完善处方信息"
        ))
        print(f"    - 处方3: 远程审方师改意见（APPROVED→NEED_REVIEW）→ 演示意见必须改变")

        crud.remote_audit(db, rx3.id, RemoteAudit(
            remote_auditor_id=remote_auditor.id,
            opinion=AuditOpinion.APPROVED,
            remark="信息补充完整，远程审方通过"
        ))
        print(f"    - 处方3: 远程审方师改意见（NEED_REVIEW→APPROVED）→ 可生成取药码")

        print("\n种子数据初始化完成！")
        print("=" * 60)
        print("场景覆盖说明：")
        print("  ✅ 正常场景1: 普通药品处方（仅需药店药师复核）")
        print("  ✅ 正常场景2: 重点药品处方（药店+远程双重审方）")
        print("  ✅ 正常场景3: 远程审方多次改意见")
        print("  ✅ 失败场景1: 处方过期，无法取药")
        print("  ✅ 失败场景2: 重点药品未远程审方，无法生成取药码")
        print("  ✅ 失败场景3: 远程审方意见未改变，拒绝提交")
        print("  ✅ 完整流程: 处方5已完成全流程")
        print("=" * 60)
    else:
        print("  - 种子数据已存在，跳过初始化")
