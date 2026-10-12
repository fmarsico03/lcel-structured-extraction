from enum import Enum
from typing import Literal, Optional
from pydantic import BaseModel, Field, SecretStr


class Criticidad(str, Enum):
    BAJA = "baja"
    MEDIA = "media"
    ALTA = "alta"

class ExtraccionTecnica(BaseModel):
    tecnologias: list[str] = Field(
        min_length=1,
        description="Tecnologías, frameworks, lenguajes o servicios mencionados explícitamente en el texto.",
    )
    nivel_de_criticidad: Criticidad = Field(
        description="Criticidad del problema o situación descrita: baja, media o alta.",
    )
    resumen_tecnico: str = Field(
        min_length=20,
        max_length=256,
        description="Resumen técnico breve (1-2 oraciones) del contenido del texto.",
    )

class Provider(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    NVIDIA = "nvidia"

class LLMConfig(BaseModel):
    provider: Provider
    model: str
    api_key: Optional[SecretStr] = None
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=1024, gt=0)