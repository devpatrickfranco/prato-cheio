# PAGAFARRA

Projeto base em Django executado com Docker.

---

## 📋 Pré-requisitos

Antes de começar, instale o **Docker** e o **Docker Compose** no seu sistema:

### Windows
1. Baixe o [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).
2. Execute o instalador e siga as instruções.
3. Certifique-se de que a virtualização (WSL 2 ou Hyper-V) esteja habilitada.
4. Após a instalação, reinicie a máquina se necessário.
5. Abra o **PowerShell** ou **Prompt de Comando** e verifique:
   ```bash
   docker --version
   docker compose version
   ```

### Linux
1. Atualize o gerenciador de pacotes e instale o Docker:
   ```bash
   sudo apt update
   sudo apt install docker.io docker-compose-plugin
   ```
2. Inicie o serviço do Docker (e habilite para iniciar junto com o sistema):
   ```bash
   sudo systemctl start docker
   sudo systemctl enable docker
   ```
3. (Opcional) Adicione seu usuário ao grupo `docker` para não usar `sudo`:
   ```bash
   sudo usermod -aG docker $USER
   ```
   Faça logout e login novamente para aplicar.
4. Verifique a instalação:
   ```bash
   docker --version
   docker compose version
   ```

### macOS
1. Baixe o [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/).
2. Arraste o Docker.app para a pasta **Aplicativos**.
3. Abra o Docker Desktop e aguarde o motor do Docker iniciar.
4. Abra o **Terminal** e verifique:
   ```bash
   docker --version
   docker compose version
   ```

---

## 🚀 Como Executar

### 1. Iniciar a aplicação
Construa as imagens e inicie os containers em segundo plano:
```bash
docker compose up -d --build
```

As migrations são aplicadas automaticamente ao subir o container. Para criar as contas e lotes de
demonstração (senha `prato123demo`):
```bash
docker compose exec web python manage.py criar_dados_demo
```

Acesse a aplicação no navegador em: **http://localhost:8000**

### 2. Parar a aplicação
Para encerrar os containers em execução:
```bash
docker compose down
```

### Execução local (sem Docker)
Requer Python 3.13.
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Variáveis de ambiente
As configurações sensíveis são lidas do ambiente; veja `.env.example` (`DJANGO_SECRET_KEY`,
`DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`). Sem elas, o projeto usa padrões de desenvolvimento.
Nunca versione o arquivo `.env`.

---

## ⚙️ Comandos Úteis do Django

Execute os comandos diretamente no container `web`:

| Comando | Descrição |
|---|---|
| `docker compose exec web python manage.py migrate` | Executar migrations |
| `docker compose exec web python manage.py createsuperuser` | Criar superusuário |
| `docker compose exec web python manage.py shell` | Abrir o Django Shell |
| `docker compose exec web python manage.py test` | Executar os testes |
| `docker compose exec web python manage.py makemigrations` | Gerar migrations após alterar models |
| `docker compose exec web python manage.py check` | Verificar a configuração do projeto |

Sem Docker, rode os mesmos comandos a partir de `python manage.py ...`.

---

## 📁 Estrutura de Diretórios

```
.
├── config/                 # Configurações do Django (settings, urls raiz, wsgi/asgi)
├── apps/
│   ├── usuarios/           # Models Usuario (AUTH_USER_MODEL, login por e-mail) e Estabelecimento; seleção de perfil
│   │   ├── perfis.py       # Perfis Doador, Consumidor e ONG (iguais a Usuario.tipo_perfil)
│   │   └── templates/usuarios/
│   ├── lotes/              # Models Categoria, Alimento, Lote e Reserva; vitrine (/explore/) e gestão do doador (/meus-lotes/)
│   │   ├── catalogo.py     # Categorias e classificação dos alimentos do CSV
│   │   ├── geo.py          # Fórmula de Haversine
│   │   ├── selectors.py    # Consulta da vitrine (validade, distância e raio)
│   │   ├── dados/pegadas_alimentos_brasil.csv   # Fonte das pegadas de CO₂, água e ecológica
│   │   └── management/commands/criar_dados_demo.py
│   ├── metricas/           # Painéis de impacto (CO₂ evitado, alimentos salvos, refeições)
│   └── auth/               # Login com JWT (páginas e API). Label `jwt_auth`, pois `auth` é do django.contrib.auth
├── templates/              # Templates compartilhados entre apps
│   ├── base.html           # Esqueleto HTML de todas as páginas
│   ├── layouts/acesso.html # Layout das telas de acesso (seleção de perfil e login)
│   ├── layouts/app.html    # Layout das áreas logadas (sidebar + conteúdo)
│   └── components/         # Componentes reutilizáveis (sidebar)
├── static/css/style.css    # Folha de estilo global
├── docs/                   # Documentação acadêmica e screenshots do protótipo
├── Dockerfile / docker-compose.yml
├── manage.py
└── requirements.txt
```

