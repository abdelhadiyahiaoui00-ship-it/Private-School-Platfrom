from pydantic import BaseModel, ConfigDict


class BaseSchema(BaseModel):
    pass


class BaseResponseSchema(BaseSchema):
    model_config = ConfigDict(from_attributes=True)


class BaseCreateSchema(BaseSchema):
    pass


class BaseUpdateSchema(BaseSchema):
    pass
