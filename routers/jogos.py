from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import Float, cast, func, select
from sqlalchemy.orm import Session as DBSession

import schemas
from CriarTabela import jogo as JogoModel
from CriarTabela import review as ReviewModel
from comum import agora
from database import get_db
from auth import verificar_token

from datetime import date

import requests

from sqlalchemy.exc import SQLAlchemyError

router = APIRouter(prefix="/jogos", tags=["Jogos"])

FREETOGAME_API_URL = "https://www.freetogame.com/api" #implementado
FREETOGAME_TIMEOUT = 10                               #implementado


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

@router.get("/catalogo")
def listar_catalogo_externo(
    categoria: Optional[str] = Query(default=None, alias="category"),
    plataforma: Optional[str] = Query(default=None, alias="platform"),
    ordenar_por: Optional[str] = Query(default=None, alias="sort-by"),
    db: DBSession = Depends(get_db),
):
    parametros = {
        chave: valor
        for chave, valor in {
            "category": categoria,
            "platform": plataforma,
            "sort-by": ordenar_por,
        }.items()
        if valor is not None
    }

    jogos = consultar_freetogame("games", parametros)

    if not isinstance(jogos, list):
        raise HTTPException(
            status_code=502,
            detail="A API retornou uma lista inválida",
        )

    sincronizar_jogos(jogos, db)

    return jogos

@router.get("/catalogo/{game_id}")
def obter_detalhes_catalogo(
    game_id: int,
    db: DBSession = Depends(get_db),
):
    jogo = consultar_freetogame(
        "game",
        {"id": game_id},
    )

    if not isinstance(jogo, dict):
        raise HTTPException(
            status_code=502,
            detail="A API retornou detalhes inválidos",
        )

    sincronizar_jogos([jogo], db)

    return jogo

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

#////////a partir daqui, as funções para inegrar a API exeterna com nossa API.///////////////
    
def consultar_freetogame(endpoint: str, parametros: dict): #FUNC implementada para consultar a API externa FreeToGame
    try:
        resposta = requests.get(
            f"{FREETOGAME_API_URL}/{endpoint}",
            params=parametros,
            timeout=FREETOGAME_TIMEOUT
        )

    except requests.RequestException as erro:
        raise HTTPException(
            status_code=502,
            detail="Não foi possível consultar o catálogo de jogos"
        ) from erro

    if resposta.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="Jogo não encontrado"
        )

    if not resposta.ok:
        raise HTTPException(
            status_code=502,
            detail="A API de jogos retornou um erro"
        )

    try:
        return resposta.json()

    except ValueError as erro:
        raise HTTPException(
            status_code=502,
            detail="A API de jogos retornou uma resposta inválida"
        ) from erro
        
def sincronizar_jogos(jogos: list[dict], db: DBSession): #FUNC implementada para sincronizar os dados dos jogos com o banco de dados
    try:
        for dados in jogos:

            if not isinstance(dados, dict):
                raise HTTPException(
                    status_code=502,
                    detail="Dados de jogo inválidos"
                )

            id_externo = dados.get("id")
            nome = dados.get("title")

            if id_externo is None or not nome:
                raise HTTPException(
                    status_code=502,
                    detail="Dados de jogo incompletos"
                )

            jogo = (
                db.query(JogoModel)
                .filter_by(id_externo=str(id_externo))
                .first()
            )

            if jogo is None:
                jogo = JogoModel(
                    id_externo=str(id_externo),
                    nome=nome
                )
                db.add(jogo)

            data_lancamento = dados.get("release_date")

            try:
                data_lancamento = (
                    date.fromisoformat(data_lancamento)
                    if data_lancamento else None
                )
            except (TypeError, ValueError) as erro:
                raise HTTPException(
                    status_code=502,
                    detail="Data de lançamento inválida"
                ) from erro

            jogo.nome = nome
            jogo.descricao = (
                dados.get("description")
                or dados.get("short_description")
            )
            jogo.data_lancamento = data_lancamento
            jogo.capa_url = dados.get("thumbnail")
            jogo.desenvolvedor = dados.get("developer")
            jogo.data_atualizacao = agora()

        db.commit()

    except SQLAlchemyError as erro:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erro ao atualizar o catálogo de jogos"
        ) from erro

    except HTTPException:
        db.rollback()
        raise
    
'''@app.get("/jogos") #FUNC implementada para listar os jogos, com filtros opcionais de categoria, plataforma e ordenação
def listar_jogos(
    categoria: Optional[str] = Query(default=None, alias="category"),
    plataforma: Optional[str] = Query(default=None, alias="platform"),
    ordenar_por: Optional[str] = Query(default=None, alias="sort-by"),
    sessao: ORMSession = Depends(obter_sessao)
):

    parametros = {
        chave: valor
        for chave, valor in {
            "category": categoria,
            "platform": plataforma,
            "sort-by": ordenar_por
        }.items()
        if valor is not None
    }

    jogos = consultar_freetogame("games", parametros)

    if not isinstance(jogos, list):
        raise HTTPException(
            status_code=502,
            detail="A API retornou uma lista inválida"
        )

    sincronizar_jogos(jogos, sessao)

    return jogos

@app.get("/jogos/{game_id}") #FUNC implementada para obter detalhes de um jogo específico, sincronizando com o banco de dados
def obter_jogo(
    game_id: int,
    sessao: ORMSession = Depends(obter_sessao)
):

    jogo = consultar_freetogame(
        "game",
        {"id": game_id}
    )

    if not isinstance(jogo, dict):
        raise HTTPException(
            status_code=502,
            detail="A API retornou detalhes inválidos"
        )

    sincronizar_jogos([jogo], sessao)

    return jogo'''