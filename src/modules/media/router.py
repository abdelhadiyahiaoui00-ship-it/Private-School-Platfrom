from enum import Enum
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from src.core.cloudinary import delete_media
from src.modules.auth.dependencies import CurrentUser


class MediaResourceType(str, Enum):
    image = "image"
    video = "video"
    raw = "raw"


class DeleteMediaRequest(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)

    public_id: str = Field(..., alias="publicId")
    resource_type: MediaResourceType = Field(MediaResourceType.image, alias="resourceType")


router = APIRouter(prefix="/media", tags=["Media"])


@router.delete("", summary="Delete media asset from Cloudinary")
async def delete_media_asset(
    body: DeleteMediaRequest,
    actor: CurrentUser,
):
    try:
        res = await delete_media(public_id=body.public_id, resource_type=body.resource_type.value)
        return {
            "data": {
                "deleted": True,
                "publicId": body.public_id,
                "result": res.get("result", "ok") if isinstance(res, dict) else "ok",
            }
        }
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete media asset: {str(exc)}",
        )
