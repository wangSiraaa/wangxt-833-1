"""
验证脚本：上传重点药品处方并验证未审方无法生成取药码

覆盖测试场景：
1. ✅ 上传含重点药品的处方
2. ✅ 药店药师复核通过
3. ✅ 未远程审方时生成取药码 → 应该失败
4. ✅ 远程审方通过（必须改变意见）
5. ✅ 远程审方后生成取药码 → 应该成功
6. ✅ 验证取药码可以正常核销
7. ✅ 验证处方过期无法取药
8. ✅ 验证远程审方意见未改变被拒绝
"""

import asyncio
from datetime import datetime, timedelta
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.database import Base, engine, SessionLocal
from app.seed_data import init_seed_data
from app.models import PrescriptionStatus, AuditOpinion, DrugCategory
from app import crud
from app.schemas import (
    PrescriptionCreate,
    PrescriptionItemCreate,
    PharmacistReview,
    RemoteAudit,
    SupplementNoteCreate
)

Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="session")
def db_session():
    db = SessionLocal()
    try:
        init_seed_data(db)
        _prepare_test_data(db)
        yield db
    finally:
        db.close()


def _prepare_test_data(db):
    now = datetime.utcnow()

    if not crud.get_prescription_by_no(db, "RX_TEST_001"):
        rx1 = crud.create_prescription(
            db,
            PrescriptionCreate(
                prescription_no="RX_TEST_001",
                patient_id=1,
                patient_name="张三",
                patient_id_card="110101199001011234",
                hospital="北京协和医院",
                doctor_name="测试医生",
                diagnosis="术后镇痛测试",
                issue_date=now,
                expire_date=now + timedelta(days=7),
                items=[
                    PrescriptionItemCreate(
                        drug_code="DRUG003",
                        drug_name="氨酚待因片",
                        drug_category=DrugCategory.KEY,
                        specification="每片含对乙酰氨基酚500mg+磷酸可待因8.4mg",
                        dosage="每次1片",
                        frequency="每日3次",
                        quantity=1,
                        unit="盒"
                    )
                ]
            )
        )

        crud.pharmacist_review(
            db, rx1.id,
            PharmacistReview(
                pharmacist_id=4,
                opinion=AuditOpinion.APPROVED,
                remark="药品清单核对无误，含重点药品需远程审方"
            )
        )

        crud.remote_audit(
            db, rx1.id,
            RemoteAudit(
                remote_auditor_id=5,
                opinion=AuditOpinion.APPROVED,
                remark="远程审方通过"
            )
        )

        result = crud.generate_pickup_code(db, rx1.id)
        crud.verify_pickup_code(db, result["pickup_code"])

    if not crud.get_prescription_by_no(db, "RX_TEST_002"):
        rx2 = crud.create_prescription(
            db,
            PrescriptionCreate(
                prescription_no="RX_TEST_002",
                patient_id=1,
                patient_name="张三",
                patient_id_card="110101199001011234",
                hospital="北京协和医院",
                doctor_name="测试医生",
                diagnosis="测试-仅药店复核未远程审方",
                issue_date=now,
                expire_date=now + timedelta(days=7),
                items=[
                    PrescriptionItemCreate(
                        drug_code="DRUG003",
                        drug_name="氨酚待因片",
                        drug_category=DrugCategory.KEY,
                        specification="每片含对乙酰氨基酚500mg+磷酸可待因8.4mg",
                        dosage="每次1片",
                        frequency="每日3次",
                        quantity=1,
                        unit="盒"
                    )
                ]
            )
        )

        crud.pharmacist_review(
            db, rx2.id,
            PharmacistReview(
                pharmacist_id=4,
                opinion=AuditOpinion.APPROVED,
                remark="重点药品处方，等待远程审方"
            )
        )

    if not crud.get_prescription_by_no(db, "RX_TEST_EXPIRED"):
        crud.create_prescription(
            db,
            PrescriptionCreate(
                prescription_no="RX_TEST_EXPIRED",
                patient_id=2,
                patient_name="李四",
                patient_id_card="110101199102022345",
                hospital="测试医院",
                doctor_name="测试医生",
                diagnosis="过期处方测试",
                issue_date=now - timedelta(days=10),
                expire_date=now - timedelta(days=3),
                items=[
                    PrescriptionItemCreate(
                        drug_code="DRUG001",
                        drug_name="阿莫西林胶囊",
                        drug_category=DrugCategory.NORMAL,
                        specification="0.5g*24粒",
                        dosage="每次1粒",
                        frequency="每日3次",
                        quantity=1,
                        unit="盒"
                    )
                ]
            )
        )

    if not crud.get_prescription_by_no(db, "RX_TEST_EXPIRED_2"):
        crud.create_prescription(
            db,
            PrescriptionCreate(
                prescription_no="RX_TEST_EXPIRED_2",
                patient_id=2,
                patient_name="李四",
                patient_id_card="110101199102022345",
                hospital="测试医院",
                doctor_name="测试医生",
                diagnosis="过期处方测试2",
                issue_date=now - timedelta(days=10),
                expire_date=now - timedelta(days=3),
                items=[
                    PrescriptionItemCreate(
                        drug_code="DRUG001",
                        drug_name="阿莫西林胶囊",
                        drug_category=DrugCategory.NORMAL,
                        specification="0.5g*24粒",
                        dosage="每次1粒",
                        frequency="每日3次",
                        quantity=1,
                        unit="盒"
                    )
                ]
            )
        )

    if not crud.get_prescription_by_no(db, "RX_TEST_EXPIRED_3"):
        rx = crud.create_prescription(
            db,
            PrescriptionCreate(
                prescription_no="RX_TEST_EXPIRED_3",
                patient_id=2,
                patient_name="李四",
                patient_id_card="110101199102022345",
                hospital="测试医院",
                doctor_name="测试医生",
                diagnosis="过期处方测试3-已复核",
                issue_date=now - timedelta(days=10),
                expire_date=now - timedelta(days=3),
                items=[
                    PrescriptionItemCreate(
                        drug_code="DRUG001",
                        drug_name="阿莫西林胶囊",
                        drug_category=DrugCategory.NORMAL,
                        specification="0.5g*24粒",
                        dosage="每次1粒",
                        frequency="每日3次",
                        quantity=1,
                        unit="盒"
                    )
                ]
            )
        )
        crud.pharmacist_review(
            db, rx.id,
            PharmacistReview(
                pharmacist_id=4,
                opinion=AuditOpinion.APPROVED,
                remark="已复核但已过期"
            ),
            _skip_expiry_check=True
        )

    if not crud.get_prescription_by_no(db, "RX_REQ_TEST_1"):
        crud.create_prescription(
            db,
            PrescriptionCreate(
                prescription_no="RX_REQ_TEST_1",
                patient_id=3,
                patient_name="王五",
                patient_id_card="110101199203033456",
                hospital="测试医院",
                doctor_name="测试医生",
                diagnosis="需求验证-过期处方复核",
                issue_date=now - timedelta(days=10),
                expire_date=now - timedelta(days=3),
                items=[
                    PrescriptionItemCreate(
                        drug_code="DRUG001",
                        drug_name="阿莫西林胶囊",
                        drug_category=DrugCategory.NORMAL,
                        specification="0.5g*24粒",
                        dosage="每次1粒",
                        frequency="每日3次",
                        quantity=1,
                        unit="盒"
                    )
                ]
            )
        )

    if not crud.get_prescription_by_no(db, "RX_REQ_TEST_2"):
        crud.create_prescription(
            db,
            PrescriptionCreate(
                prescription_no="RX_REQ_TEST_2",
                patient_id=3,
                patient_name="王五",
                patient_id_card="110101199203033456",
                hospital="测试医院",
                doctor_name="测试医生",
                diagnosis="需求验证-过期处方生成取药码",
                issue_date=now - timedelta(days=10),
                expire_date=now - timedelta(days=3),
                items=[
                    PrescriptionItemCreate(
                        drug_code="DRUG001",
                        drug_name="阿莫西林胶囊",
                        drug_category=DrugCategory.NORMAL,
                        specification="0.5g*24粒",
                        dosage="每次1粒",
                        frequency="每日3次",
                        quantity=1,
                        unit="盒"
                    )
                ]
            )
        )

    if not crud.get_prescription_by_no(db, "RX_REQ_TEST_3"):
        rx = crud.create_prescription(
            db,
            PrescriptionCreate(
                prescription_no="RX_REQ_TEST_3",
                patient_id=3,
                patient_name="王五",
                patient_id_card="110101199203033456",
                hospital="测试医院",
                doctor_name="测试医生",
                diagnosis="需求验证-过期处方远程审方",
                issue_date=now - timedelta(days=10),
                expire_date=now - timedelta(days=3),
                items=[
                    PrescriptionItemCreate(
                        drug_code="DRUG001",
                        drug_name="阿莫西林胶囊",
                        drug_category=DrugCategory.NORMAL,
                        specification="0.5g*24粒",
                        dosage="每次1粒",
                        frequency="每日3次",
                        quantity=1,
                        unit="盒"
                    )
                ]
            )
        )
        crud.pharmacist_review(
            db, rx.id,
            PharmacistReview(
                pharmacist_id=4,
                opinion=AuditOpinion.APPROVED,
                remark="已复核"
            ),
            _skip_expiry_check=True
        )

    if not crud.get_prescription_by_no(db, "RX_SUPPLEMENT_PENDING"):
        crud.create_prescription(
            db,
            PrescriptionCreate(
                prescription_no="RX_SUPPLEMENT_PENDING",
                patient_id=1,
                patient_name="张三",
                patient_id_card="110101199001011234",
                hospital="测试医院",
                doctor_name="测试医生",
                diagnosis="补录测试-待审方处方",
                issue_date=now,
                expire_date=now + timedelta(days=7),
                items=[
                    PrescriptionItemCreate(
                        drug_code="DRUG001",
                        drug_name="阿莫西林胶囊",
                        drug_category=DrugCategory.NORMAL,
                        specification="0.5g*24粒",
                        dosage="每次1粒",
                        frequency="每日3次",
                        quantity=1,
                        unit="盒"
                    )
                ]
            )
        )

    if not crud.get_prescription_by_no(db, "RX_SUPPLEMENT_EXPIRED"):
        crud.create_prescription(
            db,
            PrescriptionCreate(
                prescription_no="RX_SUPPLEMENT_EXPIRED",
                patient_id=2,
                patient_name="李四",
                patient_id_card="110101199102022345",
                hospital="测试医院",
                doctor_name="测试医生",
                diagnosis="补录测试-已过期处方",
                issue_date=now - timedelta(days=10),
                expire_date=now - timedelta(days=3),
                items=[
                    PrescriptionItemCreate(
                        drug_code="DRUG001",
                        drug_name="阿莫西林胶囊",
                        drug_category=DrugCategory.NORMAL,
                        specification="0.5g*24粒",
                        dosage="每次1粒",
                        frequency="每日3次",
                        quantity=1,
                        unit="盒"
                    )
                ]
            )
        )

    if not crud.get_prescription_by_no(db, "RX_SUPPLEMENT_PICKED"):
        rx = crud.create_prescription(
            db,
            PrescriptionCreate(
                prescription_no="RX_SUPPLEMENT_PICKED",
                patient_id=1,
                patient_name="张三",
                patient_id_card="110101199001011234",
                hospital="测试医院",
                doctor_name="测试医生",
                diagnosis="补录测试-已核销处方",
                issue_date=now - timedelta(days=5),
                expire_date=now + timedelta(days=2),
                items=[
                    PrescriptionItemCreate(
                        drug_code="DRUG001",
                        drug_name="阿莫西林胶囊",
                        drug_category=DrugCategory.NORMAL,
                        specification="0.5g*24粒",
                        dosage="每次1粒",
                        frequency="每日3次",
                        quantity=1,
                        unit="盒"
                    )
                ]
            )
        )
        crud.pharmacist_review(
            db, rx.id,
            PharmacistReview(
                pharmacist_id=4,
                opinion=AuditOpinion.APPROVED,
                remark="已复核"
            )
        )
        result = crud.generate_pickup_code(db, rx.id)
        crud.verify_pickup_code(db, result["pickup_code"])

    if not crud.get_prescription_by_no(db, "RX_SUPPLEMENT_REVIEWED"):
        rx = crud.create_prescription(
            db,
            PrescriptionCreate(
                prescription_no="RX_SUPPLEMENT_REVIEWED",
                patient_id=1,
                patient_name="张三",
                patient_id_card="110101199001011234",
                hospital="测试医院",
                doctor_name="测试医生",
                diagnosis="补录测试-已复核未审方处方",
                issue_date=now - timedelta(days=2),
                expire_date=now + timedelta(days=5),
                items=[
                    PrescriptionItemCreate(
                        drug_code="DRUG001",
                        drug_name="阿莫西林胶囊",
                        drug_category=DrugCategory.NORMAL,
                        specification="0.5g*24粒",
                        dosage="每次1粒",
                        frequency="每日3次",
                        quantity=1,
                        unit="盒"
                    )
                ]
            )
        )
        crud.pharmacist_review(
            db, rx.id,
            PharmacistReview(
                pharmacist_id=4,
                opinion=AuditOpinion.APPROVED,
                remark="已复核，普通药品无需远程审方"
            )
        )

    db.commit()


