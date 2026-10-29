# ADR 0002 — Revogação de tokens JWT e limite de tentativas de login

- **Data:** 28/10/2026
- **Status:** aceita

## Contexto
O logout apenas apagava os cookies: um token copiado continuava válido até expirar (15 min o access, 7 dias o
refresh). Além disso, nada impedia tentativas ilimitadas de senha.

## Alternativas
- **Revogação:** (a) tokens apenas de vida curta; (b) sessões no servidor; (c) lista de revogação por `jti`.
- **Limite de tentativas:** (a) cache em memória; (b) biblioteca externa (django-axes); (c) tabela própria.

## Decisão
- Todo token recebe um `jti`; o logout grava o `jti` em `TokenRevogado` e `decodificar()` recusa tokens
  revogados. Mantém o modelo stateless para quem só usa o access e custa uma consulta indexada por requisição.
- Cada senha errada grava uma `TentativaLogin`. Cinco falhas por e-mail ou vinte por IP em 15 minutos bloqueiam
  (HTTP 429) na página e na API. O cache em memória não serve: o estado se perde a cada worker/restart.
- `limpar_auth` remove registros vencidos. `DJANGO_PROXY_IP_HEADER` informa o IP real atrás de proxy (por padrão
  usa `REMOTE_ADDR`, para que `X-Forwarded-For` forjado não burle o limite).

## Consequências
- Logout efetivo imediatamente; reaproveitar cookies antigos não restaura a sessão.
- O bloqueio por e-mail permite que um atacante trave a conta da vítima por 15 minutos (trade-off aceito; o
  limite por IP e a janela curta reduzem o impacto).
- Trocar a senha ainda não revoga tokens já emitidos (melhoria futura: versão de senha no token).
