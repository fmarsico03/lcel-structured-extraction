"""Script de pruebas: corre la cadena contra textos de ejemplo y muestra los resultados.

Uso:
    python run_tests.py                 # corre todos los casos de ejemplo
    python run_tests.py "texto libre"   # procesa un texto puntual
"""
import asyncio
import logging
import sys
import time

from chain import process_text
from schemas import Criticidad

CASOS = [
    {
        "nombre": "Caída de servicio",
        "texto": (
            "2026-10-12 03:14:07 ERROR [payment-service] FATAL: could not connect to PostgreSQL "
            "at db-prod:5432 - connection refused. Kubernetes reinició el pod 12 veces "
            "(CrashLoopBackOff). Los usuarios no pueden completar pagos desde hace 40 minutos."
        ),
        "esperado": Criticidad.ALTA,
    },
    {
        "nombre": "Degradación de rendimiento",
        "texto": (
            "WARN [api-gateway] Latencia p95 subió de 120ms a 2.3s. Redis reporta evictions "
            "frecuentes por falta de memoria y la API en FastAPI está haciendo fallback a "
            "consultas directas a MongoDB. Las requests se completan pero lentamente."
        ),
        "esperado": Criticidad.MEDIA,
    },
    {
        "nombre": "Descripción de arquitectura",
        "texto": (
            "El frontend está hecho en React con TypeScript y se despliega en Vercel. "
            "El backend es una API REST en Django que corre en AWS ECS y usa RabbitMQ "
            "para procesar tareas en segundo plano con Celery."
        ),
        "esperado": Criticidad.BAJA,
    },
    {
        "nombre": "Incidente de seguridad",
        "texto": (
            "Se detectó que el bucket de Amazon S3 con backups de MySQL quedó público por un "
            "cambio en Terraform. Hay accesos desde IPs desconocidas en los logs de CloudTrail."
        ),
        "esperado": Criticidad.ALTA,
    },
    {
        "nombre": "Texto ambiguo",
        "texto": (
            "ayer anduvo raro el sistema, algunos dicen que lento y otros que no les cargaba, "
            "después se arregló solo. capaz fue la base o el servidor, no sé. revisar?"
        ),
        "esperado": None,
    },
]


def _imprimir(resultado) -> None:
    print(f"  tecnologias:         {', '.join(resultado.tecnologias)}")
    print(f"  nivel_de_criticidad: {resultado.nivel_de_criticidad.value}")
    print(f"  resumen_tecnico:     {resultado.resumen_tecnico}")


async def correr_casos() -> int:
    aprobados = 0
    for i, caso in enumerate(CASOS, start=1):
        print(f"\n[{i}/{len(CASOS)}] {caso['nombre']}")
        inicio = time.perf_counter()
        try:
            resultado = await process_text(caso["texto"])
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
            continue
        duracion = time.perf_counter() - inicio

        _imprimir(resultado)
        esperado = caso["esperado"]
        ok = esperado is None or resultado.nivel_de_criticidad == esperado
        aprobados += ok
        estado = "OK" if ok else f"FALLA (esperado: {esperado.value})"
        print(f"  -> {estado} ({duracion:.1f}s)")

    print(f"\nResultado: {aprobados}/{len(CASOS)} casos OK")
    return 0 if aprobados == len(CASOS) else 1


async def correr_texto(texto: str) -> int:
    resultado = await process_text(texto)
    _imprimir(resultado)
    return 0


def main() -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    if len(sys.argv) > 1:
        return asyncio.run(correr_texto(" ".join(sys.argv[1:])))
    return asyncio.run(correr_casos())


if __name__ == "__main__":
    sys.exit(main())