class TestKeyDrugPrescriptionFlow:
    """重点药品处方流转流程测试"""

    def test_01_seed_data_exists(self, db_session):
        """测试种子数据初始化成功"""
        prescriptions = crud.get_prescriptions(db_session)
        assert len(prescriptions) >= 5, "种子处方数据缺失"

        drugs = db_session.query(crud.Drug).all()
        assert len(drugs) >= 5, "种子药品数据缺失"

        key_drugs = [d for d in drugs if d.category == DrugCategory.KEY]
        assert len(key_drugs) >= 2, "重点药品数据缺失"

        print("✅ 种子数据初始化成功")

    def test_02_upload_key_drug_prescription(self, db_session):
        """测试上传含重点药品的处方"""
        prescription = crud.get_prescription_by_no(db_session, "RX_TEST_001")
        assert prescription is not None
        assert prescription.prescription_no == "RX_TEST_001"
        assert prescription.has_key_drug == True
        assert len(prescription.items) >= 1
        assert any(item.drug_category == DrugCategory.KEY for item in prescription.items)

        print(f"✅ 重点药品处方已上传，处方ID: {prescription.id}")

    def test_03_pharmacist_review_approved(self, db_session):
        """测试药店药师复核通过"""
        prescription = crud.get_prescription_by_no(db_session, "RX_TEST_001")
        assert prescription is not None
        assert prescription.pharmacist_opinion == AuditOpinion.APPROVED
        assert prescription.pharmacist_id == 4
        assert prescription.pharmacist_review_time is not None

        print("✅ 药店药师已复核通过")

    def test_04_key_drug_without_remote_audit_cannot_generate_code(self, db_session):
        """测试重点药品未远程审方时生成取药码 - 应该失败"""
        prescription = crud.get_prescription_by_no(db_session, "RX_TEST_002")
        assert prescription is not None
        assert prescription.has_key_drug == True
        assert prescription.remote_auditor_opinion == AuditOpinion.PENDING
        assert prescription.status == PrescriptionStatus.PHARMACIST_REVIEWED

        with pytest.raises(ValueError, match="重点药品处方必须经过远程审方通过后才能生成取药码"):
            crud.generate_pickup_code(db_session, prescription.id)

        updated = crud.get_prescription(db_session, prescription.id)
        assert updated.pickup_code is None
        assert updated.status == PrescriptionStatus.PHARMACIST_REVIEWED

        print("✅ 验证通过：未远程审方的重点药品处方无法生成取药码")

    def test_05_remote_audit_must_change_opinion(self, db_session):
        """测试远程审方必须改变审方意见"""
        prescription = crud.get_prescription_by_no(db_session, "RX_TEST_002")
        assert prescription is not None
        assert prescription.remote_auditor_opinion == AuditOpinion.PENDING

        with pytest.raises(ValueError, match="远程审方必须改变审方意见"):
            crud.remote_audit(
                db_session,
                prescription.id,
                RemoteAudit(
                    remote_auditor_id=5,
                    opinion=AuditOpinion.PENDING,
                    remark="意见未改变，应该失败"
                )
            )

        print("✅ 验证通过：远程审方必须改变审方意见")

    def test_06_remote_audit_approved(self, db_session):
        """测试远程审方通过（PENDING → APPROVED）"""
        prescription = crud.get_prescription_by_no(db_session, "RX_TEST_002")
        assert prescription is not None
        assert prescription.remote_auditor_opinion == AuditOpinion.PENDING

        audit_result = crud.remote_audit(
            db_session,
            prescription.id,
            RemoteAudit(
                remote_auditor_id=5,
                opinion=AuditOpinion.APPROVED,
                remark="远程审方通过：重点药品适应症相符，用法用量适宜"
            )
        )

        assert audit_result.status == PrescriptionStatus.REMOTE_AUDITED
        assert audit_result.remote_auditor_opinion == AuditOpinion.APPROVED
        assert audit_result.remote_auditor_id == 5
        assert audit_result.remote_audit_time is not None

        print("✅ 远程审方通过（意见已改变：PENDING → APPROVED）")

    def test_07_generate_pickup_code_after_remote_audit_should_success(self, db_session):
        """测试远程审方通过后生成取药码 - 应该成功"""
        prescription = crud.get_prescription_by_no(db_session, "RX_TEST_002")
        assert prescription is not None
        assert prescription.has_key_drug == True
        assert prescription.remote_auditor_opinion == AuditOpinion.APPROVED

        result = crud.generate_pickup_code(db_session, prescription.id)

        assert result["pickup_code"] is not None
        assert len(result["pickup_code"]) == 8
        assert result["prescription_id"] == prescription.id
        assert result["patient_name"] == "张三"

        updated = crud.get_prescription(db_session, prescription.id)
        assert updated.pickup_code == result["pickup_code"]
        assert updated.status == PrescriptionStatus.PICKUP_CODE_GENERATED
        assert updated.pickup_code_expire is not None

        print(f"✅ 取药码生成成功：{result['pickup_code']}")

    def test_08_verify_pickup_code(self, db_session):
        """测试核销取药码（使用已完成全流程的RX_TEST_001）"""
        prescription = crud.get_prescription_by_no(db_session, "RX_TEST_001")
        assert prescription is not None
        assert prescription.status == PrescriptionStatus.PICKED_UP
        assert prescription.picked_up_time is not None

        print("✅ 取药码已核销成功")

    def test_09_expired_prescription_cannot_generate_code(self, db_session):
        """测试过期处方无法生成取药码"""
        prescription = crud.get_prescription_by_no(db_session, "RX_TEST_EXPIRED")
        assert prescription is not None
        assert prescription.is_expired() == True

        with pytest.raises(ValueError, match="处方已过期，无法取药"):
            crud.generate_pickup_code(db_session, prescription.id)

        updated = crud.get_prescription(db_session, prescription.id)
        assert updated.status == PrescriptionStatus.EXPIRED

        print("✅ 验证通过：过期处方无法生成取药码")

    def test_10_audit_logs_complete(self, db_session):
        """测试稽核查询 - 操作日志完整"""
        prescription = crud.get_prescription_by_no(db_session, "RX_TEST_001")
        assert prescription is not None

        logs = crud.get_audit_logs(db_session, prescription.id)
        assert len(logs) >= 5

        actions = [log.action for log in logs]
        assert "处方上传" in actions
        assert "药店药师复核" in actions
        assert "远程审方" in actions
        assert "生成取药码" in actions
        assert "取药核销" in actions

        print("✅ 稽核查询验证通过：操作日志完整")

    def test_11_audit_opinion_history(self, db_session):
        """测试稽核查询 - 审方意见历史"""
        prescription = crud.get_prescription_by_no(db_session, "RX_TEST_001")
        assert prescription is not None

        history = crud.get_audit_opinion_history(db_session, prescription.id)

        assert history["prescription_id"] == prescription.id
        assert history["pharmacist_opinion"] == AuditOpinion.APPROVED.value
        assert history["remote_auditor_opinion"] == AuditOpinion.APPROVED.value
        assert len(history["pharmacist_history"]) >= 1
        assert len(history["remote_auditor_history"]) >= 1

        for log in history["pharmacist_history"]:
            assert "old_opinion" in log
            assert "new_opinion" in log
            assert isinstance(log["old_opinion"], (str, type(None)))
            assert isinstance(log["new_opinion"], (str, type(None)))

        for log in history["remote_auditor_history"]:
            assert "old_opinion" in log
            assert "new_opinion" in log
            assert isinstance(log["old_opinion"], (str, type(None)))
            assert isinstance(log["new_opinion"], (str, type(None)))

        print("✅ 稽核查询验证通过：审方意见历史完整")

    def test_12_seed_prescription2_needs_remote_audit(self, db_session):
        """验证种子数据中的处方2（重点药品未远程审方）无法生成取药码"""
        prescription = crud.get_prescription_by_no(db_session, "RX202606010002")
        assert prescription is not None
        assert prescription.has_key_drug == True
        assert prescription.status == PrescriptionStatus.PHARMACIST_REVIEWED
        assert prescription.remote_auditor_opinion == AuditOpinion.PENDING

        with pytest.raises(ValueError, match="重点药品处方必须经过远程审方通过后才能生成取药码"):
            crud.generate_pickup_code(db_session, prescription.id)

        print("✅ 种子数据验证：处方2（重点药品未远程审方）无法生成取药码")

    def test_13_seed_prescription4_expired(self, db_session):
        """验证种子数据中的处方4（已过期）无法生成取药码"""
        prescription = crud.get_prescription_by_no(db_session, "RX202606010004")
        assert prescription is not None
        assert prescription.is_expired() == True

        with pytest.raises(ValueError, match="处方已过期，无法取药"):
            crud.generate_pickup_code(db_session, prescription.id)

        print("✅ 种子数据验证：处方4（已过期）无法生成取药码")

    def test_14_seed_prescription3_opinion_changed(self, db_session):
        """验证种子数据中的处方3远程审方意见已改变多次"""
        prescription = crud.get_prescription_by_no(db_session, "RX202606010003")
        assert prescription is not None

        history = crud.get_audit_opinion_history(db_session, prescription.id)
        assert len(history["remote_auditor_history"]) >= 2

        opinions = [log["new_opinion"] for log in history["remote_auditor_history"]]
        assert AuditOpinion.APPROVED.value in opinions
        assert AuditOpinion.NEED_REVIEW.value in opinions

        for i in range(1, len(history["remote_auditor_history"])):
            assert history["remote_auditor_history"][i]["old_opinion"] != \
                   history["remote_auditor_history"][i]["new_opinion"], \
                   "远程审方意见必须每次都改变"

        for log in history["remote_auditor_history"]:
            assert isinstance(log["old_opinion"], str) or log["old_opinion"] is None
            assert isinstance(log["new_opinion"], str)
            assert isinstance(log["operator_role"], str)
            assert isinstance(log["created_at"], str)

        print("✅ 种子数据验证：处方3远程审方意见多次改变")


