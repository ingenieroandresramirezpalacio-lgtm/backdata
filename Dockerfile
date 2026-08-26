# DATACONTROL - imagen del backend (API)
#
# Dos etapas:
#   "produccion"   lo que corre en la fabrica: solo las dependencias necesarias.
#   "desarrollo"   agrega pytest y ruff, para correr pruebas y revisar el codigo.
# Por defecto se construye "produccion" (es la ultima etapa del archivo).

FROM python:3.12-slim AS base

# Buenas practicas de Python dentro de contenedores:
#   PYTHONDONTWRITEBYTECODE: no ensucia el volumen con archivos .pyc
#   PYTHONUNBUFFERED:        los logs salen al instante, sin quedarse en cache
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /code

# Las dependencias se copian primero y solas: mientras requirements.txt no
# cambie, Docker reutiliza esta capa y reconstruir tarda segundos.
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# La app no corre como root (si alguien lograra entrar al contenedor,
# tendria los permisos minimos).
RUN useradd --create-home --uid 1000 datacontrol

# --- Etapa de desarrollo: pruebas y linter -------------------------------
FROM base AS desarrollo

COPY requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY pyproject.toml ./
COPY app ./app
COPY tests ./tests
RUN chown -R datacontrol:datacontrol /code
USER datacontrol

CMD ["pytest"]

# --- Etapa de produccion --------------------------------------------------
FROM base AS produccion

COPY app ./app
RUN chown -R datacontrol:datacontrol /code
USER datacontrol

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
