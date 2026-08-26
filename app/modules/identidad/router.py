"""
Rutas HTTP del modulo Identidad:
  /api/v1/auth/...      inicio de sesion y datos del usuario conectado
  /api/v1/usuarios/...  administracion de usuarios (solo Administrador)
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.seguridad import crear_token_acceso
from app.db.session import get_db
from app.modules.identidad import service
from app.modules.identidad.dependencias import UsuarioAutenticado, requiere_roles
from app.modules.identidad.models import RolCodigo, Usuario
from app.modules.identidad.schemas import (
    CambiarPasswordPeticion,
    LoginPeticion,
    RolSalida,
    TokenSalida,
    UsuarioActualizar,
    UsuarioCrear,
    UsuarioSalida,
)

BD = Annotated[Session, Depends(get_db)]
SoloAdmin = Annotated[Usuario, Depends(requiere_roles(RolCodigo.ADMIN))]

router_auth = APIRouter(prefix="/auth", tags=["Autenticación"])
router_usuarios = APIRouter(prefix="/usuarios", tags=["Usuarios"])


# --- Autenticacion ---------------------------------------------------------


@router_auth.post("/login", response_model=TokenSalida)
def iniciar_sesion(datos: LoginPeticion, db: BD) -> TokenSalida:
    usuario = service.autenticar(db, datos.nombre_usuario.strip().lower(), datos.password)
    token, segundos = crear_token_acceso(usuario.id, usuario.rol.codigo)
    return TokenSalida(
        access_token=token,
        expira_en_segundos=segundos,
        usuario=UsuarioSalida.model_validate(usuario),
    )


@router_auth.get("/yo", response_model=UsuarioSalida)
def usuario_conectado(usuario: UsuarioAutenticado) -> Usuario:
    """Con quien esta trabajando la app ahora mismo (lo usa el frontend al abrir)."""
    return usuario


@router_auth.post("/cambiar-password", status_code=status.HTTP_204_NO_CONTENT)
def cambiar_password(datos: CambiarPasswordPeticion, usuario: UsuarioAutenticado, db: BD) -> None:
    service.cambiar_password_propia(db, usuario, datos.password_actual, datos.password_nueva)


# --- Usuarios (solo Administrador) ----------------------------------------


@router_usuarios.get("", response_model=list[UsuarioSalida])
def listar(db: BD, _: SoloAdmin) -> list[Usuario]:
    return service.listar_usuarios(db)


@router_usuarios.get("/roles", response_model=list[RolSalida])
def listar_roles(db: BD, _: SoloAdmin) -> list:
    return service.listar_roles(db)


@router_usuarios.get("/supervisores", response_model=list[UsuarioSalida])
def listar_supervisores(db: BD, _: SoloAdmin) -> list[Usuario]:
    """Para el filtro por supervisor de la pantalla de Análisis."""
    return service.listar_supervisores(db)


@router_usuarios.post("", response_model=UsuarioSalida, status_code=status.HTTP_201_CREATED)
def crear(datos: UsuarioCrear, db: BD, _: SoloAdmin) -> Usuario:
    return service.crear_usuario(db, datos)


@router_usuarios.get("/{usuario_id}", response_model=UsuarioSalida)
def detalle(usuario_id: int, db: BD, _: SoloAdmin) -> Usuario:
    return service.obtener_usuario(db, usuario_id)


@router_usuarios.put("/{usuario_id}", response_model=UsuarioSalida)
def actualizar(usuario_id: int, datos: UsuarioActualizar, db: BD, _: SoloAdmin) -> Usuario:
    return service.actualizar_usuario(db, usuario_id, datos)


@router_usuarios.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar(usuario_id: int, db: BD, admin: SoloAdmin) -> None:
    service.eliminar_usuario(db, usuario_id, admin)
