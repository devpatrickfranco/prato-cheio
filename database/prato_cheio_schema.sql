-- =====================================================================
-- PRATO CHEIO - Modelo Relacional
-- Projeto Integrador | Bancos de Dados Relacionais + Programacao Web
-- Grupo PAGAFARRA - Turma 102 - PUC-Campinas
-- SGBD: MySQL 8.0
-- =====================================================================

USE prato_cheio;


-- ---------------------------------------------------------------------
-- 1. USUARIO
-- Autenticacao e perfil. status_conta suporta a aprovacao do Admin (F1).
-- ---------------------------------------------------------------------
CREATE TABLE usuario (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    nome            VARCHAR(120)  NOT NULL,
    email           VARCHAR(150)  NOT NULL,
    senha_hash      VARCHAR(255)  NOT NULL,
    telefone        VARCHAR(20),
    tipo_perfil     ENUM('doador','receptor','admin') NOT NULL,
    status_conta    ENUM('pendente','aprovado','recusado')
                    NOT NULL DEFAULT 'pendente',
    criado_em       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT uk_usuario_email UNIQUE (email)
);


-- ---------------------------------------------------------------------
-- 2. ESTABELECIMENTO
-- Dados exclusivos do doador. Relacao 1:1 com usuario.
-- O bairro daqui e o que alimenta o filtro da vitrine (F3).
-- ---------------------------------------------------------------------
CREATE TABLE estabelecimento (
    id                  INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id          INT           NOT NULL,
    razao_social        VARCHAR(150)  NOT NULL,
    cnpj                CHAR(14)      NOT NULL,
    tipo_estabelecimento ENUM('mercado','padaria','hortifruti',
                              'restaurante','outro') NOT NULL,
    cep                 CHAR(8)       NOT NULL,
    logradouro          VARCHAR(150)  NOT NULL,
    numero              VARCHAR(10)   NOT NULL,
    bairro              VARCHAR(80)   NOT NULL,
    cidade              VARCHAR(80)   NOT NULL,
    uf                  CHAR(2)       NOT NULL,

    CONSTRAINT uk_estab_usuario UNIQUE (usuario_id),
    CONSTRAINT uk_estab_cnpj    UNIQUE (cnpj),
    CONSTRAINT fk_estab_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuario(id)
        ON DELETE CASCADE
);

CREATE INDEX idx_estab_bairro ON estabelecimento (cidade, bairro);


-- ---------------------------------------------------------------------
-- 3. CATEGORIA
-- Tabela, e nao ENUM, porque carrega o fator de conversao de CO2.
-- Trocar o fator vira UPDATE, sem alterar codigo da aplicacao.
-- ---------------------------------------------------------------------
CREATE TABLE categoria (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    nome          VARCHAR(60)   NOT NULL,
    descricao     VARCHAR(200),
    fator_co2_kg  DECIMAL(6,2)  NOT NULL DEFAULT 2.50,

    CONSTRAINT uk_categoria_nome UNIQUE (nome),
    CONSTRAINT ck_categoria_fator CHECK (fator_co2_kg > 0)
);


