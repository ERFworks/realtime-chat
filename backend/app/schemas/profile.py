from pydantic import BaseModel, Field, ConfigDict

class ProfileUpdate(BaseModel):
    biography: str | None = Field(default=None, max_length=500)


class ProfileOut(BaseModel):
    profile_id: int
    user_id: int
    biography: str | None = None
    profile_pic: str | None = None
    model_config = ConfigDict(from_attributes=True)
    