from app.schemas.common import StrictSchema


class HealthResponse(StrictSchema):
    status: str
