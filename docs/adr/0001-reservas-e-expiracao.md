# ADR 0001 — Ciclo de vida de reservas e expiração sem processo em segundo plano

- **Data:** 28/10/2026
- **Status:** aceita

## Contexto
Um lote reservado precisa voltar à vitrine se ninguém retirar, e lotes vencidos não podem aparecer como
disponíveis. O projeto roda em um único container (gunicorn + SQLite), sem fila de tarefas nem agendador.

## Alternativas
1. Celery/RQ com agendador: exige Redis/broker, mais infraestrutura que o MVP justifica.
2. Somente um comando agendado no cron: o estado ficaria desatualizado entre execuções.
3. Regra aplicada ao listar (lazy) **mais** comando agendado opcional.

## Decisão
Opção 3. `apps/lotes/services.py` concentra as regras (`reservar_lote`, `cancelar_reserva`,
`confirmar_retirada`, `registrar_nao_retirada`, `expirar_reservas`, `expirar_lotes`). A vitrine, "minhas
reservas" e "meus lotes" chamam `atualizar_pendencias()` antes de listar; o comando `atualizar_status` faz o
mesmo e pode ser agendado. A reserva vale até `Lote.retirada_fim`; a vitrine oculta lotes com janela encerrada.
A unicidade de reserva ativa por lote é garantida por `UniqueConstraint` condicional no banco.

## Consequências
- Sem dependência de infraestrutura extra; o estado é consistente sempre que alguém consulta.
- Cada listagem faz duas consultas de manutenção (baratas, com índice). Em escala maior, mover para tarefa agendada.
- Só lotes `retirado` (reserva confirmada pelo doador) entram nas métricas de impacto.
