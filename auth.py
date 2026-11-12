from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import os
import requests
import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, auth
from firebase_admin.exceptions import FirebaseError
from database import engine, Base, Session
from datetime import datetime
from CriarTabela import usuario as UsuarioDB
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
import CriarTabela 

load_dotenv()
router = APIRouter(tags=["Autenticação"])
API_KEY = os.getenv("FIREBASE_API_KEY")
cred = credentials.Certificate("firebase-key.json")
firebase_admin.initialize_app(cred)
security = HTTPBearer()


class Usuario(BaseModel):
    email: str
    senha: str
    username: str

class LoginUsuario(BaseModel):
    email: str
    senha: str


@router.post("/usuarios")
def criar_usuario(usuario: Usuario):
    db = Session()
    novo_usuario = None

    try:
        # Verifica se o username já está cadastrado
        usuario_existente = db.query(UsuarioDB).filter(
            func.lower(UsuarioDB.username) == usuario.username.lower()
        ).first()

        if usuario_existente:
            raise HTTPException(
                status_code=409,
                detail="Nome de usuário já está em uso"
            )

        # Cria o usuário no Firebase
        novo_usuario = auth.create_user(
            email=usuario.email,
            password=usuario.senha
        )

        # Cria o registro no banco local
        usuario_db = UsuarioDB(
            firebase_uid=novo_usuario.uid,
            username=usuario.username.lower(),
            email=usuario.email,
            biografia=None,
            avatar_url=None,
            data_cadastro=datetime.now()
        )

        db.add(usuario_db)
        db.commit()
        db.refresh(usuario_db)

        return {
            "uid": novo_usuario.uid,
            "id_usuario": usuario_db.id_usuario,
            "username": usuario_db.username,
            "email": usuario_db.email
        }

    except HTTPException:
        raise

    except auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=409,
            detail="Este e-mail já está cadastrado"
        )

    except auth.InvalidPasswordError:
        raise HTTPException(
            status_code=400,
            detail="A senha não atende aos requisitos"
        )

    except Exception as e:
        db.rollback()
        print("ERRO AO CADASTRAR:", repr(e))

        if novo_usuario:
            try:
                auth.delete_user(novo_usuario.uid)
            except Exception as erro_firebase:
                print("ERRO AO EXCLUIR DO FIREBASE:", repr(erro_firebase))

        if isinstance(e, IntegrityError):
            raise HTTPException(
                status_code=409,
                detail="Já existe um registro com esses dados"
            )

        raise HTTPException(
            status_code=500,
            detail="Erro interno ao cadastrar usuário"
        )

    finally:
        db.close()


@router.post("/login")
def login(usuario: LoginUsuario):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
    dados = {
        "email": usuario.email,
        "password": usuario.senha,
        "returnSecureToken": True
    }
    resposta = requests.post(url, json=dados)
    if resposta.status_code != 200:
        raise HTTPException(status_code=401, detail="Email ou senha inválidos")

    return {
        "token": resposta.json()["idToken"]
    }


def verificar_token(credenciais: HTTPAuthorizationCredentials = Depends(security)):
    token = credenciais.credentials
    try:
        usuario = auth.verify_id_token(token)
        return usuario
    except Exception:
        raise HTTPException(status_code=401, detail="Token inválido")


@router.get("/perfil")
def perfil(usuario = Depends(verificar_token)):
    return {
        "uid": usuario["uid"],
        "email": usuario["email"]
    }
