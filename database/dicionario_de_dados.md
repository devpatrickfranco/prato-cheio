# Dicionário de Dados — Prato Cheio

**Projeto Integrador** | Bancos de Dados Relacionais + Programação Web
**Grupo PAGAFARRA** — Turma 102 — PUC-Campinas
**SGBD:** MySQL 8.0 | **Banco:** `prato_cheio`

**Resumo:** 5 tabelas · 45 atributos · 5 relacionamentos

---

## 1. `usuario`

Armazena as credenciais e o perfil de todos os atores do sistema. O campo
`status_conta` sustenta o fluxo de aprovação feito pelo administrador.

| Campo | Tipo | Nulo | Chave | Descrição |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | Não | PK | Identificador do usuário |
| `nome` | VARCHAR(120) | Não | | Nome da pessoa ou da instituição |
| `email` | VARCHAR(150) | Não | UK | E-mail de acesso, único no sistema |
| `senha_hash` | VARCHAR(255) | Não | | Hash da senha; a senha em texto nunca é armazenada |
| `telefone` | VARCHAR(20) | Sim | | Contato para combinar a retirada |
| `tipo_perfil` | ENUM | Não | | `doador`, `receptor` ou `admin` |
| `status_conta` | ENUM | Não | | `pendente`, `aprovado` ou `recusado` |
| `criado_em` | DATETIME | Não | | Data e hora do cadastro |

---

## 2. `estabelecimento`

Dados exclusivos do perfil doador. Mantida separada de `usuario` para evitar
colunas nulas nos perfis receptor e administrador. O `bairro` registrado aqui
é o que alimenta o filtro de localização da vitrine.

| Campo | Tipo | Nulo | Chave | Descrição |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | Não | PK | Identificador do estabelecimento |
| `usuario_id` | INT | Não | FK, UK | Usuário proprietário; único, garantindo a relação 1:1 |
| `razao_social` | VARCHAR(150) | Não | | Razão social registrada |
| `cnpj` | CHAR(14) | Não | UK | CNPJ sem pontuação |
| `tipo_estabelecimento` | ENUM | Não | | `mercado`, `padaria`, `hortifruti`, `restaurante` ou `outro` |
| `cep` | CHAR(8) | Não | | CEP sem hífen |
| `logradouro` | VARCHAR(150) | Não | | Nome da rua ou avenida |
| `numero` | VARCHAR(10) | Não | | Número do endereço |
| `bairro` | VARCHAR(80) | Não | | Bairro; usado no filtro de proximidade |
| `cidade` | VARCHAR(80) | Não | | Município |
| `uf` | CHAR(2) | Não | | Unidade federativa |

---

## 3. `categoria`

Classifica os alimentos e armazena o fator de conversão usado no cálculo de
emissões evitadas. Foi modelada como tabela, e não como tipo enumerado, para
que o fator possa ser atualizado sem alteração no código da aplicação.

| Campo | Tipo | Nulo | Chave | Descrição |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | Não | PK | Identificador da categoria |
| `nome` | VARCHAR(60) | Não | UK | Nome da categoria |
| `descricao` | VARCHAR(200) | Sim | | Exemplos de itens que pertencem à categoria |
| `fator_co2_kg` | DECIMAL(6,2) | Não | | Quilos de CO₂ equivalente evitados por quilo de alimento aproveitado |

---

## 4. `lote`

Registra o excedente publicado pelo estabelecimento. Os campos `quantidade` e
`unidade` servem à exibição na vitrine; `peso_kg` é o valor canônico utilizado
pelos indicadores de impacto, necessário porque lotes medidos em unidades não
permitem cálculo direto de massa.

| Campo | Tipo | Nulo | Chave | Descrição |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | Não | PK | Identificador do lote |
| `estabelecimento_id` | INT | Não | FK | Estabelecimento que publicou o lote |
| `categoria_id` | INT | Não | FK | Categoria do alimento |
| `descricao` | VARCHAR(200) | Não | | Descrição do conteúdo do lote |
| `quantidade` | DECIMAL(8,2) | Não | | Quantidade na unidade informada |
| `unidade` | ENUM | Não | | `kg` ou `un` |
| `peso_kg` | DECIMAL(8,2) | Não | | Peso total em quilos, base do cálculo de impacto |
| `data_validade` | DATE | Não | | Data de validade do alimento |
| `retirada_inicio` | DATETIME | Não | | Início da janela de retirada |
| `retirada_fim` | DATETIME | Não | | Fim da janela de retirada |
| `foto_url` | VARCHAR(255) | Sim | | Caminho da imagem do lote |
| `status` | ENUM | Não | | `disponivel`, `reservado`, `retirado`, `nao_retirado` ou `expirado` |
| `criado_em` | DATETIME | Não | | Data e hora da publicação |

