# PAGAFARRA

Projeto base em Django executado com Docker.

## 🌱 Sobre o projeto (Prato Cheio)

Plataforma que conecta estabelecimentos com **excedente de alimentos próximo do vencimento** (mercados,
padarias, hortifrútis) a **consumidores e ONGs**, que reservam e retiram os lotes. Cada retirada confirmada
gera métricas de impacto (kg salvos, CO₂ evitado, refeições estimadas).

| Item | Descrição |
|---|---|
| Problema | Desperdício de alimentos no varejo enquanto há pessoas e instituições que precisam deles |
| Setor | Terceiro Setor (ONGs) em parceria com o Segundo Setor (varejo doador) |
| ODS | 2 (Fome Zero), 12 (Consumo e Produção Responsáveis) e 13 (Ação contra a Mudança do Clima) |
| Impacto | Social, ambiental e econômico |
| Tecnologias | Python 3.13, Django 6.1, SQLite, JWT (PyJWT), HTML5/CSS3/JavaScript sem framework, Docker |
| Status | MVP em desenvolvimento (ver Pendências) |

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
`DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`, `DJANGO_CSRF_TRUSTED_ORIGINS`, JWT, e-mail e geocodificação).
Sem elas, o projeto usa padrões de desenvolvimento. Nunca versione o arquivo `.env`; o
`docker-compose.yml` o carrega sozinho (`env_file`, opcional).

**Produção** (`DJANGO_DEBUG=False`): o app **recusa subir** sem `DJANGO_SECRET_KEY` próprio (e chave JWT, se
definida, que não seja o exemplo) e sem `DJANGO_ALLOWED_HOSTS`. Nesse modo, cookies de sessão/CSRF/JWT só
trafegam por HTTPS; atrás de um proxy HTTPS defina `DJANGO_PROXY_SSL=True` (confia em `X-Forwarded-Proto` e
redireciona http→https) e `DJANGO_CSRF_TRUSTED_ORIGINS=https://seu.dominio`. Para enviar e-mails reais
(recuperação de senha), defina `DJANGO_EMAIL_HOST` e relacionados; sem isso eles saem no console do servidor.
O container executa `migrate` e `collectstatic` ao iniciar (o volume `.:/app` oculta os estáticos gerados no
build). Fotos enviadas ficam em `media/` (monte um volume persistente).

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
| `docker compose exec web python manage.py atualizar_status` | Expirar reservas vencidas e lotes fora da validade (agende no cron; as telas também aplicam a regra ao listar) |
| `docker compose exec web python manage.py reclassificar_alimentos [--simular]` | Reaplicar `lotes/catalogo.py` aos alimentos e lotes já gravados |
| `docker compose exec web python manage.py limpar_auth` | Apagar tokens revogados já expirados e tentativas de login antigas |

Sem Docker, rode os mesmos comandos a partir de `python manage.py ...`.

---

## 📁 Estrutura de Diretórios