class TestApiIntegration:
    """API集成测试 - 通过HTTP接口验证完整流程"""

    @pytest.fixture(scope="function")
    async def async_client(self):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_complete_key_drug_flow_api(self, async_client):
        """测试：上传重点药品处方并验证未审方无法生成取药码"""
        now = datetime.utcnow()

        prescription_data = {
            "prescription_no": f"RX_API_TEST_{now.strftime('%Y%m%d%H%M%S')}",
            "patient_id": 1,
            "patient_name": "张三",
            "patient_id_card": "110101199001011234",
            "hospital": "北京协和医院",
            "doctor_name": "API测试医生",
            "diagnosis": "API测试-术后镇痛",
            "issue_date": now.isoformat(),
            "expire_date": (now + timedelta(days=7)).isoformat(),
            "items": [
                {
                    "drug_code": "DRUG004",
                    "drug_name": "盐酸曲马多缓释片",
                    "drug_category": "KEY",
                    "specification": "100mg*10片",
                    "dosage": "每次1片",
                    "frequency": "每日2次",
                    "quantity": 1,
                    "unit": "盒"
                }
            ]
        }

        response = await async_client.post("/api/prescriptions", json=prescription_data)
        assert response.status_code == 200
        data = response.json()
        prescription_id = data["data"]["prescription_id"]
        print(f"  ✅ API - 处方上传成功，ID: {prescription_id}")

        response = await async_client.post(
            f"/api/prescriptions/{prescription_id}/pharmacist-review",
            json={
                "pharmacist_id": 4,
                "opinion": "APPROVED",
                "remark": "药店药师复核通过"
            }
        )
        assert response.status_code == 200
        print("  ✅ API - 药店药师复核通过")

        response = await async_client.post(f"/api/pickup/{prescription_id}/generate-code")
        assert response.status_code == 400
        assert "重点药品处方必须经过远程审方通过后才能生成取药码" in response.json()["detail"]
        print("  ✅ API - 未远程审方生成取药码被拒绝")

        response = await async_client.post(
            f"/api/prescriptions/{prescription_id}/remote-audit",
            json={
                "remote_auditor_id": 5,
                "opinion": "APPROVED",
                "remark": "远程审方通过"
            }
        )
        assert response.status_code == 200
        assert response.json()["data"]["opinion_changed"] == True
        print("  ✅ API - 远程审方通过，意见已改变")

        response = await async_client.post(f"/api/pickup/{prescription_id}/generate-code")
        assert response.status_code == 200
        pickup_code = response.json()["data"]["pickup_code"]
        assert len(pickup_code) == 8
        print(f"  ✅ API - 取药码生成成功: {pickup_code}")

        response = await async_client.post(
            "/api/pickup/verify",
            json={"pickup_code": pickup_code}
        )
        assert response.status_code == 200
        assert response.json()["data"]["status"] == "PICKED_UP"
        print("  ✅ API - 取药码核销成功")

        response = await async_client.get(f"/api/audit/prescriptions/{prescription_id}/logs")
        assert response.status_code == 200
        assert response.json()["data"]["total"] >= 5
        print("  ✅ API - 稽核查询-操作日志完整")

        print("✅ API集成测试全部通过")

    @pytest.mark.asyncio
    async def test_remote_audit_opinion_history_api(self, async_client):
        """测试：远程审方后通过HTTP接口读取审方意见结果"""
        now = datetime.utcnow()
        prescription_no = f"RX_OP_HIST_{now.strftime('%Y%m%d%H%M%S')}"

        prescription_data = {
            "prescription_no": prescription_no,
            "patient_id": 2,
            "patient_name": "李四",
            "patient_id_card": "110101199002025678",
            "hospital": "北京协和医院",
            "doctor_name": "李医生",
            "diagnosis": "急性疼痛需镇痛",
            "issue_date": now.isoformat(),
            "expire_date": (now + timedelta(days=7)).isoformat(),
            "items": [
                {
                    "drug_code": "DRUG005",
                    "drug_name": "盐酸羟考酮缓释片",
                    "drug_category": "KEY",
                    "specification": "10mg*10片",
                    "dosage": "每次1片",
                    "frequency": "每日2次",
                    "quantity": 1,
                    "unit": "盒"
                }
            ]
        }

        response = await async_client.post("/api/prescriptions", json=prescription_data)
        assert response.status_code == 200
        data = response.json()
        prescription_id = data["data"]["prescription_id"]
        print(f"  ✅ API - 处方上传成功，ID: {prescription_id}")

        response = await async_client.get(
            f"/api/audit/prescriptions/{prescription_id}/opinion-history"
        )
        assert response.status_code == 200
        history_data = response.json()["data"]
        assert history_data["remote_auditor_opinion"] == "PENDING"
        assert history_data["pharmacist_opinion"] == "PENDING"
        assert len(history_data["remote_auditor_history"]) == 0
        assert len(history_data["pharmacist_history"]) == 0
        print("  ✅ API - 审方前读取：审方意见为PENDING，历史记录为空")

        response = await async_client.post(
            f"/api/prescriptions/{prescription_id}/pharmacist-review",
            json={
                "pharmacist_id": 4,
                "opinion": "APPROVED",
                "remark": "药店药师复核通过，确认重点药品"
            }
        )
        assert response.status_code == 200
        print("  ✅ API - 药店药师复核通过")

        response = await async_client.get(
            f"/api/audit/prescriptions/{prescription_id}/opinion-history"
        )
        assert response.status_code == 200
        history_data = response.json()["data"]
        assert history_data["pharmacist_opinion"] == "APPROVED"
        assert history_data["remote_auditor_opinion"] == "PENDING"
        assert len(history_data["pharmacist_history"]) == 1
        assert history_data["pharmacist_history"][0]["old_opinion"] == "PENDING"
        assert history_data["pharmacist_history"][0]["new_opinion"] == "APPROVED"
        assert history_data["pharmacist_history"][0]["operator_role"] == "PHARMACIST"
        print("  ✅ API - 药师复核后读取：药师意见已更新，历史记录可追溯")

        response = await async_client.post(
            f"/api/prescriptions/{prescription_id}/remote-audit",
            json={
                "remote_auditor_id": 5,
                "opinion": "NEED_REVIEW",
                "remark": "请补充患者疼痛评分记录"
            }
        )
        assert response.status_code == 200
        assert response.json()["data"]["opinion_changed"] == True
        print("  ✅ API - 远程审方第一次：PENDING → NEED_REVIEW")

        response = await async_client.get(
            f"/api/audit/prescriptions/{prescription_id}/opinion-history"
        )
        assert response.status_code == 200
        history_data = response.json()["data"]
        assert history_data["remote_auditor_opinion"] == "NEED_REVIEW"
        assert len(history_data["remote_auditor_history"]) == 1
        assert history_data["remote_auditor_history"][0]["old_opinion"] == "PENDING"
        assert history_data["remote_auditor_history"][0]["new_opinion"] == "NEED_REVIEW"
        assert history_data["remote_auditor_history"][0]["operator_role"] == "REMOTE_AUDITOR"
        assert isinstance(history_data["remote_auditor_history"][0]["created_at"], str)
        assert "T" in history_data["remote_auditor_history"][0]["created_at"]
        print("  ✅ API - 第一次远程审方后读取：意见从PENDING改为NEED_REVIEW，历史记录完整")

        response = await async_client.post(
            f"/api/prescriptions/{prescription_id}/remote-audit",
            json={
                "remote_auditor_id": 5,
                "opinion": "APPROVED",
                "remark": "已补充疼痛评分，同意发药"
            }
        )
        assert response.status_code == 200
        assert response.json()["data"]["opinion_changed"] == True
        print("  ✅ API - 远程审方第二次：NEED_REVIEW → APPROVED")

        response = await async_client.get(
            f"/api/audit/prescriptions/{prescription_id}/opinion-history"
        )
        assert response.status_code == 200
        history_data = response.json()["data"]
        assert history_data["remote_auditor_opinion"] == "APPROVED"
        assert history_data["pharmacist_opinion"] == "APPROVED"
        assert len(history_data["remote_auditor_history"]) == 2
        assert history_data["remote_auditor_history"][0]["old_opinion"] == "NEED_REVIEW"
        assert history_data["remote_auditor_history"][0]["new_opinion"] == "APPROVED"
        assert history_data["remote_auditor_history"][1]["old_opinion"] == "PENDING"
        assert history_data["remote_auditor_history"][1]["new_opinion"] == "NEED_REVIEW"

        for log in history_data["remote_auditor_history"]:
            assert isinstance(log["old_opinion"], str) or log["old_opinion"] is None
            assert isinstance(log["new_opinion"], str)
            assert isinstance(log["operator_role"], str)
            assert isinstance(log["created_at"], str)
            assert "old_status" in log
            assert "new_status" in log
            assert "remark" in log

        for log in history_data["pharmacist_history"]:
            assert isinstance(log["old_opinion"], str) or log["old_opinion"] is None
            assert isinstance(log["new_opinion"], str)
            assert isinstance(log["operator_role"], str)
            assert isinstance(log["created_at"], str)

        print("  ✅ API - 第二次远程审方后读取：意见从NEED_REVIEW改为APPROVED，完整历史可追溯")

        print("✅ HTTP层测试通过：远程审方后读取审方意见结果正常")

    @pytest.mark.asyncio
    async def test_supplement_note_api(self, async_client):
        """测试：临时补录说明 API 集成测试"""
        now = datetime.utcnow()

        prescription_data = {
            "prescription_no": f"RX_API_SUPP_{now.strftime('%Y%m%d%H%M%S')}",
            "patient_id": 1,
            "patient_name": "测试患者",
            "patient_id_card": "110101199001011234",
            "hospital": "测试医院",
            "doctor_name": "测试医生",
            "diagnosis": "API补录测试",
            "issue_date": now.isoformat(),
            "expire_date": (now + timedelta(days=7)).isoformat(),
            "items": [
                {
                    "drug_code": "DRUG001",
                    "drug_name": "阿莫西林胶囊",
                    "drug_category": "NORMAL",
                    "specification": "0.5g*24粒",
                    "dosage": "每次1粒",
                    "frequency": "每日3次",
                    "quantity": 1,
                    "unit": "盒"
                }
            ]
        }

        response = await async_client.post("/api/prescriptions", json=prescription_data)
        assert response.status_code == 200
        prescription_id = response.json()["data"]["prescription_id"]
        print(f"  ✅ API - 处方上传成功，ID: {prescription_id}")

        supplement_data = {
            "missing_reason": "处方附件缺少缴费凭证",
            "supplement_deadline": (now + timedelta(hours=24)).isoformat(),
            "handler_id": 4,
            "remark": "请患者24小时内补交缴费凭证"
        }

        response = await async_client.post(
            f"/api/prescriptions/{prescription_id}/supplement-note",
            json=supplement_data
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["missing_reason"] == "处方附件缺少缴费凭证"
        assert data["handler_name"] is not None
        print(f"  ✅ API - 补录说明成功，记录ID: {data['record_id']}")

        response = await async_client.get(
            f"/api/prescriptions/{prescription_id}/supplement-notes"
        )
        assert response.status_code == 200
        notes_data = response.json()["data"]
        assert notes_data["total"] >= 1
        assert notes_data["items"][0]["missing_reason"] == "处方附件缺少缴费凭证"
        print("  ✅ API - 查询补录记录成功")

        response = await async_client.get(
            f"/api/audit/prescriptions/{prescription_id}/opinion-history"
        )
        assert response.status_code == 200
        history_data = response.json()["data"]
        assert "supplement_records" in history_data
        assert len(history_data["supplement_records"]) >= 1
        print("  ✅ API - 审方详情中包含补录记录")

        print("  ✅ API - 待审方处方补录说明测试通过")

        prescription_data2 = {
            "prescription_no": f"RX_API_SUPP_EXP_{now.strftime('%Y%m%d%H%M%S')}",
            "patient_id": 2,
            "patient_name": "测试患者2",
            "patient_id_card": "110101199102022345",
            "hospital": "测试医院",
            "doctor_name": "测试医生",
            "diagnosis": "API补录过期测试",
            "issue_date": (now - timedelta(days=10)).isoformat(),
            "expire_date": (now - timedelta(days=3)).isoformat(),
            "items": [
                {
                    "drug_code": "DRUG001",
                    "drug_name": "阿莫西林胶囊",
                    "drug_category": "NORMAL",
                    "specification": "0.5g*24粒",
                    "dosage": "每次1粒",
                    "frequency": "每日3次",
                    "quantity": 1,
                    "unit": "盒"
                }
            ]
        }

        response = await async_client.post("/api/prescriptions", json=prescription_data2)
        assert response.status_code == 200
        prescription_id2 = response.json()["data"]["prescription_id"]
        print(f"  ✅ API - 过期处方上传成功，ID: {prescription_id2}")

        supplement_data2 = {
            "missing_reason": "测试过期处方补录",
            "supplement_deadline": (now + timedelta(hours=24)).isoformat(),
            "handler_id": 4
        }

        response = await async_client.post(
            f"/api/prescriptions/{prescription_id2}/supplement-note",
            json=supplement_data2
        )
        assert response.status_code == 400
        assert "处方已过期，无法补录说明" in response.json()["detail"]
        print(f"  ✅ API - 已过期处方补录被拒绝，错误信息: {response.json()['detail']}")

        print("✅ API临时补录说明集成测试通过")


class TestKeyRequirementValidation:
    """核心需求验证测试"""

    def test_prescription_expired_cannot_take_medicine(self, db_session):
        """需求1: 处方过期不能取药"""
        rx1 = crud.get_prescription_by_no(db_session, "RX_REQ_TEST_1")
        assert rx1 is not None
        assert rx1.is_expired() == True
        assert rx1.status == PrescriptionStatus.UPLOADED

        with pytest.raises(ValueError, match="处方已过期，无法取药"):
            crud.pharmacist_review(
                db_session, rx1.id,
                PharmacistReview(pharmacist_id=4, opinion=AuditOpinion.APPROVED)
            )
        print("✅ 需求验证：处方过期，药店药师复核失败")

        db_session.refresh(rx1)
        assert rx1.status == PrescriptionStatus.EXPIRED
        print("✅ 需求验证：处方过期自动标记为EXPIRED状态")

        rx2 = crud.get_prescription_by_no(db_session, "RX_REQ_TEST_2")
        assert rx2 is not None
        assert rx2.is_expired() == True
        assert rx2.status == PrescriptionStatus.UPLOADED

        with pytest.raises(ValueError, match="处方已过期，无法取药"):
            crud.generate_pickup_code(db_session, rx2.id)
        print("✅ 需求验证：处方过期，无法生成取药码")

        db_session.refresh(rx2)
        assert rx2.status == PrescriptionStatus.EXPIRED
        print("✅ 需求验证：过期处方生成取药码时自动标记为EXPIRED")

        rx3 = crud.get_prescription_by_no(db_session, "RX_REQ_TEST_3")
        assert rx3 is not None
        assert rx3.is_expired() == True
        assert rx3.status == PrescriptionStatus.PHARMACIST_REVIEWED

        with pytest.raises(ValueError, match="处方已过期，无法取药"):
            crud.remote_audit(
                db_session, rx3.id,
                RemoteAudit(remote_auditor_id=5, opinion=AuditOpinion.APPROVED)
            )
        print("✅ 需求验证：处方过期，远程审方失败")

        db_session.refresh(rx3)
        assert rx3.status == PrescriptionStatus.EXPIRED
        print("✅ 需求验证：过期处方远程审方时自动标记为EXPIRED")

    def test_key_drug_must_have_remote_audit(self, db_session):
        """需求2: 重点药品必须远程审方"""
        prescription = crud.get_prescription_by_no(db_session, "RX202606010002")
        assert prescription is not None
        assert prescription.has_key_drug == True
        assert prescription.remote_auditor_opinion == AuditOpinion.PENDING

        with pytest.raises(ValueError, match="重点药品处方必须经过远程审方通过后才能生成取药码"):
            crud.generate_pickup_code(db_session, prescription.id)
        print("✅ 需求验证：重点药品未远程审方，无法生成取药码")

    def test_remote_audit_must_change_opinion(self, db_session):
        """需求3: 远程审方必须改变审方意见"""
        prescription = crud.get_prescription_by_no(db_session, "RX202606010003")
        assert prescription is not None
        current_opinion = prescription.remote_auditor_opinion

        with pytest.raises(ValueError, match="远程审方必须改变审方意见"):
            crud.remote_audit(
                db_session, prescription.id,
                RemoteAudit(
                    remote_auditor_id=5,
                    opinion=current_opinion,
                    remark="意见未改变，应该失败"
                )
            )
        print(f"✅ 需求验证：远程审方意见未改变（{current_opinion}→{current_opinion}）被拒绝")

        history = crud.get_audit_opinion_history(db_session, prescription.id)
        assert len(history["remote_auditor_history"]) >= 2
        print("✅ 需求验证：远程审方历史记录完整，可读取审方意见结果")


class TestSupplementNote:
    """临时补录说明功能测试"""

    def test_01_supplement_note_for_pending_prescription_success(self, db_session):
        """测试：给待审方处方补录说明成功"""
        prescription = crud.get_prescription_by_no(db_session, "RX_SUPPLEMENT_PENDING")
        assert prescription is not None
        assert prescription.status == PrescriptionStatus.UPLOADED
        assert prescription.is_expired() == False

        now = datetime.utcnow()
        supplement_deadline = now + timedelta(days=3)
        note = SupplementNoteCreate(
            missing_reason="处方附件缺少患者身份证照片",
            supplement_deadline=supplement_deadline,
            handler_id=4,
            remark="请患者尽快补交身份证照片"
        )

        record = crud.add_supplement_note(db_session, prescription.id, note)

        assert record is not None
        assert record.prescription_id == prescription.id
        assert record.missing_reason == "处方附件缺少患者身份证照片"
        assert record.handler_id == 4
        assert record.handler_name is not None
        assert record.supplement_deadline == supplement_deadline
        assert record.remark == "请患者尽快补交身份证照片"
        assert record.created_at is not None

        print(f"✅ 补录说明成功，记录ID: {record.id}，处理人: {record.handler_name}")

    def test_02_supplement_note_record_in_audit_detail(self, db_session):
        """测试：补录记录能在审方详情里查到"""
        prescription = crud.get_prescription_by_no(db_session, "RX_SUPPLEMENT_PENDING")
        assert prescription is not None

        history = crud.get_audit_opinion_history(db_session, prescription.id)
        assert "supplement_records" in history
        assert len(history["supplement_records"]) >= 1

        supplement_record = history["supplement_records"][0]
        assert supplement_record["missing_reason"] == "处方附件缺少患者身份证照片"
        assert supplement_record["handler_id"] == 4
        assert supplement_record["handler_name"] is not None
        assert "supplement_deadline" in supplement_record
        assert "created_at" in supplement_record

        print("✅ 审方详情中可查到补录记录")

    def test_03_supplement_note_for_expired_prescription_rejected(self, db_session):
        """测试：给已过期处方补录说明被拒绝"""
        prescription = crud.get_prescription_by_no(db_session, "RX_SUPPLEMENT_EXPIRED")
        assert prescription is not None
        assert prescription.is_expired() == True

        now = datetime.utcnow()
        note = SupplementNoteCreate(
            missing_reason="测试过期处方补录",
            supplement_deadline=now + timedelta(days=1),
            handler_id=4
        )

        with pytest.raises(ValueError, match="处方已过期，无法补录说明") as exc_info:
            crud.add_supplement_note(db_session, prescription.id, note)

        updated = crud.get_prescription(db_session, prescription.id)
        assert updated.status == PrescriptionStatus.EXPIRED

        print(f"✅ 已过期处方补录被拒绝，错误信息: {exc_info.value}")

    def test_04_supplement_note_for_picked_up_prescription_rejected(self, db_session):
        """测试：给已核销处方补录说明被拒绝"""
        prescription = crud.get_prescription_by_no(db_session, "RX_SUPPLEMENT_PICKED")
        assert prescription is not None
        assert prescription.status == PrescriptionStatus.PICKED_UP

        now = datetime.utcnow()
        note = SupplementNoteCreate(
            missing_reason="测试已核销处方补录",
            supplement_deadline=now + timedelta(days=1),
            handler_id=4
        )

        with pytest.raises(ValueError, match="处方已核销，无法补录说明") as exc_info:
            crud.add_supplement_note(db_session, prescription.id, note)

        print(f"✅ 已核销处方补录被拒绝，错误信息: {exc_info.value}")

    def test_05_supplement_note_for_reviewed_prescription_rejected(self, db_session):
        """测试：给非待审方状态处方补录说明被拒绝"""
        prescription = crud.get_prescription_by_no(db_session, "RX_SUPPLEMENT_REVIEWED")
        assert prescription is not None
        assert prescription.status == PrescriptionStatus.PHARMACIST_REVIEWED

        now = datetime.utcnow()
        note = SupplementNoteCreate(
            missing_reason="测试已复核处方补录",
            supplement_deadline=now + timedelta(days=1),
            handler_id=4
        )

        with pytest.raises(ValueError, match="仅待审方（UPLOADED）状态的处方可补录说明") as exc_info:
            crud.add_supplement_note(db_session, prescription.id, note)

        print(f"✅ 非待审方状态处方补录被拒绝，错误信息: {exc_info.value}")

    def test_06_acceptance_test_full_flow(self, db_session):
        """验收用例：给待审方处方补录说明成功，再尝试给已过期处方补录并看到拒绝原因"""
        print("\n=== 验收用例开始 ===")

        print("\n步骤1: 给待审方处方补录说明")
        pending_rx = crud.get_prescription_by_no(db_session, "RX_SUPPLEMENT_PENDING")
        assert pending_rx is not None
        assert pending_rx.status == PrescriptionStatus.UPLOADED

        now = datetime.utcnow()
        deadline = now + timedelta(hours=48)
        note = SupplementNoteCreate(
            missing_reason="处方附件缺少医生签章",
            supplement_deadline=deadline,
            handler_id=4,
            remark="请联系医院补盖医生签章后重新上传"
        )

        record = crud.add_supplement_note(db_session, pending_rx.id, note)
        assert record is not None
        assert record.missing_reason == "处方附件缺少医生签章"
        print(f"✅ 待审方处方补录成功，记录ID: {record.id}")

        print("\n步骤2: 在审方详情中查询补录记录")
        history = crud.get_audit_opinion_history(db_session, pending_rx.id)
        assert len(history["supplement_records"]) >= 1
        latest_record = history["supplement_records"][0]
        assert latest_record["missing_reason"] == "处方附件缺少医生签章"
        assert latest_record["handler_name"] is not None
        print(f"✅ 审方详情中查到补录记录，处理人: {latest_record['handler_name']}")

        print("\n步骤3: 尝试给已过期处方补录说明")
        expired_rx = crud.get_prescription_by_no(db_session, "RX_SUPPLEMENT_EXPIRED")
        assert expired_rx is not None
        assert expired_rx.is_expired() == True

        note2 = SupplementNoteCreate(
            missing_reason="测试过期处方",
            supplement_deadline=deadline,
            handler_id=4
        )

        try:
            crud.add_supplement_note(db_session, expired_rx.id, note2)
            assert False, "应该抛出异常"
        except ValueError as e:
            error_msg = str(e)
            assert "处方已过期，无法补录说明" in error_msg
            print(f"❌ 已过期处方补录被拒绝，拒绝原因: {error_msg}")

        print("\n步骤4: 验证重点药品远程审方限制未放松")
        key_drug_rx = crud.get_prescription_by_no(db_session, "RX202606010002")
        assert key_drug_rx is not None
        assert key_drug_rx.has_key_drug == True
        assert key_drug_rx.remote_auditor_opinion == AuditOpinion.PENDING

        with pytest.raises(ValueError, match="重点药品处方必须经过远程审方通过后才能生成取药码"):
            crud.generate_pickup_code(db_session, key_drug_rx.id)
        print("✅ 重点药品远程审方限制未放松")

        print("\n=== 验收用例全部通过 ===")
