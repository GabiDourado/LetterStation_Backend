from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DBSession

import schemas
from CriarTabela import review as ReviewModel
from CriarTabela import usuario as UsuarioModel
from CriarTabela import usuario_seguidores as SeguidorModel
from comum import get_perfil_atual
from database import get_db

# O perfil é criado junto com a conta em POST /usuarios (auth.py).
# Aqui ficam consulta, edição e exclusão do perfil, e os seguidores.
router = APIRouter(prefix="/usuarios", tags=["Usuários"])


# ---------- helpers ----------
def _contar(db: DBSession, tabela, condicao) -> int:
    return db.scalar(select(func.count()).select_from(tabela).where(condicao)) or 0


def _perfil_dict(db: DBSession, u: UsuarioModel, privado: bool = False) -> dict:
    dados = {
        "id_usuario": u.id_usuario,
        "username": u.username,
        "avatar_url": u.avatar_url,
        "biografia": u.biografia,
        "data_cadastro": u.data_cadastro,
        "total_seguidores": _contar(db, SeguidorModel, SeguidorModel.id_seguido == u.id_usuario),
        "total_seguindo": _contar(db, SeguidorModel, SeguidorModel.id_usuario == u.id_usuario),
        "total_reviews": _contar(db, ReviewModel, ReviewModel.id_usuario == u.id_usuario),
    }
    if privado:
        dados["email"] = u.email
    return dados


def _obter_usuario(db: DBSession, id_usuario: int) -> UsuarioModel:
    u = db.get(UsuarioModel, id_usuario)
    if u is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado"
        )
    return u


def _username_em_uso(db: DBSession, username: str) -> bool:
    """Mesma regra do cadastro (auth.py): sem diferenciar maiúsculas de minúsculas."""
    return db.scalar(
        select(UsuarioModel.id_usuario).where(
            func.lower(UsuarioModel.username) == username.lower()
        )
    ) is not None


# ---------- meu perfil (usuário logado) ----------
@router.get("/me", response_model=schemas.UsuarioPrivado)
def ver_meu_perfil(
    perfil: UsuarioModel = Depends(get_perfil_atual), db: DBSession = Depends(get_db)
):
    return _perfil_dict(db, perfil, privado=True)


@router.put("/me", response_model=schemas.UsuarioPrivado)
def atualizar_meu_perfil(
    dados: schemas.PerfilAtualizar,
    perfil: UsuarioModel = Depends(get_perfil_atual),
    db: DBSession = Depends(get_db),
):
    """Atualiza só os campos enviados (username, biografia, avatar_url)."""
    campos = dados.model_dump(exclude_unset=True)

    if "username" in campos:
        if campos["username"] is None:
            campos.pop("username")  # username é obrigatório: ignora null
        else:
            campos["username"] = campos["username"].lower()  # igual ao cadastro
            if campos["username"] != perfil.username and _username_em_uso(
                db, campos["username"]
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Nome de usuário já está em uso",
                )

    for campo, valor in campos.items():
        setattr(perfil, campo, valor)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Nome de usuário já está em uso",
        )
    db.refresh(perfil)
    return _perfil_dict(db, perfil, privado=True)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def excluir_meu_perfil(
    perfil: UsuarioModel = Depends(get_perfil_atual), db: DBSession = Depends(get_db)
):
    """Apaga o perfil, as reviews e os vínculos de seguidor. (A conta do Firebase não é apagada.)"""
    db.execute(delete(ReviewModel).where(ReviewModel.id_usuario == perfil.id_usuario))
    db.execute(
        delete(SeguidorModel).where(
            or_(
                SeguidorModel.id_usuario == perfil.id_usuario,
                SeguidorModel.id_seguido == perfil.id_usuario,
            )
        )
    )
    db.delete(perfil)
    db.commit()


# ---------- consulta de usuários (público) ----------
@router.get("", response_model=list[schemas.UsuarioResumo])
def listar_usuarios(
    busca: Optional[str] = Query(None, min_length=1, description="Parte do username"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    stmt = select(UsuarioModel)
    if busca:
        stmt = stmt.where(UsuarioModel.username.icontains(busca, autoescape=True))
    stmt = stmt.order_by(UsuarioModel.username).limit(limit).offset(offset)
    return db.scalars(stmt).all()


@router.get("/{id_usuario}", response_model=schemas.UsuarioPublico)
def buscar_usuario(id_usuario: int, db: DBSession = Depends(get_db)):
    return _perfil_dict(db, _obter_usuario(db, id_usuario))


# ---------- seguidores ----------
@router.get("/{id_usuario}/seguidores", response_model=list[schemas.UsuarioResumo])
def listar_seguidores(
    id_usuario: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    """Quem segue este usuário."""
    _obter_usuario(db, id_usuario)
    stmt = (
        select(UsuarioModel)
        .join(SeguidorModel, SeguidorModel.id_usuario == UsuarioModel.id_usuario)
        .where(SeguidorModel.id_seguido == id_usuario)
        .order_by(UsuarioModel.username)
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()


@router.get("/{id_usuario}/seguindo", response_model=list[schemas.UsuarioResumo])
def listar_seguindo(
    id_usuario: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    """Quem este usuário segue."""
    _obter_usuario(db, id_usuario)
    stmt = (
        select(UsuarioModel)
        .join(SeguidorModel, SeguidorModel.id_seguido == UsuarioModel.id_usuario)
        .where(SeguidorModel.id_usuario == id_usuario)
        .order_by(UsuarioModel.username)
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()


@router.post(
    "/{id_seguido}/seguir",
    response_model=schemas.SeguirResponse,
    status_code=status.HTTP_201_CREATED,
)
def seguir_usuario(
    id_seguido: int,
    perfil: UsuarioModel = Depends(get_perfil_atual),
    db: DBSession = Depends(get_db),
):
    if id_seguido == perfil.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você não pode seguir a si mesmo",
        )
    _obter_usuario(db, id_seguido)

    ja_segue = db.scalar(
        select(SeguidorModel.usu_seg_id).where(
            SeguidorModel.id_usuario == perfil.id_usuario,
            SeguidorModel.id_seguido == id_seguido,
        )
    )
    if ja_segue is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Você já segue este usuário"
        )

    db.add(SeguidorModel(id_usuario=perfil.id_usuario, id_seguido=id_seguido))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Você já segue este usuário"
        )
    return {"id_usuario": perfil.id_usuario, "id_seguido": id_seguido}


@router.delete("/{id_seguido}/seguir", status_code=status.HTTP_204_NO_CONTENT)
def deixar_de_seguir(
    id_seguido: int,
    perfil: UsuarioModel = Depends(get_perfil_atual),
    db: DBSession = Depends(get_db),
):
    vinculo = db.scalar(
        select(SeguidorModel).where(
            SeguidorModel.id_usuario == perfil.id_usuario,
            SeguidorModel.id_seguido == id_seguido,
        )
    )
    if vinculo is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Você não segue este usuário"
        )
    db.delete(vinculo)
    db.commit()
