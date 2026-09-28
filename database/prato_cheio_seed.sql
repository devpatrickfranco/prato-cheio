-- =====================================================================
-- PRATO CHEIO - Dados de teste (seed)
-- Rodar DEPOIS de prato_cheio_schema.sql
--
-- As senhas sao hashes ficticios, apenas para preencher o campo.
-- Em producao, o hash e gerado pelo back-end (bcrypt).
--
-- As datas usam CURDATE() para o cenario nunca ficar velho.
-- =====================================================================

USE prato_cheio;

-- Limpa dados anteriores mantendo a estrutura e as categorias
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE reserva;
TRUNCATE TABLE lote;
TRUNCATE TABLE estabelecimento;
TRUNCATE TABLE usuario;
SET FOREIGN_KEY_CHECKS = 1;


-- ---------------------------------------------------------------------
-- USUARIOS
-- O usuario 6 fica 'pendente' de proposito, para testar F1/F7.
-- ---------------------------------------------------------------------
INSERT INTO usuario
  (id, nome, email, senha_hash, telefone, tipo_perfil, status_conta) VALUES
  (1, 'Equipe Prato Cheio',        'admin@pratocheio.com.br',
      '$2b$10$hashficticio000000001', '19999990000', 'admin',    'aprovado'),
  (2, 'Hortifruti Bom Preco',      'contato@bompreco.com.br',
      '$2b$10$hashficticio000000002', '19999990002', 'doador',   'aprovado'),
  (3, 'Padaria Pao Nosso',         'contato@paonosso.com.br',
      '$2b$10$hashficticio000000003', '19999990003', 'doador',   'aprovado'),
  (4, 'ONG Mesa Solidaria',        'contato@mesasolidaria.org.br',
      '$2b$10$hashficticio000000004', '19999990004', 'receptor', 'aprovado'),
  (5, 'Cozinha Comunitaria Vila Nova', 'cozinha@vilanova.org.br',
      '$2b$10$hashficticio000000005', '19999990005', 'receptor', 'aprovado'),
  (6, 'Mercado Novo Dia',          'contato@novodia.com.br',
      '$2b$10$hashficticio000000006', '19999990006', 'doador',   'pendente');


-- ---------------------------------------------------------------------
-- ESTABELECIMENTOS
-- Bairros diferentes para testar o filtro da vitrine (F3).
-- ---------------------------------------------------------------------
INSERT INTO estabelecimento
  (id, usuario_id, razao_social, cnpj, tipo_estabelecimento,
   cep, logradouro, numero, bairro, cidade, uf) VALUES
  (1, 2, 'Hortifruti Bom Preco LTDA', '11222333000181', 'hortifruti',
      '13010100', 'Rua Barao de Jaguara',  '850', 'Centro',   'Campinas', 'SP'),
  (2, 3, 'Padaria Pao Nosso ME',      '22333444000172', 'padaria',
      '13025200', 'Rua Coronel Quirino',  '1200', 'Cambui',   'Campinas', 'SP'),
  (3, 6, 'Mercado Novo Dia EIRELI',   '33444555000163', 'mercado',
      '13076000', 'Avenida Julio Diniz',   '430', 'Taquaral', 'Campinas', 'SP');


