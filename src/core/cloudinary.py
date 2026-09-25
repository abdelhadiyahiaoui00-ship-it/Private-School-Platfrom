import asyncio
import cloudinary
import cloudinary.uploader
import cloudinary.exceptions
from .config import settings
from fastapi import UploadFile

cloudinary.config(
    cloud_name = settings.CLOUDINARY_CLOUD_NAME,
    api_key = settings.CLOUDINARY_API_KEY,
    api_secret = settings.CLOUDINARY_API_SECRET,
    secure = True
)

async def upload_image(file: UploadFile) -> str:
    """
    Upload an image to Cloudinary and automatically convert it to .webp format.
    """
    try:
        result = cloudinary.uploader.upload(
            file.file,               # file-like object
            folder="products",
            format="webp",           # Convert automatically to .webp
            transformation=[{"quality": "auto"}]
        )
        return result["secure_url"]
    except Exception as e:
        raise Exception(f"Image upload failed: {e}")

async def delete_media(public_id: str, resource_type: str = "image") -> dict:
    """
    Delete media from Cloudinary by public_id and resource_type using server credentials.
    Treats non-existent / 404 / already-deleted assets as success (idempotent).
    """
    try:
        res = await asyncio.to_thread(
            cloudinary.uploader.destroy,
            public_id,
            resource_type=resource_type,
            invalidate=True,
        )
        return res
    except cloudinary.exceptions.NotFound:
        return {"result": "not_found"}
    except Exception as exc:
        err_str = str(exc).lower()
        if "not found" in err_str or "404" in err_str:
            return {"result": "not_found"}
        raise exc