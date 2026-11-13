from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    correo: str = Field(..., description="Correo institucional")
    password: str = Field(..., min_length=1)


class RegistroRequest(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=100)
    correo: str = Field(..., description="Correo institucional")
    password: str = Field(..., min_length=8)
