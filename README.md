# Prato Cheio

Plataforma web que conecta estabelecimentos com excedente de alimentos a quem pode
aproveitá-los: ONGs (doação) e consumidores (venda com desconto). Cada retirada
confirmada gera indicadores de impacto: CO₂ evitado, alimentos salvos e refeições.

Projeto Integrador · PUC-Campinas · Grupo PAGAFARRA.

## Stack

- Back-end: Python + Django 6 (Django Templates), autenticação por **JWT**
- Banco: PostgreSQL via Django ORM (SQLite local quando `POSTGRES_DB` não está definido)
- Front-end: HTML5 semântico, CSS e JavaScript escritos à mão, sem frameworks

## Perfis

| Perfil | Papel | Cadastro |
|---|---|---|
| **PJ** (doador) | Publica lotes para doação ou venda, confirma retiradas, vê seu impacto e nível | Aguarda aprovação da equipe |
| **ONG** | Reserva lotes de **doação** | Aguarda aprovação da equipe |
| **PF** (consumidor) | Compra lotes de **venda** | Aprovado na hora |
| **Admin** | Aprova contas e gerencia dados em `/admin/` | `createsuperuser` |

Comissão: cada venda registra a comissão da plataforma (`COMISSAO_PERCENTUAL`, padrão 8%).

## Como executar

### Com Docker

```bash
cp .env.example .env        # defina DJANGO_SECRET_KEY e POSTGRES_PASSWORD
docker compose up -d --build
docker compose exec web python manage.py migrate
docker compose exec web python manage.py seed_demo   # dados de demonstração (opcional)
```

Acesse **http://localhost:8000**.

### Sem Docker (SQLite)

```bash
python -m venv .venv && source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

### Dados de demonstração

`seed_demo` cria usuários de cada perfil (senha padrão `prato-cheio-123`), lotes à venda,
doações, reservas e histórico de retiradas.

| Perfil | E-mail |
|---|---|
| Doador | `contato@bompreco.com.br` |
| ONG | `contato@mesasolidaria.org.br` |
| Consumidor | `joao@exemplo.com.br` |
| Admin | `admin@pratocheio.com.br` |

## Autenticação (JWT)

- O login valida e-mail e senha e grava dois cookies **HttpOnly** (`SameSite=Lax`):
  `access` (15 min) e `refresh` (7 dias). O JavaScript da página não consegue lê-los.
- `usuarios.middleware.JWTAuthMiddleware` lê o cookie, expõe `request.usuario` e renova o
  access token quando só o refresh ainda vale.
- `@jwt_required('pj')` protege as views por perfil. Conta recusada perde o acesso mesmo com token válido.
- O CSRF do Django continua ativo nos formulários POST. O `/admin/` usa a sessão padrão do Django.
- Limite de 5 tentativas de senha por 5 minutos (por perfil, IP e e-mail).

## Estrutura

```
config/      configurações do Django (settings, urls)
core/        base dos templates, CSS, JS e filtros de template compartilhados
usuarios/    Usuario, Estabelecimento, JWT, cadastro e login
produtos/    Categoria, Lote, Reserva, vitrine e regras de reserva
metricas/    painel e relatório de impacto (CO₂, kg, refeições)
database/    DER e dicionário de dados do grupo (o esquema real vem dos models)
docs/        documentação e protótipos
```

## Modelo de dados

Implementado nos models do Django (`usuarios/models.py`, `produtos/models.py`).
Diferenças em relação ao dicionário de dados em `database/`:

- `tipo_perfil` agora é `pf`, `pj`, `ong` ou `admin` (antes: `doador`, `receptor`, `admin`).
- `estabelecimento` também guarda as ONGs (`tipo_estabelecimento = ong`).
- `lote` ganhou `tipo` (doação/venda), `preco` e `foto_validade` (foto do código de barras e da validade).
- `reserva` ganhou `valor` e `comissao`.
- A regra "uma reserva ativa por lote" é a constraint `uk_reserva_ativa` (índice único parcial).

## CO₂

O fator de conversão fica em `Categoria.fator_co2_kg`. Os valores atuais (2,5 kg CO₂e por kg)
são uma estimativa didática. Quando a base de dados de CO₂ (PDF) estiver pronta, basta
atualizar os fatores no admin ou em uma nova migração de dados; as telas recalculam sozinhas.

## Testes

```bash
python manage.py test
```

## Regras de Git

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

## Escopo

- **Usuários:** PJ (compra, venda e gamificação), PF (compra), ONG (recebe doação), localização por bairro
- **Produto:** categorias, cadastro, venda, doação, compra, retirada, prazo de vencimento,
  garantia de qualidade (foto do código de barras e da validade), imagens, descrição, quantidade e unidade
- **Métricas:** CO₂ evitado e kg não desperdiçados
- **Modelo de negócio:** comissão por venda
- **Metodologia:** Scrum e Kanban
