# Relatório de Extensão — Prato Cheio (conteúdo para colar no modelo)

Legenda: **[CONFIRMAR]** = dado que só o grupo sabe; não foi inventado.
Cobre as partes vermelhas (Parcial 1) e verdes (Parcial 2). As partes roxas (resultados, impactos, reflexão, declaração) dependem do projeto concluído e estão no fim, como esqueleto.

Correção no modelo: o rodapé da página 1 diz "1º semestre/2027"; o correto é "2º semestre/2026".

---

## 2. Identificação da comunidade externa / parceiro

**2.1 Nome:** [CONFIRMAR: nome do(s) parceiro(s) reais, por exemplo a padaria/mercado e a ONG consultados]. Se ainda não houver parceiro fechado, escrever: "Comerciantes do setor de alimentos (mercados, padarias e hortifrutis) e ONGs de distribuição de alimentos da região de Campinas/SP, consultados como usuários-teste da plataforma."

**2.2 Tipo (marcar mais de um, ou "Outra" e especificar):** EMPRESA (comércios doadores) e ORGANIZAÇÃO DA SOCIEDADE CIVIL SEM FINS LUCRATIVOS (ONGs receptoras). O modelo pede uma opção; se só uma for aceita, marcar "Outra" e especificar: "Comércios de alimentos (doadores) e ONGs (receptoras)".

**2.3** Já preenchido. Está adequado.

## 3. Participantes

- 3.1: Docentes 1, Estudantes 5, Técnicos 0 (ou deixar em branco).
- 3.2: [CONFIRMAR: número real] — contar apenas quem interagiu com o grupo (ex.: 2 comerciantes + 1 ONG + usuários-teste).
- 3.3: [CONFIRMAR] — total de pessoas da comunidade externa a envolver/impactar. O público-alvo descrito em 2.3 inclui também as pessoas atendidas pelas ONGs; se for estimativa, dizer "estimativa".

## 4. Interlocução

**4.1 Marcar** (somente o que de fato ocorreu): levantamento de demandas (entrevistas/questionário) e reunião com representantes. Marcar "apresentação/validação dos resultados" apenas se houver devolutiva programada ou feita. **[CONFIRMAR]**

**4.2 Texto-base:**
> A interlocução ocorreu em três momentos. No planejamento (agosto/2026), o grupo conversou com [CONFIRMAR: perfis ouvidos, ex.: responsável por uma padaria e por uma ONG] para entender como o excedente de alimentos é hoje descartado ou doado, quais informações precisam constar em um anúncio de lote (descrição, quantidade, validade, janela de retirada) e como as ONGs combinam a retirada. No desenvolvimento (setembro/2026), o protótipo navegável das telas (seleção de perfil, login, explorar lotes, meus lotes e painel de impacto) foi apresentado a [CONFIRMAR] para coletar ajustes. Na avaliação (até o encerramento do semestre), está prevista a validação do sistema com os mesmos participantes, com devolutiva dos resultados.

## 5. Atividades

Já marcada: "Desenvolvimento de material, produto, processo ou tecnologia em resposta às demandas externas". Adequada.

## 6. Descrição e objetivos

**6.1 Descrição:**
> O desperdício de alimentos próximos da validade é recorrente em mercados, padarias e hortifrutis, enquanto ONGs e famílias em insegurança alimentar têm dificuldade de acesso a alimentos. O Prato Cheio é uma plataforma web que conecta esses comércios (doadores) a ONGs e consumidores (receptores): o comércio publica o lote excedente com descrição, quantidade, validade e janela de retirada; o receptor busca os lotes disponíveis por bairro e categoria e reserva um deles; o doador confirma a retirada. A atividade foi desenvolvida em etapas: (1) levantamento de requisitos e definição do escopo (perfis, categorias, regras de negócio); (2) modelagem do banco de dados relacional no MySQL 8.0 — modelo entidade-relacionamento, normalização, dicionário de dados e script SQL; (3) prototipação das telas em HTML/CSS; (4) desenvolvimento do back-end em Django, com conexão ao banco e as operações de cadastro, vitrine, reserva e painel de impacto; (5) validação com a comunidade parceira. A plataforma também calcula indicadores de impacto (quilos de alimento aproveitados, refeições estimadas e CO₂ equivalente evitado) para dar visibilidade ao resultado.

**6.2 Objetivos (até 5):**
1. Desenvolver uma plataforma web que conecte comércios de alimentos a ONGs e consumidores para destinar excedentes próximos da validade.
2. Modelar e implementar um banco de dados relacional normalizado que garanta a integridade das reservas (uma reserva ativa por lote).
3. Reduzir o desperdício de alimentos ao facilitar a doação e a retirada dentro da validade.
4. Mensurar o impacto das doações por meio de indicadores de quilos aproveitados, refeições e CO₂ evitado.
5. Validar a solução com a comunidade externa, incorporando suas demandas e sugestões.

## 7. Papel no desenvolvimento (roxo; esqueleto para o Relatório Final)

