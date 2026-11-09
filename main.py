from fastapi import FastAPI, HTTPException, Depends, Query #implementado o Query
from auth import router as auth_router
from auth import verificar_token
from datetime import date, datetime, timezone #implementado
from typing import Iterator, Optional #implementado
from sqlalchemy.exc import SQLAlchemyError #implementado
from sqlalchemy.orm import Session as ORMSession #implementado
import requests

from database import engine, Base, Session #Session importada para criar sessão com o banco de dados
import CriarTabela 
Base.metadata.create_all(bind=engine)

app = FastAPI()
app.include_router(auth_router)

FREETOGAME_API_URL = "https://www.freetogame.com/api" #implementado
FREETOGAME_TIMEOUT = 10                               #implementado

def obter_sessao() -> Iterator[ORMSession]: #FUNC implementada para criar sessão com o banco de dados
    sessao = Session()

    try:
        yield sessao
    finally:
        sessao.close()

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
        
def sincronizar_jogos(jogos: list[dict], sessao: ORMSession): #FUNC implementada para sincronizar os dados dos jogos com o banco de dados
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
                sessao.query(CriarTabela.jogo)
                .filter_by(id_externo=str(id_externo))
                .first()
            )

            if jogo is None:
                jogo = CriarTabela.jogo(
                    id_externo=str(id_externo),
                    nome=nome
                )
                sessao.add(jogo)

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
            jogo.data_atualizacao = datetime.now(timezone.utc)

        sessao.commit()

    except SQLAlchemyError as erro:
        sessao.rollback()
        raise HTTPException(
            status_code=500,
            detail="Erro ao atualizar o catálogo de jogos"
        ) from erro

    except HTTPException:
        sessao.rollback()
        raise
    
@app.get("/jogos") #FUNC implementada para listar os jogos, com filtros opcionais de categoria, plataforma e ordenação
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

    return jogo

