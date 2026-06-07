# 药店处方流转审方 API 服务

## 项目概述

本项目是一个可本地验收的药店处方流转审方API服务，实现了处方从上传到取药的完整流程，包括药品校验、远程审方、取药码生成、核销、稽核查询等核心功能。

## 核心功能

| 功能 | 说明 |
|------|------|
| 处方上传 | 患者提交处方信息和药品清单 |
| 药品校验 | 自动识别重点药品（麻醉/精神类） |
| 药店药师复核 | 药店药师审核药品清单，给出审方意见 |
| 远程审方 | 重点药品必须经过远程审方，且**必须改变审方意见** |
| 取药码生成 | 校验处方有效期和审方状态后生成取药码 |
| 核销 | 取药时核销取药码 |
| 稽核查询 | 支持多维度查询处方流转记录和审方历史 |

## 核心业务规则

1. **处方过期不能取药**：处方超过有效期后，无法进行复核、审方、生成取药码、核销等任何操作
2. **重点药品必须远程审方**：含有重点药品（麻醉/精神类）的处方，必须经过远程审方师审核通过后才能生成取药码
3. **远程审方必须改变审方意见**：远程审方师提交的意见不能与原意见相同，确保真实审核
4. **普通药品仅需药店药师复核**：不含重点药品的处方，药店药师复核通过后即可生成取药码

## 状态流转

```
处方上传(UPLOADED)
    │
    ├─► 处方过期(EXPIRED) ── 结束
    │
    ▼
药店药师复核(PHARMACIST_REVIEWED)
    │
    ├─► 驳回(REJECTED) ── 结束
    │
    ▼
远程审方(REMOTE_AUDITED) 「仅重点药品需要」
    │
    ├─► 驳回(REJECTED) ── 结束
    │
    ▼
取药码生成(PICKUP_CODE_GENERATED)
    │
    ├─► 取药码过期 ── 结束
    │
    ▼
已取药(PICKED_UP) ── 结束
```

## 角色说明

| 角色 | 权限 |
|------|------|
| 患者 | 提交处方、查看处方状态、获取取药码 |
| 药店药师 | 复核药品清单、给出审方意见 |
| 远程审方师 | 审核重点药品处方、给出审方意见 |

## 快速开始

### 方式一：Docker Compose 启动（推荐）

```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

服务启动后访问：http://localhost:8000

### 方式二：本地 Python 环境启动

```bash
# 1. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 方式三：使用启动脚本

```bash
chmod +x start.sh
./start.sh
```

## 访问接口文档

服务启动后，可以通过以下地址访问交互式API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 健康检查

```bash
curl http://localhost:8000/health
```

返回示例：
```json
{"status": "healthy", "timestamp": "2026-06-07T00:00:00Z"}
```

## API 接口列表

### 1. 处方管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/prescriptions | 上传处方 |
| GET | /api/prescriptions | 查询处方列表 |
| GET | /api/prescriptions/{id} | 查询处方详情 |
| POST | /api/prescriptions/{id}/pharmacist-review | 药店药师复核 |
| POST | /api/prescriptions/{id}/remote-audit | 远程审方 |

### 2. 取药管理

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/pickup/{prescription_id}/generate-code | 生成取药码 |
| POST | /api/pickup/verify | 核销取药码 |

### 3. 稽核查询

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/audit/prescriptions | 稽核查询处方 |
| GET | /api/audit/prescriptions/{id}/logs | 查询操作日志 |
| GET | /api/audit/prescriptions/{id}/opinion-history | 查询审方意见历史 |

## 种子数据说明

服务首次启动时会自动初始化种子数据，覆盖以下场景：

### 正常场景
1. **处方1（RX202606010001）**：普通药品处方，药店药师已复核通过，可直接生成取药码
2. **处方2（RX202606010002）**：重点药品处方，药店药师已复核通过，等待远程审方
3. **处方3（RX202606010003）**：重点+普通药品混合处方，远程审方师多次改意见（PENDING→APPROVED→NEED_REVIEW→APPROVED）
4. **处方5（RX202606010005）**：普通药品处方，已完成全流程（上传→复核→取药码生成）