```
.
├── config/                 # Configurações do Django (settings, urls raiz, wsgi/asgi)
├── apps/
│   ├── usuarios/           # Models Usuario (AUTH_USER_MODEL, login por e-mail) e Estabelecimento; seleção de perfil e cadastro
│   │   ├── perfis.py       # Perfis Doador, Consumidor e ONG (iguais a Usuario.tipo_perfil)
│   │   ├── forms.py        # Cadastro (CPF/CNPJ, senha) e estabelecimento
│   │   ├── validators.py   # Dígitos verificadores de CPF/CNPJ e CEP
│   │   ├── geocodificacao.py  # Endereço/CEP → latitude/longitude (Nominatim/OpenStreetMap)
│   │   ├── static/usuarios/js/cadastro.js  # Validação em tempo real do cadastro
│   │   └── templates/usuarios/
│   ├── lotes/              # Models Categoria, Alimento, Lote e Reserva; vitrine, reservas e gestão do doador
│   │   ├── catalogo.py     # Categorias e classificação dos alimentos do CSV
│   │   ├── geo.py          # Fórmula de Haversine
│   │   ├── selectors.py    # Consulta da vitrine (validade, busca, categoria, bairro, distância e raio)
│   │   ├── services.py     # Reservar, cancelar, confirmar retirada, expirar reservas/lotes, excluir
│   │   ├── dados/pegadas_alimentos_brasil.csv   # Fonte das pegadas de CO₂, água e ecológica
│   │   └── management/commands/criar_dados_demo.py
│   ├── metricas/           # Painéis e relatório de impacto, calculados das retiradas confirmadas (servicos.py)
│   └── auth/               # Login com JWT (páginas e API), recuperação de senha, revogação de tokens e limite de tentativas. Label `jwt_auth`, pois `auth` é do django.contrib.auth
├── templates/              # Templates compartilhados entre apps
│   ├── base.html           # Esqueleto HTML de todas as páginas
│   ├── layouts/acesso.html # Layout das telas de acesso (seleção de perfil e login)
│   ├── layouts/app.html    # Layout das áreas logadas (sidebar + conteúdo)
│   └── components/         # Componentes reutilizáveis (sidebar)
├── static/css/style.css    # Folha de estilo global
├── docs/                   # Documentação acadêmica, screenshots do protótipo e decisões arquiteturais (docs/adr/)
├── media/                  # Fotos enviadas pelos doadores (não versionado)
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
- Os painéis de impacto vêm de dados reais: só lotes `retirado` (reserva confirmada pelo doador) contam.
- Decisões arquiteturais ficam registradas em `docs/adr/` (ADRs).

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

### Cadastro e aprovação de contas

`/cadastro/doador/`, `/cadastro/consumidor/` e `/cadastro/ong/` criam a conta com `status_conta = pendente`;
o administrador aprova ou recusa no Django Admin (filtro "status conta" + ações em lote; a tela da conta também
permite trocar a senha). O consumidor informa **CPF** e a ONG **CNPJ** (validados pelos dígitos verificadores);
o doador informa os dados do estabelecimento (CNPJ, endereço), que ele mesmo edita depois em **Meu
Estabelecimento**. O formulário valida em tempo real (contador de caracteres, força da senha, erros por campo,
sumário de erros acessível e botão habilitado só com tudo válido) e o servidor repete todas as validações.

O endereço/CEP é convertido em latitude/longitude automaticamente (Nominatim/OpenStreetMap, no cadastro e na
edição). Se o serviço não responder, o cadastro segue sem coordenadas e o usuário aparece sem distância na
vitrine (desligue com `DJANGO_GEOCODIFICACAO=False`). Recuperação de senha: "Esqueceu a senha?" envia um link
de uso único.

### Reservas e retirada

| Etapa | Quem | Efeito |
|---|---|---|
| Reservar (`/explore/`) | Consumidor/ONG | Lote vira `reservado`; a reserva vale até o fim da janela de retirada |
| Cancelar (`/minhas-reservas/`) | Quem reservou | Lote volta à vitrine |
| Confirmar retirada (`/meus-lotes/`) | Doador | Reserva `confirmada`, lote `retirado`: passa a contar nas métricas |
| Não retirado (`/meus-lotes/`) | Doador | Reserva `nao_retirada`, lote `nao_retirado` |
| Expiração | Automática | Reserva ativa vencida vira `expirada` e o lote volta a `disponivel` (ou `expirado` se a validade passou); lote disponível vencido vira `expirado` |

A vitrine tem busca (sem diferenciar acentos), filtro por categoria, bairro e distância, e mostra só lotes
disponíveis, dentro da validade e com a janela de retirada em aberto. O doador pode editar lotes disponíveis,
enviar foto (JPG/PNG/WebP até 5 MB) e excluir lotes que não estejam reservados ou retirados. No cadastro de
lote, o campo Alimento tem busca com autocomplete.

### Painéis de impacto

Para o doador, contam as retiradas dos seus lotes; para consumidor e ONG, as próprias. Kg salvos = soma de
`peso_kg`; CO₂ evitado = soma de `Lote.co2_evitado_kg`; refeições = kg ÷ 0,4. A tendência compara o mês
atual com o anterior, o gráfico mostra o CO₂ dos últimos 6 meses e **Ver Relatório Completo**
(`/relatorio/<perfil>/`) detalha 12 meses e cada retirada.

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

| `/auth/token/revogar/` | POST | `{"refresh": "..."}` (+ `Authorization: Bearer <access>` opcional) | revoga os tokens informados |

Só contas ativas com `status_conta = aprovado` acessam. Para proteger uma rota da API, use
`apps.auth.decorators.jwt_obrigatorio`. A validade dos tokens é configurada em `.env.example`.

**Revogação:** cada token tem um `jti`; sair da conta (página ou `/auth/token/revogar/`) grava o `jti` em
`TokenRevogado`, e tokens revogados deixam de valer mesmo antes de expirar (`limpar_auth` apaga os vencidos).
**Força bruta:** 5 senhas erradas por e-mail ou 20 por IP em 15 minutos bloqueiam novos logins (HTTP 429),
na página e na API; um login correto zera as falhas do e-mail. Atrás de proxy, defina `DJANGO_PROXY_IP_HEADER`
para o limite por IP enxergar o cliente real.

---

## 📝 Pendências

Estado em 28/10/2026. O branch `refactor/arquitetura-apps` já foi mergeado (PR #7); as mudanças abaixo estão
**apenas no diretório local, sem commit nem push**.

### Funcionalidades

**Reservas (consumidor e ONG)**
- [x] Botão "Reservar Lote" na vitrine: cria a `Reserva` e muda o lote para `reservado`.
- [x] Expirar reservas vencidas: reserva `ativa` com `data_expiracao` passada vira `expirada` e o lote volta a `disponivel`.
- [x] Doador confirma a retirada (`retirado`) ou registra `nao_retirado`.
- [x] Tela de "minhas reservas" para consumidor e ONG.

**Lotes (doador)**
- [x] Excluir lote (lotes reservados ou retirados são histórico e não podem ser excluídos).
- [x] Foto do lote: upload (`MEDIA_ROOT`/`MEDIA_URL`), validado por tipo e tamanho.
- [x] Marcar como `expirado` os lotes disponíveis cuja validade passou.
- [x] Busca com autocomplete na escolha do alimento (lista com 1038 itens).

**Vitrine**
- [x] Campo "Buscar alimentos...".
- [x] Filtros por categoria e por bairro.
- [ ] Opcional: distância por rota (hoje é em linha reta, pela fórmula de Haversine). Exige um serviço de roteamento externo; ficou fora do MVP.

**Painéis de impacto**
- [x] Números reais dos lotes `retirado`: kg salvos, CO₂ evitado e refeições (kg ÷ 0,4).
- [x] Gráfico "Impacto Ambiental Histórico" e "Ver Relatório Completo".
- [x] Lista de atividades recentes com dados reais.

**Contas e cadastro**
- [x] Cadastro de novos usuários (doador, consumidor e ONG).
- [x] Fluxo de aprovação de contas pelo admin (`pendente` → `aprovado`/`recusado`).
- [x] Cadastro e edição do estabelecimento pelo próprio doador.
- [x] Documento por perfil: CPF para consumidor (PF) e CNPJ para ONG (PJ).
- [x] Geocodificação do endereço/CEP para preencher latitude e longitude automaticamente.
- [x] "Esqueceu a senha?".
- [x] Admin do `Usuario`: troca de senha.

**Escopo original ainda não iniciado:** compra e venda, gamificação para PJ e comissão por venda.

### Técnico

- [x] Branch `refactor/arquitetura-apps`: já mergeado pela PR #7.
- [x] Produção: `DJANGO_DEBUG=False`, `DJANGO_SECRET_KEY` e `DJANGO_ALLOWED_HOSTS` obrigatórios; `collectstatic` ao iniciar; `CSRF_TRUSTED_ORIGINS`; `env_file` no compose.
- [x] `Dockerfile` sem `libpq-dev`/`build-essential` (o banco é SQLite).
- [x] JWT: logout revoga os tokens (lista de revogação).
- [x] Limitar tentativas de login (força bruta).
- [x] Comando `reclassificar_alimentos` para reaplicar `lotes/catalogo.py`.
- [ ] Antes de publicar: servir `/media/` por um servidor web/armazenamento de objetos e configurar SMTP real.

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