### Arquitetura

- Cada app declara as próprias rotas em `urls.py` (com `app_name`), e `config/urls.py` apenas as inclui.
  Rotas são referenciadas por namespace: `jwt_auth:login_doador`, `metricas:dashboard_doador`, `lotes:explorar`.
- Templates de um app ficam em `apps/<app>/templates/<app>/`; a pasta global `templates/` guarda só o que
  é compartilhado (layout base, layout das áreas logadas e componentes).
- Recursos estáticos específicos de um app ficam em `apps/<app>/static/<app>/`; o CSS global em `static/`.
- Dependências entre apps: `auth`, `lotes` e `metricas` usam `apps.usuarios.perfis`; `lotes` e `metricas`
  usam `apps.auth.decorators`; `usuarios` não importa outros apps.
- Banco de dados: SQLite (`db.sqlite3`, não versionado). O schema vem exclusivamente dos models;
  `python manage.py migrate` cria as tabelas e carrega categorias e alimentos a partir do CSV.
- Os painéis de impacto (`PAINEIS` em `metricas/views.py`) ainda exibem números fixos do protótipo.

### Perfis

| Perfil | Pessoa | Acesso |
|---|---|---|
| Doador | Jurídica (estabelecimento) | `/login/doador/` → painel e Meus Lotes |
| Consumidor | Física | `/login/consumidor/` → painel e Explorar Lotes |
| ONG | Jurídica | `/login/ong/` → painel e Explorar Lotes |

### Dados de demonstração

```bash
python manage.py criar_dados_demo
```
Cria em Campinas/SP três doadores com lotes, o consumidor `joao@demo.com` e a ONG `esperanca@demo.com`
(senha de todas: `prato123demo`). Pode ser executado mais de uma vez.

### Categorias e alimentos

Cada linha do CSV vira um `Alimento` com a descrição original (ex.: "arroz integral") e uma `Categoria`
(ex.: "Grãos e cereais"), atribuída em `lotes/catalogo.py` pelo grupo de origem e, quando o grupo não
corresponde à prateleira, pelo nome do item (ex.: "ovo de galinha" → Ovos, "suco de laranja" → Bebidas).
O fator de CO₂ da categoria é a mediana dos seus alimentos na forma de varejo. Um lote pode indicar o
alimento (fator específico) ou só a categoria (fator da categoria): `Lote.co2_evitado_kg`.

### Distância (fórmula de Haversine)

A vitrine mostra a distância em linha reta até cada estabelecimento, calculada por
`lotes.geo.haversine_km` a partir da localização do navegador (botão "Usar minha localização") ou, na
falta dela, das coordenadas do cadastro do usuário. O campo "Até x km" (`?raio=`) mantém apenas os lotes
dentro do raio. Estabelecimentos e usuários sem `latitude`/`longitude` aparecem sem distância.

### Autenticação JWT (`apps/auth`)

As páginas depois do login são protegidas por `apps.auth.decorators.login_obrigatorio`: o login emite
access e refresh tokens em cookies HttpOnly; com o access expirado, o refresh gera outro automaticamente;
sem token válido, o usuário volta à seleção de perfil; com perfil errado, vai para o próprio painel.

Para clientes externos há uma API JSON:

| Rota | Método | Corpo | Resposta |
|---|---|---|---|
| `/auth/token/` | POST | `{"email": "...", "senha": "..."}` | `{"access": "...", "refresh": "..."}` |
| `/auth/token/renovar/` | POST | `{"refresh": "..."}` | `{"access": "..."}` |
| `/auth/eu/` | GET | header `Authorization: Bearer <access>` | dados do usuário autenticado |

Só contas ativas com `status_conta = aprovado` acessam. Para proteger uma rota da API, use
`apps.auth.decorators.jwt_obrigatorio`. A validade dos tokens é configurada em `.env.example`.

---

## 📝 Pendências

Estado em 28/10/2026. O trabalho está no branch `refactor/arquitetura-apps`, **ainda sem commit**.

### Funcionalidades

