# API do LetterStation (jogos, perfis, seguidores e reviews)

Arquivos: `comum.py`, `schemas.py` e `routers/` (usuarios, jogos, reviews).
Depende de `auth.py` (`verificar_token`) e de `CriarTabela.py`.

Integração em arquivos compartilhados:
- `database.py`: adicionar `get_db` e `PRAGMA foreign_keys=ON` (SQLite não valida chaves estrangeiras por padrão).
- `main.py`: importar e registrar os 3 routers; mover o catálogo FreeToGame para `/catalogo/jogos` e `/catalogo/jogos/{game_id}` para liberar `/jogos`.

## Endpoints da API

🔒 = exige `Authorization: Bearer <token>` (token obtido em `/login`).

### Catálogo externo (FreeToGame) — `main.py`
| Método | Rota | Descrição |
|---|---|---|
| GET | `/catalogo/jogos?category=&platform=&sort-by=` | Consulta a FreeToGame e sincroniza na tabela `jogo` |
| GET | `/catalogo/jogos/{game_id}` | Detalhe na FreeToGame (id externo) e sincroniza |

Depois de sincronizar, use `GET /jogos?id_externo=<id>` para descobrir o `id_jogo` interno
(usado nas reviews).

### Perfis e seguidores
O perfil é criado junto com a conta, em `POST /usuarios`.

| Método | Rota | Descrição | Retorno |
|---|---|---|---|
| GET | `/usuarios/me` 🔒 | Vê o próprio perfil | 200 / 404 |
| PUT | `/usuarios/me` 🔒 | Atualiza username, biografia, avatar | 200 / 409 / 422 |
| DELETE | `/usuarios/me` 🔒 | Apaga o perfil, reviews e vínculos | 204 |
| GET | `/usuarios?busca=` | Lista/busca usuários | 200 |
| GET | `/usuarios/{id}` | Perfil público com contagens | 200 / 404 |
| GET | `/usuarios/{id}/seguidores` | Quem segue o usuário | 200 / 404 |
| GET | `/usuarios/{id}/seguindo` | Quem o usuário segue | 200 / 404 |
| POST | `/usuarios/{id}/seguir` 🔒 | Seguir | 201 / 400 / 404 / 409 |
| DELETE | `/usuarios/{id}/seguir` 🔒 | Deixar de seguir | 204 / 404 |

### Jogos (banco local)
| Método | Rota | Descrição | Retorno |
|---|---|---|---|
| GET | `/jogos?busca=&id_externo=&ordenar=nome\|lancamento\|nota` | Lista jogos com nota média | 200 |
| GET | `/jogos/{id}` | Detalhe do jogo | 200 / 404 |
| POST | `/jogos` 🔒 | Cadastra jogo | 201 / 409 |
| PUT | `/jogos/{id}` 🔒 | Atualiza jogo | 200 / 404 / 409 |
| DELETE | `/jogos/{id}` 🔒 | Exclui jogo (sem reviews) | 204 / 404 / 409 |

### Reviews
| Método | Rota | Descrição | Retorno |
|---|---|---|---|
| POST | `/jogos/{id}/reviews` 🔒 | Avalia um jogo (nota 0–5, 1 casa decimal) | 201 / 404 / 409 |
| GET | `/jogos/{id}/reviews` | Reviews de um jogo | 200 / 404 |
| GET | `/usuarios/{id}/reviews` | Reviews de um usuário | 200 / 404 |
| GET | `/reviews/{id}` | Detalhe da review | 200 / 404 |
| PUT | `/reviews/{id}` 🔒 | Edita a própria review | 200 / 403 / 404 |
| DELETE | `/reviews/{id}` 🔒 | Exclui a própria review | 204 / 403 / 404 |
| GET | `/feed` 🔒 | Reviews de quem o usuário segue | 200 |

As listagens aceitam `limit` (1–100, padrão 20) e `offset`.
