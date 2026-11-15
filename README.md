# 🎮 LetterStation — Back-end

API responsável pelo funcionamento do LetterStation, uma plataforma de interação entre jogadores, inspirada no Letterboxd.

O back-end concentra as regras de negócio, autenticação dos usuários, gerenciamento das informações e comunicação com o banco de dados e serviços externos.

## 📋 Tecnologias utilizadas

- Python
- FastAPI
- SQLAlchemy
- SQLite
- Firebase Authentication
- Firebase Admin SDK
- FreeToGame API

## ⚙️ Pré-requisitos

Antes de começar, é necessário ter instalado:

- [Python](https://www.python.org/) (versão compatível com as dependências do projeto).
- [Git](https://git-scm.com/).

Também é necessário possuir acesso a um projeto Firebase configurado para autenticação.

## 📥 Instalação

1. Clone o repositório:

```bash
git clone URL_DO_REPOSITORIO
```

2. Acesse a pasta do projeto:

```bash
cd LetterStation_Backend
```

3. Crie um ambiente virtual:

```bash
python -m venv venv
```

4. Ative o ambiente virtual.

No Windows:

```bash
venv\Scripts\activate
```

No Linux/macOS:

```bash
source venv/bin/activate
```

5. Instale as dependências:

```bash
pip install -r requirements.txt
```

## 🔐 Configuração do Firebase

O projeto utiliza o Firebase Authentication para realizar a autenticação dos usuários.

Para executar o back-end, é necessário configurar as credenciais do Firebase.

### 1. Arquivo de credenciais

Cada integrante deve obter um arquivo de chave privada de uma conta de serviço do Firebase:

1. Acesse o [Firebase Console](https://console.firebase.google.com/).
2. Selecione o projeto Firebase utilizado pelo LetterStation.
3. Acesse as configurações do projeto.
4. Entre na seção de contas de serviço.
5. Gere uma nova chave privada.
6. Salve o arquivo na pasta do back-end com o nome:

```text
firebase-key.json
```

O arquivo deve ficar na localização esperada pela configuração do projeto.

**Importante:** esse arquivo contém credenciais privadas. Nunca o envie para o GitHub ou compartilhe publicamente.

### 2. Variáveis de ambiente

Crie um arquivo `.env` na raiz do back-end.

Configure as variáveis necessárias conforme o arquivo `.env.example`:

```env
FIREBASE_API_KEY=
```

Preencha a chave correspondente ao projeto Firebase utilizado.

Não compartilhe o arquivo `.env`.

## 🗄️ Banco de dados

O LetterStation utiliza SQLite como banco de dados relacional e SQLAlchemy para o mapeamento das entidades.

O banco de dados local é armazenado no arquivo:

```text
banco.db
```

Esse arquivo não é versionado no Git. Cada integrante terá sua própria cópia local.

As tabelas são criadas automaticamente pela configuração de inicialização do projeto, utilizando os modelos definidos no back-end.

## ▶️ Executando a API

Com o ambiente virtual ativado e as configurações realizadas, execute:

```bash
uvicorn main:app --reload
```

Por padrão, a API ficará disponível em:

http://localhost:8000

## 📚 Documentação da API

O FastAPI disponibiliza uma documentação interativa dos endpoints por meio do Swagger UI.

Para acessar:

http://localhost:8000/docs

Nessa página é possível consultar os endpoints, visualizar os parâmetros esperados e realizar requisições para testar as funcionalidades da API.

## 🔑 Autenticação

A autenticação é realizada pelo Firebase Authentication.

Após o login, o sistema utiliza o token de autenticação Firebase nas requisições que exigem identificação do usuário.

Essas requisições utilizam o cabeçalho:

```http
Authorization: Bearer SEU_TOKEN
```

O back-end verifica a validade do token antes de permitir o acesso aos recursos protegidos.

## 🔗 Principais funcionalidades

A API disponibiliza operações relacionadas a:

- Cadastro e autenticação de usuários.
- Consulta e atualização de perfis.
- Exclusão da própria conta.
- Pesquisa e consulta de jogos.
- Gerenciamento de resenhas.
- Consulta de resenhas publicadas.
- Seguir e deixar de seguir usuários.
- Consulta de informações de usuários e seus perfis públicos.

## 🔗 Integração com o front-end

O front-end realiza requisições HTTP para a API.

O endereço local padrão utilizado durante o desenvolvimento é:

http://localhost:8000

A API utiliza configuração de CORS para permitir a comunicação com o front-end, normalmente executado em:

http://localhost:5173

Caso a origem ou a porta do front-end seja alterada, a configuração de CORS deverá ser atualizada.

## ⚠️ Solução de problemas

**Erro ao iniciar a API:**
- Verifique se o ambiente virtual está ativado.
- Confira se as dependências foram instaladas.
- Verifique se o comando está sendo executado na pasta correta.

**Erro relacionado ao Firebase:**
- Confira se o arquivo `firebase-key.json` existe.
- Verifique se o caminho configurado no código corresponde à localização do arquivo.
- Confira se o arquivo pertence ao projeto Firebase correto.

**Erro de conexão com o banco de dados:**
- Verifique as configurações de conexão do SQLite.
- Confira se o diretório utilizado permite a criação do arquivo do banco.

**Erro de CORS:**
- Confira se a origem do front-end está autorizada no back-end.
- Verifique se o front-end está utilizando o endereço correto da API.

## 👥 Projeto acadêmico

LetterStation é um projeto acadêmico desenvolvido como parte das atividades do curso de Ciência da Computação.

O projeto tem como objetivo desenvolver uma aplicação integrada, utilizando API própria, banco de dados relacional, autenticação e integração com serviços externos.