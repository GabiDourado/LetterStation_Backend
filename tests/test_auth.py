from auth import criar_usuario, Usuario
import pytest

def test_criar_usuario():
    usuario_teste = Usuario(
        email="teste3@gmail.com",
        username="TesteUSUARIO2123",
        senha="123Abc@#$"
    )

    usuario_criado = criar_usuario(usuario_teste)

    # ta em colchetes pq é um dicionario
    assert usuario_criado["email"] == usuario_teste.email