---

## 5. `reserva`

Vincula um receptor a um lote. O campo `ativa` é uma coluna gerada pelo próprio
banco e não recebe valor digitado: assume 1 quando a reserva está ativa e nulo
nos demais casos. Combinada ao índice único sobre `(lote_id, ativa)`, ela impede
fisicamente que dois receptores mantenham reservas ativas do mesmo lote.

| Campo | Tipo | Nulo | Chave | Descrição |
|---|---|---|---|---|
| `id` | INT AUTO_INCREMENT | Não | PK | Identificador da reserva |
| `lote_id` | INT | Não | FK | Lote reservado |
| `usuario_id` | INT | Não | FK | Receptor que efetuou a reserva |
| `status` | ENUM | Não | | `ativa`, `confirmada`, `expirada` ou `cancelada` |
| `data_reserva` | DATETIME | Não | | Momento em que a reserva foi feita |
| `data_expiracao` | DATETIME | Não | | Limite para a retirada; após esse instante o lote é liberado |
| `data_confirmacao` | DATETIME | Sim | | Momento em que o doador confirmou a retirada |
| `observacao` | VARCHAR(200) | Sim | | Anotação livre do receptor |
| `ativa` | TINYINT (gerada) | Sim | UK | Coluna calculada pelo banco; sustenta a unicidade da reserva ativa |

---

## Relacionamentos

| Origem | Destino | Cardinalidade | Ação ao excluir | Leitura |
|---|---|---|---|---|
| `usuario` | `estabelecimento` | 1:1 | CASCADE | Cada doador possui um único estabelecimento |
| `estabelecimento` | `lote` | 1:N | CASCADE | Um estabelecimento publica vários lotes |
| `categoria` | `lote` | 1:N | RESTRICT | Uma categoria classifica vários lotes |
| `lote` | `reserva` | 1:N | CASCADE | Um lote acumula histórico de reservas, mas apenas uma ativa |
| `usuario` | `reserva` | 1:N | RESTRICT | Um receptor realiza várias reservas |

A exclusão em cascata aplica-se aos dados que perdem sentido sem o registro
principal. Já `categoria` e `usuario` usam RESTRICT: impedir a remoção de uma
categoria em uso ou de um receptor com histórico preserva a integridade dos
indicadores de impacto.

---

## Restrições de integridade

| Restrição | Tabela | Regra |
|---|---|---|
| `uk_usuario_email` | `usuario` | E-mail não pode se repetir |
| `uk_estab_cnpj` | `estabelecimento` | CNPJ não pode se repetir |
| `uk_estab_usuario` | `estabelecimento` | Garante a relação 1:1 com `usuario` |
| `uk_categoria_nome` | `categoria` | Nome de categoria não pode se repetir |
| `ck_categoria_fator` | `categoria` | Fator de CO₂ deve ser positivo |
| `ck_lote_quantidade` | `lote` | Quantidade deve ser positiva |
| `ck_lote_peso` | `lote` | Peso deve ser positivo |
| `ck_lote_janela` | `lote` | Fim da retirada deve ser posterior ao início |
| `uk_reserva_ativa` | `reserva` | Apenas uma reserva ativa por lote |

---

## Índices

| Índice | Tabela | Colunas | Finalidade |
|---|---|---|---|
| `idx_estab_bairro` | `estabelecimento` | `cidade`, `bairro` | Filtro de localização da vitrine |
| `idx_lote_vitrine` | `lote` | `status`, `data_validade` | Consulta principal da vitrine, ordenada por validade |
| `idx_lote_categoria` | `lote` | `categoria_id` | Filtro por categoria |
| `idx_reserva_usuario` | `reserva` | `usuario_id`, `status` | Listagem das reservas de um receptor |