**Reservas (consumidor e ONG)**
- [ ] Botão "Reservar Lote" na vitrine (hoje é `#`): criar `Reserva` e mudar o lote para `reservado`.
- [ ] Expirar reservas vencidas: reserva `ativa` com `data_expiracao` passada vira `expirada` e o lote volta a `disponivel`.
- [ ] Doador confirma a retirada (`retirado`) ou registra `nao_retirado`.
- [ ] Tela de "minhas reservas" para consumidor e ONG.

**Lotes (doador)**
- [ ] Excluir ou cancelar lote.
- [ ] Foto do lote: upload (configurar `MEDIA_ROOT`/`MEDIA_URL`). Hoje a vitrine usa a imagem padrão da categoria.
- [ ] Marcar como `expirado` os lotes disponíveis cuja validade passou. A vitrine já os esconde pela data, mas o status não muda.
- [ ] Melhorar a escolha do alimento no formulário (lista com 1038 itens): busca com autocomplete.

**Vitrine**
- [ ] Campo "Buscar alimentos..." (ainda não funciona).
- [ ] Filtros por categoria e por bairro.
- [ ] Opcional: distância por rota (hoje é em linha reta, pela fórmula de Haversine).

**Painéis de impacto**
- [ ] Trocar os números fixos (`PAINEIS` em `metricas/views.py`) por dados reais dos lotes `retirado`:
  kg salvos, CO₂ evitado (`Lote.co2_evitado_kg`) e refeições (kg ÷ 0,4).
- [ ] Gráfico "Impacto Ambiental Histórico" e "Ver Relatório Completo" (hoje são espaços reservados).
- [ ] Lista de atividades recentes com dados reais.

**Contas e cadastro**
- [ ] Cadastro de novos usuários (doador, consumidor e ONG). Hoje as contas são criadas pelo admin ou por `criar_dados_demo`.
- [ ] Fluxo de aprovação de contas pelo admin (`status_conta` pendente → aprovado/recusado).
- [ ] Cadastro e edição do estabelecimento pelo próprio doador.
- [ ] Documento por perfil: CPF para consumidor (PF) e CNPJ para ONG (PJ). O doador já tem CNPJ no `Estabelecimento`.
- [ ] Geocodificação do endereço/CEP para preencher latitude e longitude automaticamente.
- [ ] "Esqueceu a senha?" (hoje é `#`).
- [ ] Admin do `Usuario`: permitir troca de senha (hoje o campo de senha fica oculto).

**Escopo original ainda não iniciado:** compra e venda, gamificação para PJ e comissão por venda.

### Técnico

- [ ] Fazer o commit e abrir a PR do branch `refactor/arquitetura-apps`.
- [ ] Produção:
  - `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY` e `DJANGO_ALLOWED_HOSTS` definidos;
  - `collectstatic` (com o volume `.:/app` do compose, a pasta `staticfiles/` gerada no build fica oculta);
  - `CSRF_TRUSTED_ORIGINS` para HTTPS;
  - carregar o `.env` no `docker-compose.yml` (`env_file`).
- [ ] O `Dockerfile` instala `libpq-dev` (PostgreSQL), mas o projeto usa SQLite: remover ou migrar para PostgreSQL.
- [ ] JWT: o logout só apaga os cookies, e os tokens continuam válidos até expirar. Avaliar uma lista de revogação.
- [ ] Limitar tentativas de login (proteção contra força bruta).
- [ ] Comando para reclassificar os alimentos quando `lotes/catalogo.py` mudar. A migration `0003_catalogo` só classifica na criação do banco.

---

## 🔒 Regras de Git

| Tipo | Descrição |
|---|---|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `refactor` | Melhorar/reorganizar código |
| `perf` | Melhorar performance |
| `docs` | Documentação |
| `test` | Testes |
| `style` | Formatação/estilo |
| `build` | Dependências/build |
| `ci` | CI/CD |
| `chore` | Manutenção geral |
| `revert` | Desfazer commit |

# ESCOPO

Apps
   - Usuarios
   -- PJ / compra e venda, gamificação
   -- PF / compra
   -- ONG / Recebe doação
   -- Localização

   - Produto
   -- categorias
   -- cadastra
   -- vender
   -- doar
   -- comprar
   -- Retirada
   -- prazo de vencimento
   -- garantia de qualidade / imagem codigo de barra e vencimento
   -- imagens
   -- descrição
   -- quantidade
   -- unidade

   - Metricas
   -- CO2
   -- Kg não desperdiçados

Modelo de negocio

   - Comissão por venda

Metologia

   - SCRUM
   - KANBAN


   joao@demo.com, esperanca@demo.com e mercado@demo.com. A senha de todos é prato123demo.