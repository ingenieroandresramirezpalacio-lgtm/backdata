"""
Punto de entrada de la API de DATACONTROL.

Esta capa hace solo tres cosas: configurar la aplicacion, enchufar los
routers de cada modulo y traducir errores. Toda la logica vive en
app/modules/<modulo>/service.py.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.manejadores import registrar_manejadores
from app.api.router import api_router
from app.core.config import settings
from app.db.bootstrap import crear_admin_inicial
from app.db.session import SessionLocal

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("datacontrol")


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI) -> AsyncIterator[None]:
    """Se ejecuta una vez al arrancar (y al apagar) el servidor."""
    db = SessionLocal()
    try:
        crear_admin_inicial(db)
    except Exception:  # noqa: BLE001 - arrancar igual: la API sirve sin admin
        logger.exception("No se pudo verificar el usuario administrador inicial")
    finally:
        db.close()

    logger.info("%s listo (entorno: %s)", settings.app_name, settings.app_env)
    yield


app = FastAPI(
    title=f"{settings.app_name} API",
    version="2.0.0",
    description=(
        "API de recolección de datos de producción de Productos Alimenticios Fritomix SAS: "
        "órdenes, registro de horno, saborizado, catálogos y análisis."
    ),
    lifespan=ciclo_de_vida,
    # La documentacion interactiva queda fuera en produccion.
    docs_url=None if settings.es_produccion else "/docs",
    redoc_url=None,
    openapi_url=None if settings.es_produccion else "/openapi.json",
)

# El frontend Angular corre en otro origen (otro puerto), asi que hay que
# autorizarlo explicitamente. La lista viene del .env.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origenes_cors,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    # Sin esto el navegador no deja leer el nombre del archivo exportado.
    expose_headers=["Content-Disposition"],
)

registrar_manejadores(app)
app.include_router(api_router)
