from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession

from auth import verificar_token
from CriarTabela import usuario as UsuarioModel
from database import get_db


def agora() -> datetime:
    """Data/hora atual em UTC (sem fuso), para os campos TIMESTAMP."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_perfil_atual(
    token: dict = Depends(verificar_token),
    db: DBSession = Depends(get_db),
):
    """Perfil (linha da tabela usuario) do usuário logado no Firebase.

    O perfil é criado junto com a conta, em POST /usuarios (auth.py).
    """
    perfil = db.scalar(
        select(UsuarioModel).where(UsuarioModel.firebase_uid == token["uid"])
    )
    if perfil is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Perfil não encontrado para esta conta",
        )
    return perfil
