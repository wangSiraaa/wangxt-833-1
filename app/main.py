from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import prescription, pickup, audit_query
from app.seed_data import init_seed_data

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="药店处方流转审方API服务",
    description="处方上传、药品校验、远程审方、取药码生成、核销、稽核查询全流程",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(prescription.router)
app.include_router(pickup.router)
app.include_router(audit_query.router)


@app.on_event("startup")
def startup_event():
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        init_seed_data(db)
    finally:
        db.close()


@app.get("/", tags=["根路径"])
def root():
    return {
        "name": "药店处方流转审方API服务",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/health", tags=["健康检查"])
def health_check():
    return {"status": "healthy", "timestamp": "2026-06-07T00:00:00Z"}
