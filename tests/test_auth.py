from auth import criar_usuario, Usuario
import pytest
from fastapi import HTTPException #pois a exceções são lançadas com HTTPException, então precisamos importar para testar

def test_criar_usuario():
    usuario_teste = Usuario(
        email="teste6711@gmail.com",
        username="TesteUSUARIO2123786171",
        senha="123Abc@#$"
    )

    usuario_criado = criar_usuario(usuario_teste)

    # ta em colchetes pq é um dicionario
    assert usuario_criado["email"] == usuario_teste.email
    

def test_criar_usuario_username_existente():
    usuario_teste = Usuario(
        email="teste4@gmail.com",
        username="TesteUSUARIO2123",
        senha="123Abc@#$"
    )

    with pytest.raises(HTTPException) as exc: #o exc é uma variável que vai armazenar a exceção lançada.
        criar_usuario(usuario_teste)

    assert exc.value.status_code == 409
    assert exc.value.detail == "Nome de usuário já está em uso"
    

def test_email_senha_invalido():
    usuario_teste = Usuario(
        email="teste715gmail.com",
        username="TesteUSUARIO21237915",
        senha="123Abc@#$"
    )

    with pytest.raises(AttributeError):
        criar_usuario(usuario_teste)