import cloudinary
import cloudinary.uploader
from .config import get_settings
from fastapi import UploadFile

settings = get_settings()

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