- 7.1: [CONFIRMAR] quais demandas do parceiro viraram requisitos (ex.: janela de retirada, filtro por bairro, aprovação de cadastro pelo administrador).
- 7.2: um parágrafo por estudante, com base no histórico do repositório:
  - **Patrick Rovaron Franco:** estrutura inicial do projeto Django, app core, escopo do projeto, integração de pull requests.
  - **Fabio Barbosa Gonsalez:** páginas HTML/CSS (cadastro, index, telas iniciais) e estrutura de pastas.
  - **Arthur Costa Marques:** integração do protótipo completo aos templates do app usuarios e formatação dos templates.
  - **Gabriel Sorge de Almeida:** [CONFIRMAR — sem commits no repositório até 28/09/2026]
  - **Rafael Gambaro Farjallat:** [CONFIRMAR — sem commits no repositório até 28/09/2026]
  Cada um deve acrescentar o que fez fora do Git (modelagem, MER, entrevistas, documentação).

## 8. Registro de carga horária (cada estudante deve ter ≥ 45 h)

Proposta com as datas reais do repositório; **ajustar as horas à realidade de cada estudante**:

| Data | Atividade | Horas |
|---|---|---|
| 23–27/08/2026 | Definição do tema, escopo e estrutura inicial do projeto (repositório, Django, Docker) | 6 |
| 28/08–03/09/2026 | Levantamento de requisitos, perfis de usuário e documento de escopo | 6 |
| Setembro/2026 | Contato e entrevista com parceiros da comunidade [CONFIRMAR] | 5 |
| Setembro/2026 | Modelagem do banco: MER, normalização e dicionário de dados | 8 |
| Setembro/2026 | Script SQL (tabelas, restrições, índices, consultas de referência) | 5 |
| 28/08–28/09/2026 | Protótipo das telas em HTML/CSS e integração aos templates Django | 8 |
| Outubro/2026 (previsto) | Conexão com o banco e manipulações no back-end | 5 |
| Outubro/2026 (previsto) | Testes e validação com a comunidade externa | 3 |
| **Total** | | **46** |

---

## Evidência 1 — Modelagem dos dados

**Normalização.** O modelo já está na 3FN:
- **1FN:** todos os atributos são atômicos (endereço separado em cep, logradouro, número, bairro, cidade, uf; telefone e e-mail em campos únicos); não há grupos repetitivos, pois os vários lotes e reservas de uma pessoa ficam em tabelas próprias.
- **2FN:** todas as tabelas têm chave primária simples (`id`), então não há dependência parcial.
- **3FN:** não há dependência transitiva. Os dados do estabelecimento (CNPJ, endereço) foram separados de `usuario`, e o nome e o fator de CO₂ da categoria ficam em `categoria`, não repetidos em cada `lote`. Decisão consciente: `peso_kg` coexiste com `quantidade`/`unidade` porque o peso é um dado informado (lotes em unidades não permitem calcular a massa), não derivado.

Etapas, partindo de uma planilha única de lotes (usuário, CNPJ, endereço, categoria, fator de CO₂, lote, reserva): (1) atomizar o endereço; (2) separar lote e reserva (um lote tem várias reservas ao longo do tempo); (3) retirar de `lote` os dados que dependem do estabelecimento e da categoria, criando `estabelecimento` e `categoria`; (4) separar `estabelecimento` de `usuario` para não gerar colunas nulas nos perfis receptor e admin.

**MER (entidades, relacionamentos e cardinalidades mín,máx).** Figura: `database/der_prato_cheio.png` (anexar).

| Relacionamento | Lado A | Lado B |
|---|---|---|
| usuario **possui** estabelecimento | usuario (0,1) | estabelecimento (1,1) |
| estabelecimento **publica** lote | estabelecimento (0,N) | lote (1,1) |
| categoria **classifica** lote | categoria (0,N) | lote (1,1) |
| usuario **realiza** reserva | usuario (0,N) | reserva (1,1) |
| lote **recebe** reserva | lote (0,N) | reserva (1,1) |

Observação: um lote tem histórico de várias reservas, mas só uma ativa por vez (índice único sobre `lote_id` + coluna gerada `ativa`).

Atributos: ver `database/dicionario_de_dados.md` (5 tabelas, 45 atributos).

**SQL de criação:** anexar `database/prato_cheio_schema.sql`. O script atual não tem `CREATE DATABASE`; acrescentar no topo:
```sql
CREATE DATABASE IF NOT EXISTS prato_cheio CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE prato_cheio;
```

## Evidência 2 — Repositório

Link: https://github.com/devpatrickfranco/prato-cheio (repositório principal). Parcial 2: descrever a conexão com o MySQL e as manipulações no back-end (hoje o `models.py` do Django ainda está vazio e o projeto usa SQLite; falta apontar para o MySQL e mapear as 5 tabelas).

## Evidência 3 — Declaração de participação (roxo)
Anexar a declaração assinada eletronicamente pelo parceiro. **[CONFIRMAR]**

## Evidência 4 — Apresentação (roxo)
Link público da apresentação. Capturas das telas já existem em `docs/screenshots-prototipo/` (01 a 05) e podem ilustrar o relatório.

---

## Partes roxas (Relatório Final) — esqueleto

- **9.1 Resultados:** plataforma web Prato Cheio; banco relacional normalizado (5 tabelas) com dicionário de dados; protótipo de 5 telas; painel de impacto (kg, refeições, CO₂).
- **9.2 Impactos:** só com evidências reais (falas dos parceiros, número de lotes cadastrados em teste, quilos). Não escrever números sem medição.
- **10 Reflexão:** relacionar com a disciplina (modelagem, normalização, integridade com restrições e índices, consultas SQL), formação cidadã (insegurança alimentar), dificuldades (conciliar o escopo, tradução do modelo para o Django, contato com parceiros) e melhorias (testes automatizados, notificações, geolocalização).
