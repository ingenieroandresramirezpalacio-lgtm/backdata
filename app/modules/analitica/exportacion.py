"""
Exportacion de datos a CSV y Excel.

Genera una fila por orden de produccion, con el numero de orden como
identificador (para poder cruzarla con otros analisis) y los mismos
totales que muestra la pantalla de Analisis, respetando sus filtros.
"""

import csv
import io
from datetime import datetime

from openpyxl import Workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.tiempo import ahora_local
from app.modules.analitica.schemas import FiltrosAnalisis
from app.modules.analitica.service import consulta_ordenes_filtradas
from app.modules.produccion.models import (
    Desperdicio,
    OrdenProduccion,
    RegistroHorno,
    RegistroSaborizado,
)

ENCABEZADOS = [
    "numero_orden",
    "fecha",
    "destino",
    "estado",
    "supervisor",
    "turno",
    "horno",
    "categoria",
    "producto",
    "cantidad_programada_kg",
    "kg_crudos",
    "cantidad_bultos",
    "kg_papa_frita",
    "kg_sabor_usado",
    "kg_desperdicio",
    "kg_aceite_consumido",
]


def obtener_filas(db: Session, filtros: FiltrosAnalisis) -> list[list]:
    ordenes_sub = consulta_ordenes_filtradas(filtros).subquery()

    ordenes = db.scalars(
        select(OrdenProduccion)
        .where(OrdenProduccion.id.in_(select(ordenes_sub.c.id)))
        .order_by(OrdenProduccion.fecha, OrdenProduccion.numero_orden)
    ).unique().all()

    filas: list[list] = [ENCABEZADOS]
    for orden in ordenes:
        kg_crudos, bultos, kg_aceite = db.execute(
            select(
                func.coalesce(func.sum(RegistroHorno.kg_crudos_calculados), 0),
                func.coalesce(func.sum(RegistroHorno.cantidad_bultos), 0),
                func.coalesce(func.sum(RegistroHorno.kg_aceite_consumido), 0),
            ).where(RegistroHorno.orden_id == orden.id, RegistroHorno.eliminado == False)
        ).one()

        kg_desperdicio = db.scalar(
            select(func.coalesce(func.sum(Desperdicio.cantidad_kg), 0))
            .join(RegistroHorno, Desperdicio.registro_horno_id == RegistroHorno.id)
            .where(RegistroHorno.orden_id == orden.id, RegistroHorno.eliminado == False)
        )

        kg_papa_frita, kg_sabor = db.execute(
            select(
                func.coalesce(func.sum(RegistroSaborizado.kg_recibidos), 0),
                func.coalesce(func.sum(RegistroSaborizado.cantidad_sabor_kg), 0),
            ).where(
                RegistroSaborizado.orden_id == orden.id, RegistroSaborizado.eliminado == False
            )
        ).one()

        filas.append(
            [
                orden.numero_orden,
                orden.fecha.isoformat(),
                orden.destino_etiqueta,
                orden.estado_etiqueta,
                orden.supervisor.nombre_completo,
                orden.turno.nombre,
                orden.horno.nombre,
                orden.categoria.nombre,
                orden.producto.nombre_comercial,
                float(orden.cantidad_programada),
                float(kg_crudos),
                float(bultos),
                float(kg_papa_frita),
                float(kg_sabor),
                float(kg_desperdicio or 0),
                float(kg_aceite),
            ]
        )
    return filas


def generar_csv(filas: list[list]) -> bytes:
    salida = io.StringIO()
    csv.writer(salida, delimiter=";").writerows(filas)
    # utf-8-sig (con BOM) para que Excel en Windows abra bien las tildes.
    return salida.getvalue().encode("utf-8-sig")


def generar_excel(filas: list[list]) -> bytes:
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Producción"
    for fila in filas:
        hoja.append(fila)

    # Ancho de columna aproximado al contenido, para que se lea sin ajustar.
    for indice, encabezado in enumerate(filas[0], start=1):
        largo = max((len(str(fila[indice - 1])) for fila in filas), default=len(encabezado))
        hoja.column_dimensions[hoja.cell(row=1, column=indice).column_letter].width = min(
            max(12, largo + 2), 40
        )

    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def nombre_archivo(extension: str, momento: datetime | None = None) -> str:
    momento = momento or ahora_local()
    return f"datacontrol_{momento:%Y%m%d_%H%M}.{extension}"