-- ---------------------------------------------------------------------
-- LOTES
--
-- Lote 1 = o cenario da demo final: 20 kg ja retirados.
-- Lote 3 = unidade 'un', mostrando por que peso_kg existe.
-- Lote 4 = vencido e ainda 'disponivel', para testar a Regra 1.
-- ---------------------------------------------------------------------
INSERT INTO lote
  (id, estabelecimento_id, categoria_id, descricao, quantidade, unidade,
   peso_kg, data_validade, retirada_inicio, retirada_fim, status) VALUES

  -- 1: hortifruti, ja retirado -> alimenta o painel de impacto
  (1, 1, 1, 'Bananas maduras em caixa', 20.00, 'kg', 20.00,
      DATE_ADD(CURDATE(), INTERVAL 1 DAY),
      DATE_ADD(CURDATE(), INTERVAL 1 DAY),
      DATE_ADD(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR,
      'retirado'),

  -- 2: disponivel, aparece na vitrine
  (2, 1, 1, 'Tomates maduros',           8.00, 'kg',  8.00,
      DATE_ADD(CURDATE(), INTERVAL 2 DAY),
      DATE_ADD(CURDATE(), INTERVAL 1 DAY),
      DATE_ADD(CURDATE(), INTERVAL 2 DAY),
      'disponivel'),

  -- 3: 40 unidades de pao pesando 80 g cada = 3,2 kg
  (3, 2, 2, 'Paes frances do dia',      40.00, 'un',  3.20,
      DATE_ADD(CURDATE(), INTERVAL 1 DAY),
      CURDATE() + INTERVAL 18 HOUR,
      CURDATE() + INTERVAL 20 HOUR,
      'reservado'),

  -- 4: venceu ontem e continua 'disponivel' -> alvo da Regra 1
  (4, 2, 2, 'Bolos de fuba',             5.00, 'un',  4.00,
      DATE_SUB(CURDATE(), INTERVAL 1 DAY),
      DATE_SUB(CURDATE(), INTERVAL 2 DAY),
      DATE_SUB(CURDATE(), INTERVAL 1 DAY),
      'disponivel'),

  -- 5: laticinio disponivel em outro bairro
  (5, 1, 3, 'Iogurtes naturais',        12.00, 'un',  1.20,
      DATE_ADD(CURDATE(), INTERVAL 3 DAY),
      DATE_ADD(CURDATE(), INTERVAL 1 DAY),
      DATE_ADD(CURDATE(), INTERVAL 3 DAY),
      'disponivel');


-- ---------------------------------------------------------------------
-- RESERVAS
-- ---------------------------------------------------------------------
INSERT INTO reserva
  (id, lote_id, usuario_id, status, data_expiracao, data_confirmacao) VALUES
  -- Reserva do lote 1, ja confirmada: e ela que virou 'retirado'
  (1, 1, 4, 'confirmada',
      DATE_ADD(CURDATE(), INTERVAL 1 DAY) + INTERVAL 8 HOUR,
      DATE_ADD(CURDATE(), INTERVAL 1 DAY) + INTERVAL 7 HOUR),
  -- Reserva ativa do lote 3, ainda aguardando retirada
  (2, 3, 5, 'ativa',
      CURDATE() + INTERVAL 20 HOUR, NULL);


-- =====================================================================
-- TESTES DE VALIDACAO
-- Rode um de cada vez e compare com o resultado esperado.
-- =====================================================================

-- TESTE A - Painel de impacto (F6)
-- Esperado: 1 lote, 20.00 kg, 50 refeicoes, 50.00 kg de CO2e.
-- Sao exatamente os numeros da demo final do grupo.
SELECT
    COUNT(*)                                  AS lotes_salvos,
    SUM(l.peso_kg)                            AS kg_salvos,
    ROUND(SUM(l.peso_kg) / 0.4)               AS refeicoes_estimadas,
    ROUND(SUM(l.peso_kg * c.fator_co2_kg), 2) AS co2e_evitado_kg
FROM lote l
JOIN categoria c ON c.id = l.categoria_id
WHERE l.status = 'retirado';


-- TESTE B - Vitrine (F3 + Regra 1)
-- Esperado: 3 linhas (lotes 2, 5 e o 3 se estivesse disponivel nao entra
-- por estar reservado). O lote 4 NAO pode aparecer: venceu ontem.
SELECT
    l.id, l.descricao, c.nome AS categoria,
    l.quantidade, l.unidade, l.data_validade,
    e.razao_social, e.bairro
FROM lote l
JOIN estabelecimento e ON e.id = l.estabelecimento_id
JOIN categoria        c ON c.id = l.categoria_id
WHERE l.status = 'disponivel'
  AND l.data_validade >= CURDATE()
ORDER BY l.data_validade ASC;


-- TESTE C - Regra 2: um lote so aceita uma reserva ativa por vez.
-- O lote 3 ja tem a reserva 2 ativa. Este INSERT DEVE FALHAR com
-- "Duplicate entry" na chave uk_reserva_ativa.
-- Se ele passar, o indice unico nao esta protegendo a regra.
INSERT INTO reserva (lote_id, usuario_id, status, data_expiracao)
VALUES (3, 4, 'ativa', CURDATE() + INTERVAL 20 HOUR);


-- TESTE D - Regra 1: expirar lotes vencidos.
-- Esperado: 1 row affected (o lote 4).
-- Rode o TESTE B de novo depois: o resultado nao muda,
-- porque a consulta ja filtrava por data.
UPDATE lote
SET status = 'expirado'
WHERE status = 'disponivel'
  AND data_validade < CURDATE();
