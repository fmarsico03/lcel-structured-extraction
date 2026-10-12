import logging
import os
from functools import lru_cache

from dotenv import load_dotenv
from langchain_core.exceptions import OutputParserException
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import ValidationError

from clients.langchain_factory import get_chat_model
from schemas import ExtraccionTecnica, LLMConfig

load_dotenv()

logger = logging.getLogger(__name__)

MAX_INTENTOS = 3

_MOTIVOS_TRUNCADO = {"length", "max_tokens", "MAX_TOKENS"}

PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "Sos un ingeniero de software senior especializado en análisis de sistemas. "
        "Tu tarea es extraer información técnica de textos como descripciones de arquitectura "
        "o logs de error.\n"
        "Reglas:\n"
        "- tecnologias: solo las tecnologías, frameworks, lenguajes o servicios mencionados "
        "explícitamente en el texto. No inventes ninguna.\n"
        "- nivel_de_criticidad: 'alta' si hay caída del servicio, pérdida de datos o problemas "
        "de seguridad; 'media' si hay degradación de rendimiento o errores recuperables; "
        "'baja' si es informativo o una descripción sin problemas.\n"
        "- resumen_tecnico: 1-2 oraciones, en español, describiendo el sistema y el problema principal.",
    ),
    ("human", "Analizá el siguiente texto:\n{text}"),
])


class RespuestaIncompletaError(Exception):
    """El modelo cortó la respuesta antes de terminar."""


def _validar_salida(output: dict) -> ExtraccionTecnica:
    """Revisa el finish_reason y el resultado del parseo antes de devolver el objeto validado.
    Si algo falla, lanza una excepción para que vuelva a intentar.
    """
    metadata = output["raw"].response_metadata
    motivo_fin = metadata.get("finish_reason") or metadata.get("stop_reason")

    if motivo_fin in _MOTIVOS_TRUNCADO:
        logger.warning("Respuesta truncada por falta de tokens (finish_reason=%s). Reintentando...", motivo_fin)
        raise RespuestaIncompletaError(f"Respuesta truncada (finish_reason={motivo_fin})")

    if output["parsing_error"] is not None:
        logger.warning("La salida no cumple el esquema: %s. Reintentando...", output["parsing_error"])
        raise output["parsing_error"]

    if output["parsed"] is None:
        logger.warning("El modelo no devolvió una salida estructurada. Reintentando...")
        raise OutputParserException("El modelo no devolvió una salida estructurada")

    logger.info("Validación con Pydantic OK")
    return output["parsed"]


def _config() -> LLMConfig:
    return LLMConfig(
        provider=os.environ["LLM_PROVIDER"],
        model=os.environ["LLM_MODEL"],
        api_key=os.environ["LLM_API_KEY"],
        temperature=float(os.getenv("LLM_TEMPERATURE", "0")),
        max_tokens=int(os.getenv("LLM_MAX_TOKENS", "1024")),
    )


@lru_cache(maxsize=1)
def build_chain() -> Runnable:
    """Arma la cadena LCEL: prompt | modelo con salida estructurada | validación, con reintentos."""
    config = _config()
    logger.info("Usando proveedor=%s modelo=%s", config.provider.value, config.model)

    model = get_chat_model(config)
    structured_model = model.with_structured_output(ExtraccionTecnica, include_raw=True)

    chain = PROMPT | structured_model | RunnableLambda(_validar_salida)

    return chain.with_retry(
        retry_if_exception_type=(OutputParserException, ValidationError, RespuestaIncompletaError),
        stop_after_attempt=MAX_INTENTOS,
        wait_exponential_jitter=True,
    )


async def process_text(text: str) -> ExtraccionTecnica:
    """Extrae entidades técnicas de un texto y devuelve un objeto validado."""
    logger.info("Procesando texto (%d caracteres)", len(text))
    try:
        resultado = await build_chain().ainvoke({"text": text})
    except (OutputParserException, ValidationError, RespuestaIncompletaError) as e:
        logger.error("No se pudo obtener una salida válida tras %d intentos: %s", MAX_INTENTOS, e)
        raise
    logger.info("Extracción completada: %s", resultado.model_dump_json())
    return resultado
