from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from routers.reviews import _review_do_dono
from routers.usuarios import seguir_usuario, deixar_de_seguir

def test_usuario_so_pode_acessar_sua_review(): #testa se o usuário só pode acessar sua própria review
    review = SimpleNamespace(id_usuario=2)
    db = SimpleNamespace(get=lambda model, id: review)

    with pytest.raises(HTTPException) as erro:
        _review_do_dono(db, 1, SimpleNamespace(id_usuario=1))

    assert erro.value.status_code == 403
    

def test_relacionamento_seguidores(): #testa se o usuário não pode seguir a si mesmo
    usuario = SimpleNamespace(id_usuario=1)
    db = SimpleNamespace()

    # Não pode seguir a si mesmo
    with pytest.raises(HTTPException) as erro:
        seguir_usuario(1, usuario, db)
    assert erro.value.status_code == 400