from pydantic import BaseModel, Field, ConfigDict, field_validator

class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=8, max_length=128)
    first_name: str
    last_name: str | None = None

    @field_validator("username")
    @classmethod
    def normalize_username(cls, value: str) -> str:
        value = value.strip().lower()

        if not value:
            raise ValueError("Username cannot be empty")

        return value


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    user_id: int
    username: str
    first_name: str
    last_name: str | None = None
    model_config = ConfigDict(from_attributes=True)


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