### 失败场景
1. **处方4（RX202606010004）**：已过期处方，任何操作都会提示"处方已过期，无法取药"
2. **处方2（RX202606010002）**：重点药品未经过远程审方，生成取药码会被拒绝
3. **远程审方意见未改变**：提交与原意见相同的审方意见会被拒绝

## 验收验证

### 重点验证场景：上传重点药品处方并验证未审方无法生成取药码

```bash
# 运行自动化验证脚本
pytest tests/test_key_drug_flow.py -v
```

或手动验证：

```bash
# 1. 查询处方2（重点药品处方，已药店复核但未远程审方）
curl http://localhost:8000/api/prescriptions?prescription_no=RX202606010002

# 2. 尝试生成取药码（应该失败：重点药品必须经过远程审方）
curl -X POST http://localhost:8000/api/pickup/2/generate-code

# 预期返回：
# {"detail": "重点药品处方必须经过远程审方通过后才能生成取药码"}

# 3. 远程审方通过
curl -X POST http://localhost:8000/api/prescriptions/2/remote-audit \
  -H "Content-Type: application/json" \
  -d '{"remote_auditor_id": 5, "opinion": "APPROVED", "remark": "远程审方通过"}'

# 4. 再次生成取药码（应该成功）
curl -X POST http://localhost:8000/api/pickup/2/generate-code
```

### 验证处方过期场景

```bash
# 尝试对已过期处方4进行任何操作（应该失败）
curl -X POST http://localhost:8000/api/pickup/4/generate-code

# 预期返回：
# {"detail": "处方已过期，无法取药"}
```

### 验证远程审方必须改变意见

```bash
# 处方3当前远程审方意见为APPROVED，再次提交APPROVED（应该失败）
curl -X POST http://localhost:8000/api/prescriptions/3/remote-audit \
  -H "Content-Type: application/json" \
  -d '{"remote_auditor_id": 5, "opinion": "APPROVED", "remark": "意见未改变"}'

# 预期返回：
# {"detail": "远程审方必须改变审方意见，不能与原意见相同"}
```

## 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── main.py              # 主入口
│   ├── models.py            # 数据模型
│   ├── schemas.py           # Pydantic模式
│   ├── database.py          # 数据库配置
│   ├── crud.py              # 业务逻辑
│   ├── seed_data.py         # 种子数据
│   └── routers/
│       ├── __init__.py
│       ├── prescription.py  # 处方管理API
│       ├── pickup.py        # 取药管理API
│       └── audit_query.py   # 稽核查询API
├── tests/
│   ├── __init__.py
│   └── test_key_drug_flow.py # 重点药品流程验证脚本
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── start.sh
└── README.md
```

## 数据库表结构

- `users` - 用户表（患者、药店药师、远程审方师）
- `drugs` - 药品表（普通药品、重点药品）
- `prescriptions` - 处方主表
- `prescription_items` - 处方明细表
- `audit_logs` - 操作日志表

## 枚举值说明

### PrescriptionStatus（处方状态）
- `UPLOADED` - 已上传
- `PHARMACIST_REVIEWED` - 药店药师已复核
- `REMOTE_AUDITED` - 远程审方完成
- `PICKUP_CODE_GENERATED` - 取药码已生成
- `PICKED_UP` - 已取药
- `EXPIRED` - 已过期
- `REJECTED` - 已驳回

### AuditOpinion（审方意见）
- `PENDING` - 待审核
- `APPROVED` - 通过
- `REJECTED` - 驳回
- `NEED_REVIEW` - 需复审

### DrugCategory（药品分类）
- `NORMAL` - 普通药品
- `KEY` - 重点药品（麻醉/精神类等需特殊管制）

### UserRole（用户角色）
- `PATIENT` - 患者
- `PHARMACIST` - 药店药师
- `REMOTE_AUDITOR` - 远程审方师

## 测试账号

| 用户名 | 姓名 | 角色 | ID |
|--------|------|------|----|
| patient001 | 张三 | 患者 | 1 |
| patient002 | 李四 | 患者 | 2 |
| patient003 | 王五 | 患者 | 3 |
| pharmacist001 | 李药师 | 药店药师 | 4 |
| auditor001 | 王审方师 | 远程审方师 | 5 |

## 许可证

MIT License
