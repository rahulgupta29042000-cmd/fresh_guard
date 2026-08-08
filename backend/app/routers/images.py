from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import inspection_service, models, serializers
from ..database import get_db
from ..schemas import ImageUploadSampleRequest
from ..vision.storage import get_storage

router = APIRouter(prefix="/api/images", tags=["images"])


@router.post("/upload")
async def upload_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    try:
        file_bytes = await file.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to upload image. Try again.")
    if not file_bytes:
        raise HTTPException(status_code=400, detail="Unable to upload image. Try again.")

    image = inspection_service.save_uploaded_image(db, file_bytes, file.content_type or "image/jpeg")
    return serializers.image_to_out(image)


@router.post("/upload-sample")
def upload_sample_image(payload: ImageUploadSampleRequest, db: Session = Depends(get_db)):
    """Convenience endpoint for the demo/simulation mode — 'captures' one of
    the bundled sample product photos instead of requiring a real camera."""
    image = inspection_service.save_sample_image(db, payload.sample_key)
    return serializers.image_to_out(image)


@router.get("/samples")
def list_sample_images():
    return inspection_service.list_samples()


@router.get("/{image_id}/file")
def get_image_file(image_id: int, db: Session = Depends(get_db)):
    from fastapi.responses import Response

    image = db.get(models.InspectionImage, image_id)
    if not image:
        raise HTTPException(status_code=404, detail=f"Image {image_id} not found")
    data = get_storage().read(image.file_path)
    return Response(content=data, media_type=image.content_type or "image/jpeg")
