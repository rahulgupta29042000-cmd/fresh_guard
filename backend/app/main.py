from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import models
from .database import Base, engine
from .routers import dashboard, delivery, feedback, orders, packing, picking, reference

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Fresh_Guard API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(reference.router)
app.include_router(orders.router)
app.include_router(picking.router)
app.include_router(packing.router)
app.include_router(delivery.router)
app.include_router(feedback.router)
app.include_router(dashboard.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "fresh-guard-api"}
