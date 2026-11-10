from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Float, cast, func, select
from sqlalchemy.orm import Session as DBSession

import LetterStation_Backend.schemas as schemas
from CriarTabela import jogo as JogoModel
from CriarTabela import review as ReviewModel
from LetterStation_Backend.comum import agora
from database import get_db
from auth import verificar_token

router = APIRouter(prefix="/jogos", tags=["Jogos"])


# ---------- helpers ----------
def _consulta_jogos():
    """SELECT de jogos já com nota média e total de reviews."""
    agregado = (
        select(
            ReviewModel.id_jogo.label("id_jogo"),
            func.avg(cast(ReviewModel.nota, Float)).label("media"),
            func.count(ReviewModel.id_avaliacao).label("total"),
        )
        .group_by(ReviewModel.id_jogo)
        .subquery()
    )
    stmt = select(JogoModel, agregado.c.media, agregado.c.total).outerjoin(
        agregado, agregado.c.id_jogo == JogoModel.id_jogo
    )
    return stmt, agregado


def _jogo_dict(j: JogoModel, media, total) -> dict:
    return {
        "id_jogo": j.id_jogo,
        "id_externo": j.id_externo,
        "nome": j.nome,
        "descricao": j.descricao,
        "data_lancamento": j.data_lancamento,
        "capa_url": j.capa_url,
        "desenvolvedor": j.desenvolvedor,
        "data_atualizacao": j.data_atualizacao,
        "nota_media": round(media, 2) if media is not None else None,
        "total_reviews": total or 0,
    }


def _obter_jogo_dict(db: DBSession, id_jogo: int) -> dict:
    stmt, _ = _consulta_jogos()
    linha = db.execute(stmt.where(JogoModel.id_jogo == id_jogo)).first()
    if linha is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jogo não encontrado"
        )
    return _jogo_dict(*linha)


def _id_externo_em_uso(db: DBSession, id_externo: str) -> bool:
    return db.scalar(
        select(JogoModel.id_jogo).where(JogoModel.id_externo == id_externo)
    ) is not None


# ---------- rotas ----------
@router.get("", response_model=list[schemas.JogoResponse])
def listar_jogos(
    busca: Optional[str] = Query(None, min_length=1, description="Parte do nome do jogo"),
    id_externo: Optional[str] = Query(None, description="Id do jogo na API externa (FreeToGame)"),
    ordenar: Literal["nome", "lancamento", "nota"] = "nome",
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: DBSession = Depends(get_db),
):
    stmt, agregado = _consulta_jogos()
    if busca:
        stmt = stmt.where(JogoModel.nome.icontains(busca, autoescape=True))
    if id_externo:
        stmt = stmt.where(JogoModel.id_externo == id_externo)

    if ordenar == "nome":
        stmt = stmt.order_by(JogoModel.nome)
    elif ordenar == "lancamento":
        stmt = stmt.order_by(JogoModel.data_lancamento.desc().nulls_last(), JogoModel.nome)
    else:  # nota
        stmt = stmt.order_by(agregado.c.media.desc().nulls_last(), JogoModel.nome)

    linhas = db.execute(stmt.limit(limit).offset(offset)).all()
    return [_jogo_dict(*linha) for linha in linhas]


@router.get("/{id_jogo}", response_model=schemas.JogoResponse)
def buscar_jogo(id_jogo: int, db: DBSession = Depends(get_db)):
    return _obter_jogo_dict(db, id_jogo)


@router.post("", response_model=schemas.JogoResponse, status_code=status.HTTP_201_CREATED)
def cadastrar_jogo(
    dados: schemas.JogoCriar,
    token: dict = Depends(verificar_token),
    db: DBSession = Depends(get_db),
):
    if _id_externo_em_uso(db, dados.id_externo):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um jogo com este id_externo",
        )
    novo = JogoModel(**dados.model_dump(), data_atualizacao=agora())
    db.add(novo)
    db.commit()
    db.refresh(novo)
    return _jogo_dict(novo, None, 0)


@router.put("/{id_jogo}", response_model=schemas.JogoResponse)
def atualizar_jogo(
    id_jogo: int,
    dados: schemas.JogoAtualizar,
    token: dict = Depends(verificar_token),
    db: DBSession = Depends(get_db),
):
    """Atualiza só os campos enviados."""
    jogo_db = db.get(JogoModel, id_jogo)
    if jogo_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jogo não encontrado"
        )

    campos = dados.model_dump(exclude_unset=True)
    for obrigatorio in ("nome", "id_externo"):
        if obrigatorio in campos and campos[obrigatorio] is None:
            campos.pop(obrigatorio)  # colunas obrigatórias: ignora null

    novo_externo = campos.get("id_externo")
    if novo_externo and novo_externo != jogo_db.id_externo and _id_externo_em_uso(db, novo_externo):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Já existe um jogo com este id_externo",
        )

    for campo, valor in campos.items():
        setattr(jogo_db, campo, valor)
    jogo_db.data_atualizacao = agora()
    db.commit()
    return _obter_jogo_dict(db, id_jogo)


@router.delete("/{id_jogo}", status_code=status.HTTP_204_NO_CONTENT)
def excluir_jogo(
    id_jogo: int,
    token: dict = Depends(verificar_token),
    db: DBSession = Depends(get_db),
):
    jogo_db = db.get(JogoModel, id_jogo)
    if jogo_db is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Jogo não encontrado"
        )

    tem_reviews = db.scalar(
        select(ReviewModel.id_avaliacao).where(ReviewModel.id_jogo == id_jogo).limit(1)
    )
    if tem_reviews is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O jogo possui reviews e não pode ser excluído",
        )
    db.delete(jogo_db)
    db.commit()