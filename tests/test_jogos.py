from unittest.mock import MagicMock
from datetime import date
from routers.jogos import sincronizar_jogos

def test_jogo_externo_e_salvo_no_banco_local(): #verifica se o jogo externo é salvo no banco local
    db = MagicMock()
    db.query.return_value.filter_by.return_value.first.return_value = None

    dados = [{
        "id": 123,
        "title": "Minecraft",
        "description": "Jogo de construção",
        "release_date": "2011-11-18",
        "thumbnail": "capa.jpg",
        "developer": "Mojang"
    }]

    sincronizar_jogos(dados, db)

    jogo = db.add.call_args.args[0]

    assert jogo.id_externo == "123"
    assert jogo.nome == "Minecraft"
    assert jogo.descricao == "Jogo de construção"
    assert jogo.data_lancamento == date(2011, 11, 18)
    assert jogo.capa_url == "capa.jpg"
    assert jogo.desenvolvedor == "Mojang"
    db.commit.assert_called_once()