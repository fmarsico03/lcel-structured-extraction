from enum import Enum
from pydantic import BaseModel, Field


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
