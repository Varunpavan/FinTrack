from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserSignup(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserProfileUpdate(BaseModel):
    name: str
    email: EmailStr


class UserPasswordChange(BaseModel):
    currentPassword: str
    newPassword: str


class UserResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    mongo_id: str = Field(serialization_alias="_id")
    name: str
    email: str

    @classmethod
    def from_model(cls, user):
        user_id_str = str(user.id)
        return cls(
            id=user_id_str,
            mongo_id=user_id_str,
            name=user.name,
            email=user.email
        )


class AuthResponse(BaseModel):
    success: bool = True
    message: str
    token: str
    user: UserResponse


class GenericResponse(BaseModel):
    success: bool = True
    message: str