-- ---------------------------------------------------------------------
-- 4. LOTE
-- quantidade + unidade servem para exibicao;
-- peso_kg e o valor canonico usado pelas metricas (F6).
-- ---------------------------------------------------------------------
CREATE TABLE lote (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    estabelecimento_id INT           NOT NULL,
    categoria_id       INT           NOT NULL,
    descricao          VARCHAR(200)  NOT NULL,
    quantidade         DECIMAL(8,2)  NOT NULL,
    unidade            ENUM('kg','un') NOT NULL,
    peso_kg            DECIMAL(8,2)  NOT NULL,
    data_validade      DATE          NOT NULL,
    retirada_inicio    DATETIME      NOT NULL,
    retirada_fim       DATETIME      NOT NULL,
    foto_url           VARCHAR(255),
    status             ENUM('disponivel','reservado','retirado',
                            'nao_retirado','expirado')
                       NOT NULL DEFAULT 'disponivel',
    criado_em          DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_lote_estab FOREIGN KEY (estabelecimento_id)
        REFERENCES estabelecimento(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_lote_categoria FOREIGN KEY (categoria_id)
        REFERENCES categoria(id)
        ON DELETE RESTRICT,

    CONSTRAINT ck_lote_quantidade CHECK (quantidade > 0),
    CONSTRAINT ck_lote_peso       CHECK (peso_kg > 0),
    CONSTRAINT ck_lote_janela     CHECK (retirada_fim > retirada_inicio)
);

-- Indice da consulta principal da vitrine (F3):
-- filtra status + validade e ordena por "vence primeiro, aparece primeiro".
CREATE INDEX idx_lote_vitrine ON lote (status, data_validade);
CREATE INDEX idx_lote_categoria ON lote (categoria_id);


-- ---------------------------------------------------------------------
-- 5. RESERVA
-- Vinculo entre o lote e o receptor (F4/F5).
--
-- REGRA 2 - "um lote so aceita uma reserva ativa por vez":
-- MySQL nao tem indice unico parcial. A coluna gerada 'ativa' vale 1
-- quando a reserva esta ativa e NULL nos demais casos. Como UNIQUE
-- ignora NULLs, o banco permite apenas uma linha ativa por lote.
-- ---------------------------------------------------------------------
CREATE TABLE reserva (
    id                INT AUTO_INCREMENT PRIMARY KEY,
    lote_id           INT       NOT NULL,
    usuario_id        INT       NOT NULL,
    status            ENUM('ativa','confirmada','expirada','cancelada')
                      NOT NULL DEFAULT 'ativa',
    data_reserva      DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    data_expiracao    DATETIME  NOT NULL,
    data_confirmacao  DATETIME  NULL,
    observacao        VARCHAR(200),

    ativa TINYINT GENERATED ALWAYS AS
          (CASE WHEN status = 'ativa' THEN 1 ELSE NULL END) STORED,

    CONSTRAINT uk_reserva_ativa UNIQUE (lote_id, ativa),
    CONSTRAINT fk_reserva_lote FOREIGN KEY (lote_id)
        REFERENCES lote(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_reserva_usuario FOREIGN KEY (usuario_id)
        REFERENCES usuario(id)
        ON DELETE RESTRICT
);

CREATE INDEX idx_reserva_usuario ON reserva (usuario_id, status);


-- =====================================================================
-- CARGA INICIAL DAS CATEGORIAS
-- Fator unico de 2,5 kg CO2e por kg, declarado como estimativa didatica.
-- Substituir por fatores especificos quando houver fonte citavel.
-- =====================================================================
INSERT INTO categoria (nome, descricao, fator_co2_kg) VALUES
  ('Hortifruti',    'Frutas, legumes e verduras',            2.50),
  ('Padaria',       'Paes, bolos e produtos de panificacao', 2.50),
  ('Laticinio',     'Leite, queijos e derivados',            2.50),
  ('Nao pereciveis','Enlatados, graos e industrializados',   2.50),
  ('Pronto',        'Refeicoes prontas e preparadas',        2.50);


-- =====================================================================
-- CONSULTAS DE REFERENCIA
-- =====================================================================

-- F3 - Vitrine: apenas lotes disponiveis e dentro da validade (Regra 1),
-- com filtro por bairro e categoria, ordenados por validade mais proxima.
SELECT
    l.id,
    l.descricao,
    c.nome              AS categoria,
    l.quantidade,
    l.unidade,
    l.data_validade,
    e.razao_social,
    e.bairro
FROM lote l
JOIN estabelecimento e ON e.id = l.estabelecimento_id
JOIN categoria        c ON c.id = l.categoria_id
WHERE l.status = 'disponivel'
  AND l.data_validade >= curdate()
  AND e.bairro = 'Centro'
  AND c.nome   = 'Hortifruti'
ORDER BY l.data_validade ASC;


-- F6 - Painel de impacto geral (Regra 5: so conta lote retirado).
-- Refeicoes estimadas a 0,4 kg por refeicao.
SELECT
    count(*)                              AS lotes_salvos,
    sum(l.peso_kg)                        AS kg_salvos,
    round(sum(l.peso_kg) / 0.4)           AS refeicoes_estimadas,
    round(sum(l.peso_kg * c.fator_co2_kg), 2) AS co2e_evitado_kg
FROM lote l
JOIN categoria c ON c.id = l.categoria_id
WHERE l.status = 'retirado';


-- F6 - Painel por doador.
SELECT
    e.razao_social,
    sum(l.peso_kg)                            AS kg_salvos,
    round(sum(l.peso_kg * c.fator_co2_kg), 2) AS co2e_evitado_kg
FROM lote l
JOIN estabelecimento e ON e.id = l.estabelecimento_id
JOIN categoria        c ON c.id = l.categoria_id
WHERE l.status = 'retirado'
GROUP BY e.id, e.razao_social
ORDER BY kg_salvos DESC;


-- Regra 4 - Reservas vencidas voltam a ficar disponiveis.
-- Rodar periodicamente (rotina agendada ou na carga da vitrine).
UPDATE reserva r
JOIN lote l ON l.id = r.lote_id
SET r.status = 'expirada',
    l.status = 'disponivel'
WHERE r.status = 'ativa'
  AND r.data_expiracao < now();


-- Regra 1 - Lotes que passaram da validade saem da vitrine.
UPDATE lote
SET status = 'expirado'
WHERE status = 'disponivel'
  AND data_validade < curdate();
