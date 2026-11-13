from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import Session as DBSession

import schemas
from CriarTabela import jogo as JogoModel
from CriarTabela import review as ReviewModel
from CriarTabela import usuario as UsuarioModel
from comum import agora, get_perfil_atual
from database import get_db

router = APIRouter(tags=["Reviews"])


# ---------- helpers ----------
def _consulta_reviews():
    """SELECT de reviews já com username do autor e nome do jogo."""
    return (
        select(
            ReviewModel,
            UsuarioModel.username,
            JogoModel.nome,
            JogoModel.capa_url,
        )
        .join(UsuarioModel, UsuarioModel.id_usuario == ReviewModel.id_usuario)
        .join(JogoModel, JogoModel.id_jogo == ReviewModel.id_jogo)
    )


def _review_dict(
    r: ReviewModel,
    username: str,
    jogo_nome: str,
    capa_url: str | None,
) -> dict:
    return {
        "id_avaliacao": r.id_avaliacao,
        "id_usuario": r.id_usuario,
        "username": username,
        "id_jogo": r.id_jogo,
        "jogo_nome": jogo_nome,
        "capa_url": capa_url,
        "nota": float(r.nota),
        "texto": r.texto,
        "data_criacao": r.data_criacao,
        "data_atualizacao": r.data_atualizacao,
    }


def _listar(db: DBSession, stmt, limit: int, offset: int) -> list[dict]:
    stmt = stmt.order_by(desc(ReviewModel.data_criacao), desc(ReviewModel.id_avaliacao))
    linhas = db.execute(stmt.limit(limit).offset(offset)).all()
    return [_review_dict(*linha) for linha in linhas]


def _obter_review_dict(db: DBSession, id_avaliacao: int) -> dict:
    linha = db.execute(
        _consulta_reviews().where(ReviewModel.id_avaliacao == id_avaliacao)
    ).first()
    if linha is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review não encontrada"
        )
    return _review_dict(*linha)


def _review_do_dono(db: DBSession, id_avaliacao: int, perfil: UsuarioModel) -> ReviewModel:
    review_db = db.get(ReviewModel, id_avaliacao)
    if review_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Review não encontrada"
        )
    if review_db.id_usuario != perfil.id_usuario:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você só pode alterar as suas próprias reviews",
        )
    return review_db


# ---------- criar ----------
@router.post(
    "/jogos/{id_jogo}/reviews",
    response_model=schemas.ReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_review(
    id_jogo: int,
    dados: schemas.ReviewCriar,
    perfil: UsuarioModel = Depends(get_perfil_atual),
    db: DBSession = Depends(get_db),
):
    """Cada usuário pode ter uma review por jogo (para mudar, use PUT /reviews/{id})."""
    if db.get(JogoModel, id_jogo) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jogo não encontrado"
        )

    ja_avaliou = db.scalar(
        select(ReviewModel.id_avaliacao).where(
            ReviewModel.id_usuario == perfil.id_usuario,
            ReviewModel.id_jogo == id_jogo,
        )
    )
    if ja_avaliou is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Você já avaliou este jogo (review {ja_avaliou})",
        )

    nova = ReviewModel(
        id_usuario=perfil.id_usuario,
        id_jogo=id_jogo,
        nota=dados.nota,
        texto=dados.texto,
        data_criacao=agora(),
    )
    db.add(nova)
    db.commit()
    db.refresh(nova)
    return _obter_review_dict(db, nova.id_avaliacao)


# ---------- consultar (público) ----------
@router.get("/jogos/{id_jogo}/reviews", response_model=list[schemas.ReviewResponse])
def listar_reviews_do_jogo(
    id_jogo: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    if db.get(JogoModel, id_jogo) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jogo não encontrado"
        )
    stmt = _consulta_reviews().where(ReviewModel.id_jogo == id_jogo)
    return _listar(db, stmt, limit, offset)


@router.get("/usuarios/{id_usuario}/reviews", response_model=list[schemas.ReviewResponse])
def listar_reviews_do_usuario(
    id_usuario: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    if db.get(UsuarioModel, id_usuario) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Usuário não encontrado"
        )
    stmt = _consulta_reviews().where(ReviewModel.id_usuario == id_usuario)
    return _listar(db, stmt, limit, offset)


@router.get("/reviews/{id_avaliacao}", response_model=schemas.ReviewResponse)
def buscar_review(id_avaliacao: int, db: DBSession = Depends(get_db)):
    return _obter_review_dict(db, id_avaliacao)


# ---------- feed ----------
@router.get("/feed", response_model=list[schemas.ReviewResponse])
def feed(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    perfil: UsuarioModel = Depends(get_perfil_atual),
    db: DBSession = Depends(get_db),
):
    """Retorna todas as reviews, das mais recentes às mais antigas."""
    stmt = _consulta_reviews()
    return _listar(db, stmt, limit, offset)


# ---------- alterar / excluir (só o dono) ----------
@router.put("/reviews/{id_avaliacao}", response_model=schemas.ReviewResponse)
def atualizar_review(
    id_avaliacao: int,
    dados: schemas.ReviewAtualizar,
    perfil: UsuarioModel = Depends(get_perfil_atual),
    db: DBSession = Depends(get_db),
):
    """Atualiza só os campos enviados (nota e/ou texto)."""
    review_db = _review_do_dono(db, id_avaliacao, perfil)

    campos = dados.model_dump(exclude_unset=True)
    if "nota" in campos and campos["nota"] is None:
        campos.pop("nota")  # nota é obrigatória: ignora null
    for campo, valor in campos.items():
        setattr(review_db, campo, valor)
    review_db.data_atualizacao = agora()
    db.commit()
    return _obter_review_dict(db, id_avaliacao)


@router.delete("/reviews/{id_avaliacao}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_review(
    id_avaliacao: int,
    perfil: UsuarioModel = Depends(get_perfil_atual),
    db: DBSession = Depends(get_db),
):
    review_db = _review_do_dono(db, id_avaliacao, perfil)
    db.delete(review_db)
    db.commit()
