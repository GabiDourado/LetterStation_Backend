import pytest
from pydantic import ValidationError
from schemas import ReviewCriar


def test_criar_review_sem_nota(): #verifica se o campo nota é obrigatório
    with pytest.raises(ValidationError):
        ReviewCriar(texto="Gostei bastante do jogo!")