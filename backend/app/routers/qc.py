from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import inspection_service, serializers
from ..database import get_db

router = APIRouter(prefix="/api/qc", tags=["qc"])


@router.get("/review-queue")
def review_queue(db: Session = Depends(get_db)):
    inspections = inspection_service.get_review_queue(db)
    return {"count": len(inspections), "items": [serializers.inspection_to_out(i) for i in inspections]}
