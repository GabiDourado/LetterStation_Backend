from sqlalchemy import Column, Integer, String, Text, Date, TIMESTAMP, ForeignKey, Numeric, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship
from database import Base
import sqlite3

class jogo(Base):
    __tablename__ = "jogo"
    
    id_jogo = Column(Integer, primary_key=True)
    id_externo = Column(String(100), nullable=False)
    nome = Column(String(255), nullable=False)
    descricao = Column(Text)
    data_lancamento = Column(Date)
    capa_url = Column(String(500))
    desenvolvedor = Column(String(255))
    data_atualizacao = Column(TIMESTAMP, nullable=True)

class usuario(Base):
    __tablename__ = "usuario"
    
    id_usuario = Column(Integer, primary_key=True)
    firebase_uid = Column(String(128), nullable=False, unique=True)
    username = Column(String(30), nullable=False, unique=True)
    email = Column(String(128), nullable=False)
    biografia = Column(String(300))
    avatar_url = Column(String(300))
    data_cadastro = Column(TIMESTAMP, nullable=False)

class usuario_seguidores(Base):
    __tablename__ = "usuario_seguidores"
    
    usu_seg_id = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)
    id_seguido = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)
    __table_args__ = (
        UniqueConstraint("id_usuario", "id_seguido"),
        CheckConstraint("id_usuario != id_seguido"),
    )

class review(Base):
    __tablename__ = "review"
    
    id_avaliacao = Column(Integer, primary_key=True)
    id_usuario = Column(Integer, ForeignKey("usuario.id_usuario"), nullable=False)
    id_jogo = Column(Integer, ForeignKey("jogo.id_jogo"), nullable=False)
    nota = Column(Numeric(2, 1), nullable=False)
    texto = Column(Text)
    data_criacao = Column(TIMESTAMP, nullable=False)
    data_atualizacao = Column(TIMESTAMP, nullable=True)
    
    __table_args__ = (
        CheckConstraint('nota >= 0 AND nota <= 5', name='check_nota_range'),
    )
    
#Teste de inserção de dados nas tabelas
conexao = sqlite3.connect('banco.db')
cursor = conexao.cursor()

comando_review = """
INSERT INTO review (id_usuario, id_jogo, nota, texto, data_criacao) 
VALUES (1, 1, 4.5, 'Ótimo jogo!', '2023-10-01 12:00:00');
"""

cursor.execute(comando_review)
conexao.commit()

conexao.close()

print("Avaliação inserida com sucesso")
    

