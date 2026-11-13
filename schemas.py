from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# Os limites de tamanho seguem as colunas de CriarTabela.py
# (username 30, biografia 300, avatar_url 300, id_externo 100, nome 255 ...).


# ---------- Usuários / perfis ----------
class PerfilAtualizar(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: Optional[str] = Field(default=None, min_length=1, max_length=30)
    biografia: Optional[str] = Field(default=None, max_length=300)
    avatar_url: Optional[str] = Field(default=None, max_length=300)


class UsuarioResumo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_usuario: int
    username: str
    avatar_url: Optional[str]


class UsuarioPublico(UsuarioResumo):
    biografia: Optional[str]
    data_cadastro: datetime
    total_seguidores: int
    total_seguindo: int
    total_reviews: int


class UsuarioPrivado(UsuarioPublico):
    email: str


class SeguirResponse(BaseModel):
    id_usuario: int  # quem segue
    id_seguido: int  # quem é seguido


# ---------- Jogos ----------
class JogoCriar(BaseModel):
    id_externo: str = Field(min_length=1, max_length=100)
    nome: str = Field(min_length=1, max_length=255)
    descricao: Optional[str] = None
    data_lancamento: Optional[date] = None
    capa_url: Optional[str] = Field(default=None, max_length=500)
    desenvolvedor: Optional[str] = Field(default=None, max_length=255)


class JogoAtualizar(BaseModel):
    id_externo: Optional[str] = Field(default=None, min_length=1, max_length=100)
    nome: Optional[str] = Field(default=None, min_length=1, max_length=255)
    descricao: Optional[str] = None
    data_lancamento: Optional[date] = None
    capa_url: Optional[str] = Field(default=None, max_length=500)
    desenvolvedor: Optional[str] = Field(default=None, max_length=255)


class JogoResponse(BaseModel):
    id_jogo: int
    id_externo: str
    nome: str
    descricao: Optional[str]
    data_lancamento: Optional[date]
    capa_url: Optional[str]
    desenvolvedor: Optional[str]
    data_atualizacao: Optional[datetime]
    nota_media: Optional[float]  # None enquanto não houver reviews
    total_reviews: int


# ---------- Reviews ----------
class ReviewCriar(BaseModel):
    # 0 a 5, no máximo uma casa decimal (Numeric(2, 1) + CHECK nota 0..5)
    nota: Decimal = Field(ge=0, le=5, max_digits=2, decimal_places=1)
    texto: Optional[str] = Field(default=None, max_length=5000)


class ReviewAtualizar(BaseModel):
    nota: Optional[Decimal] = Field(
        default=None, ge=0, le=5, max_digits=2, decimal_places=1
    )
    texto: Optional[str] = Field(default=None, max_length=5000)


class ReviewResponse(BaseModel):
    id_avaliacao: int
    id_usuario: int
    username: str
    id_jogo: int
    jogo_nome: str
    capa_url: Optional[str] = None
    nota: float
    texto: Optional[str]
    data_criacao: datetime
    data_atualizacao: Optional[datetime]
