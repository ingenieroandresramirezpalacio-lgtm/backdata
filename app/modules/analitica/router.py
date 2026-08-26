"""
Rutas HTTP del modulo Analitica: /api/v1/analitica/...

Toda esta seccion es exclusiva del Administrador / Analista.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.modules.analitica import exportacion, service
from app.modules.analitica.schemas import (
    FilaBache,
    FiltrosAnalisis,
    IndicadoresCategoriaSalida,
    IndicadoresSalida,
)
from app.modules.identidad.dependencias import requiere_roles
from app.modules.identidad.models import RolCodigo, Usuario

BD = Annotated[Session, Depends(get_db)]
SoloAdmin = Annotated[Usuario, Depends(requiere_roles(RolCodigo.ADMIN))]

router = APIRouter(prefix="/analitica", tags=["Análisis"])


def filtros_desde_query(
    fecha_desde: Annotated[str | None, Query()] = None,
    fecha_hasta: Annotated[str | None, Query()] = None,
    turno_id: int | None = None,
    horno_id: int | None = None,
    producto_id: int | None = None,
    categoria_id: int | None = None,
    supervisor_id: int | None = None,
    sabor_id: int | None = None,
) -> FiltrosAnalisis:
    """
    Convierte los parametros de la URL en un objeto de filtros. Las fechas
    llegan como texto para poder aceptar vacio ("") desde el formulario.
    """
    return FiltrosAnalisis(
        fecha_desde=fecha_desde or None,
        fecha_hasta=fecha_hasta or None,
        turno_id=turno_id,
        horno_id=horno_id,
        producto_id=producto_id,
        categoria_id=categoria_id,
        supervisor_id=supervisor_id,
        sabor_id=sabor_id,
    )


Filtros = Annotated[FiltrosAnalisis, Depends(filtros_desde_query)]


@router.get("/indicadores", response_model=IndicadoresSalida)
def indicadores(db: BD, _: SoloAdmin, filtros: Filtros):
    return service.calcular_indicadores(db, filtros)


@router.get("/por-categoria", response_model=list[IndicadoresCategoriaSalida])
def por_categoria(db: BD, _: SoloAdmin, filtros: Filtros):
    return service.calcular_indicadores_por_categoria(db, filtros)


@router.get("/baches", response_model=list[FilaBache])
def baches(db: BD, _: SoloAdmin, filtros: Filtros):
    return service.obtener_detalle_baches(db, filtros)


@router.get("/exportar.csv")
def exportar_csv(db: BD, _: SoloAdmin, filtros: Filtros) -> Response:
    contenido = exportacion.generar_csv(exportacion.obtener_filas(db, filtros))
    return Response(
        content=contenido,
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="{exportacion.nombre_archivo("csv")}"'
        },
    )


@router.get("/exportar.xlsx")
def exportar_excel(db: BD, _: SoloAdmin, filtros: Filtros) -> Response:
    contenido = exportacion.generar_excel(exportacion.obtener_filas(db, filtros))
    return Response(
        content=contenido,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="{exportacion.nombre_archivo("xlsx")}"'
        },
    )
