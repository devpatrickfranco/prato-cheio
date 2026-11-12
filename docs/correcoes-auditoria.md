# Correções da auditoria

Registro das mudanças aplicadas depois da auditoria de código. A primeira rodada (seções 1 a 6) está no commit
`c14e9f0`, na branch `fix/correcoes-auditoria`. A segunda rodada (seção 7) corrige o que a revisão desse commit
encontrou e ainda está na árvore de trabalho, sem commit.
As alterações que já existiam sem commit em `autocomplete.js`, `localizacao.js` e `cadastro.js` (troca de `var` por `let`)
foram preservadas e as mudanças novas foram feitas por cima.

## 1. Resumo

- **38 itens pedidos: 38 aplicados, 0 pulados, 0 adiados.** Com ressalva, descrita na tabela: 20 (o laço duplicado de mensagens não existia), 25 (Open Graph genérico) e 32 (precisou de um atributo novo no HTML).
- Testes antes: **173 OK**. Depois: **193 OK** (20 testes novos). Todos rodados com `DJANGO_DEBUG=True`.
- Nenhuma migration, model, rota, view, renomeação ou mudança de regra de negócio. `makemigrations --check --dry-run`: "No changes detected".
- Conferência no navegador (Chrome emulando 375 px, banco temporário, `DEBUG=False`): feita para os itens 5, 10, 15, 19, 21–24, 29, 31, 32 e 34 (exceto `localizacao.js`). Ver a coluna Verificação.
- Não verificado de fato: o build do Docker e o `docker compose up` (o Docker está instalado, mas o motor não estava rodando e não o iniciei), o workflow do GitHub Actions (não rodou no GitHub; só os mesmos comandos, localmente) e `localizacao.js` (depende da permissão de geolocalização do navegador).

## 2. Itens

Verificação: **teste novo** = teste de regressão escrito (nos itens [teste] ele falhou antes da correção); **suíte** = só a
suíte existente passando; **manual** = conferido por mim rodando o código ou o navegador; **não verificado** = alterado sem
conseguir exercitar.

| # | Arquivos | O que mudou | Por quê | Verificação |
|---|---|---|---|---|
| 1 | `.dockerignore` | `db.sqlite3media` separado em `db.sqlite3` e `media`. | Eram duas entradas coladas, nenhuma valia. | Manual (leitura). |
| 2 | `config/settings.py`, `docker-compose.yml`, `.env.example`, `README.md` | `DJANGO_DEBUG` passa a `False` por padrão; `env_file` do compose passa a `required: true`; README e `.env.example` explicam que localmente é preciso `DJANGO_DEBUG=True`. | Padrão seguro: esquecer a variável não liga o debug em produção. | Suíte (com a variável) e manual: sem ela o app recusa subir com `ImproperlyConfigured`. |
| 3 | `Dockerfile`, `docker-compose.yml` | gunicorn com `--workers 3 --threads 2 --timeout 30 --access-logfile -`. Os dois comandos eram idênticos, então o `command:` do compose foi removido (o `CMD` do Dockerfile é a única fonte). Removido `PIP_NO_CACHE_DIR=1` (ficou o `--no-cache-dir`). | Evitar duas definições do mesmo comando. | Não verificado (sem build). |
| 4 | `config/settings.py`, `config/urls.py`, `.env.example` | `ADMIN_URL` lida de `DJANGO_ADMIN_URL` (padrão `admin/`), usada em `urls.py`. `.env.example` diz para trocar em produção. | Admin num caminho previsível é alvo de varredura. | Suíte. Busca: nenhum teste, template ou README usa `/admin/` fixo (os testes usam `reverse('admin:...')`). O `robots.txt` cita `/admin/` (o padrão): se o caminho for trocado, ele deixa de cobrir o admin. |
| 5 | `config/settings.py`, `.env.example`, `README.md` | Só com `DEBUG=False`: `SECURE_HSTS_SECONDS` (env `DJANGO_HSTS_SECONDS`, padrão 3600); `SECURE_SSL_REDIRECT` (env `DJANGO_SSL_REDIRECT`, padrão `True`, não mais atrelado a `DJANGO_PROXY_SSL`); CSP nativa do Django 6 em `SECURE_CSP_REPORT_ONLY` liberando `fonts.googleapis.com`, `fonts.gstatic.com` e `style` inline; middleware `ContentSecurityPolicyMiddleware` adicionado. | Resolve security.W004 e W008 e começa a CSP sem risco de quebrar telas. | Manual: `check --deploy` sem W004/W008 (ver seção 6). Navegador com `DEBUG=False`: o cabeçalho `Content-Security-Policy-Report-Only` sai com a política esperada e o console ficou **sem violações** em explorar, relatório, painel do doador (gráfico com style inline), novo lote e meus lotes. O cabeçalho HSTS só aparece em HTTPS; não testado. |
| 6 | `config/settings.py` | `STORAGES` explícito; `CompressedManifestStaticFilesStorage` só com `DEBUG=False`. | Estáticos versionados e comprimidos em produção. | Manual: `collectstatic` em modo produção terminou ("420 post-processed"). A suíte roda com `DEBUG=True`, onde o manifest fica desligado. |
| 7 | `config/settings.py` | `LOGGING` para stdout, raiz em INFO, `django.request` em ERROR. | Logs visíveis no `docker logs`. | Suíte (os avisos aparecem na saída dos testes). |
| 8 | `docker-compose.yml`, `Dockerfile` | `container_name` vira `prato_cheio_app`; comentário do Dockerfile agora diz que `collectstatic` roda na subida, não no build. | Padronização e texto correto. | Não verificado (sem Docker). |
| 9 | `.env.example`, `config/settings.py` | `DJANGO_GEOCODIFICACAO` ficou comentada no `.env.example` e o comentário do settings foi reescrito. | O valor `True` definido contradizia "desligada nos testes": variável definida vale também nos testes. | Manual (leitura da lógica de `_booleano`). |
| 10 | `apps/auth/views.py`, `apps/usuarios/models.py`, `apps/auth/tests.py` | Os dois logins aplicam `.strip().lower()` no e-mail; `UsuarioManager.normalize_email` baixa a caixa toda. Sem migration. | `Joao@X.com` não logava porque o cadastro grava em minúsculas. | **Teste novo** (3 testes; falhavam antes). |
| 11 | `apps/auth/views.py`, `apps/auth/tests.py` | `_dados` devolve `None` se o JSON não for objeto; novo `_texto()` trata e-mail, senha e refresh que não são texto como ausentes. Token: 400; renovar: 401; revogar: 400 (o que cada rota já devolvia para entrada inválida). | Corpo `[]`, `"texto"` ou números derrubava as rotas com 500. | **Teste novo** (4 testes; erravam antes). |
| 12 | `apps/auth/limitador.py`, `apps/auth/tests_seguranca.py` | `ip_do_cliente` usa o **último** valor do cabeçalho e valida com `ipaddress.ip_address`; inválido cai para `REMOTE_ADDR`. O teste antigo do cabeçalho foi ajustado (o IP do cliente agora é o último valor). | O primeiro valor é controlado pelo cliente e burlava o limite por IP. | **Teste novo** (3 testes; 2 falhavam antes, o de IPv6 já passava). |
| 13 | `apps/lotes/management/commands/criar_dados_demo.py`, `apps/lotes/tests.py` | O comando recusa com `CommandError` se `DEBUG=False`, salvo `--forcar`. O teste existente passou a usar `forcar=True`. | Evitar contas aprovadas com senha pública em produção. | **Teste novo** (recusa sem a flag; roda com `DEBUG=True`). |
| 14 | `apps/auth/tokens.py` | Removido o claim `perfil`. | Nada o lia (busca em código e testes). | Suíte. |
| 15 | `apps/lotes/forms.py`, `config/settings.py`, `apps/usuarios/forms.py`, `apps/auth/urls.py`, `senha_redefinir.html`, `cadastro.js` | "Até 5 MB" vem de `FOTO_LOTE_MAX_MB`. Mínimo de senha: nova `SENHA_MIN_CARACTERES = 8` em settings, usada pelo validador, pelo texto de ajuda do cadastro, pelo `extra_context` da página de redefinição e pelo `cadastro.js` (via atributo `minlength` do campo). | Uma só fonte para cada número. | Suíte e manual (o HTML renderizado traz `minlength="8"`). O `8` da pontuação de força da senha no JS é outro critério e foi mantido. |
| 16 | `apps/lotes/models.py` | Docstring cita `0003_catalogo`. | Nome correto da migration. | Manual. |
| 17 | `apps/metricas/views.py` | Descrição do painel do doador: "lotes doados e vendidos". | Existe a modalidade venda. | Suíte. |
| 18 | `templates/components/campo.html`, `apps/usuarios/tests_cadastro.py` | Ajuda com `id="{{ id_for_label }}_helptext"` e erro com `id="..._error"`. Nada no CSS ou JS usava o sufixo `-ajuda`. | O `aria-describedby` gerado pelo Django apontava para ids inexistentes. | **Teste novo** (falhava antes). Limite: o erro escrito pelo JS no navegador não ganha `aria-describedby` (seção 5). |
| 19 | `static/css/style.css` | No bloco `max-width:700px`: a busca deixa de ser escondida e ocupa a largura toda; a barra superior quebra linha (`flex-wrap`). Removida a classe `.mobile-note`. | O filtro ficava ativo sem o usuário ver o campo. | Manual no navegador a 375 px reais: a busca ocupa a largura toda (335 px) numa segunda linha da barra, sem rolagem horizontal. |
| 20 | `apps/auth/templates/jwt_auth/login.html` | `autocomplete="email"` e `autocomplete="current-password"`; o laço de mensagens usa `role="alert"` para erros. | Gerenciadores de senha e leitores de tela. | Teste novo (autocomplete) e suíte. **O laço duplicado não existia**: o arquivo tinha um só (o layout `acesso.html` não tem outro). Removi-o por engano e o restaurei; ficou um. |
| 21 | `templates/layouts/app.html` | Mensagens de erro com `role="alert"`, as demais com `role="status"`. | Leitores de tela anunciam erros com urgência. | Suíte. |
| 22 | `templates/components/sidebar.html` | `aria-current="page"` no link ativo. | Acessibilidade da navegação. | **Teste novo**. |
| 23 | `templates/layouts/app.html`, `templates/layouts/acesso.html`, `static/css/style.css` | Link "Pular para o conteúdo" como primeiro elemento, visível só com foco, para `id="conteudo"` no `<main>`. | Navegação por teclado. | **Teste novo** (marcação). Navegador: o link vai a `top: 0` com foco e `aria-current` marca "Explorar Lotes". |
| 24 | `apps/lotes/templates/lotes/explorar.html` | Imagens com `alt=""`, `loading="lazy"`, `width="400" height="190"`; "15 kg" com espaço. | O título já está ao lado; menos deslocamento de layout. | Suíte. |
| 25 | `templates/base.html`, `static/img/favicon.svg`, `templates/layouts/app.html` | Favicon SVG; canonical sem query string (só quando há `request`); metas Open Graph; bloco `robots` preenchido com `noindex, nofollow` nas áreas logadas. | SEO básico e compartilhamento. | **Teste novo** (canonical e noindex). `og:title` e `og:description` são fixos: o Django não permite repetir o bloco `titulo`/`descricao` para reaproveitá-los. |
| 26 | `config/settings.py`, `raiz/robots.txt` | `WHITENOISE_ROOT = raiz/`; `robots.txt` bloqueia `/admin/`, `/auth/`, `/senha/`, `/dashboard/`, `/relatorio/`, `/explore/`, `/minhas-reservas/`, `/meus-lotes/`, `/meu-estabelecimento/`. | Sem rota nova. | **Teste novo** (GET `/robots.txt`). |
| 27 | `static/css/style.css`, `templates/base.html` | `@import` das fontes saiu do CSS; `preconnect` e `stylesheet` no `<head>`. | O `@import` atrasa a renderização. | Suíte; `collectstatic` ok. |
| 28 | `static/css/style.css` | Removidas `.chart-placeholder`, `.mobile-note`, `.icon`, `.filtro-distancia` e `.mensagem-info` (nenhuma aparece em templates, JS ou Python); a segunda definição, `.field select,.field input[type=file],.field textarea{font:inherit}`, ficou sem `select` (repetia a primeira); `th` com `#5f6a62` (5,05:1 sobre `#f1f3f0`, antes 4,42:1). | Código morto e contraste. | Manual (buscas e cálculo do contraste). Se algum dia houver `messages.info`, faltará estilo; hoje o código usa só success/error. |
| 29 | `apps/metricas/templates/metricas/relatorio.html`, `static/css/style.css` | Cartão "Refeições estimadas" (`total.refeicoes` já estava no contexto); grade `.metrics-auto` para os quatro cartões não deixarem um órfão. | A tabela abaixo já mostrava o dado. | Navegador: quatro cartões (incluindo "Refeições estimadas"), sem rolagem horizontal a 375 px; cor do `th` computada `rgb(95,106,98)`. |
| 30 | `templates/404.html`, `500.html`, `403_csrf.html`, `static/css/style.css` | Páginas em português com a marca. O `500.html` é HTML autônomo com `<style>` embutido, sem contexto nem `{% static %}`. | O erro 500 não pode falhar de novo ao renderizar. | **Teste novo** (404, falha de CSRF e renderização do 500 sem contexto). |
| 31 | `cadastro.js`, `cadastro.html` | Botão "Criar conta" sempre habilitado; o submit barra o envio, mostra os erros e foca o primeiro campo inválido. Removido `data-enviar`. | O trecho de foco do submit nunca rodava. | Manual no navegador: formulário quase vazio + clique mostrou a lista de erros e focou o primeiro campo. |
| 32 | `cadastro.js`, `apps/usuarios/forms.py` | O campo documento valida 11 dígitos (CPF) ou 14 (CNPJ) conforme o perfil. **O HTML não trazia essa informação**, então o form agora põe `data-documento="cpf"`/`"cnpj"` no campo. | O servidor exige CPF para consumidor e CNPJ para ONG. | Manual no navegador (ONG com 11 dígitos: "O CNPJ tem 14 dígitos"). |
| 33 | `cadastro.js` | Removida a leitura de `data-obrigatorio`. | Nenhum template o define. | Manual (busca). |
| 34 | `menu.js`, `calendario.js`, `modalidade.js`, `localizacao.js`, `confirmar.js` | `var` virou `let`/`const`; os dois últimos ganharam IIFE com `'use strict'`. | Padronização, sem mudança de comportamento. | `node --check` em todos os JS e navegador: menu abre/fecha (foco em "Fechar", Esc devolve o foco ao botão), calendário seleciona dias e muda de mês, preço some em doação, `confirmar.js` cancela o envio. `localizacao.js` não foi exercitado. |
| 35 | `README.md`, `docs/escopo.md` | Título "Prato Cheio" com "PAGAFARRA" logo abaixo; pendências atualizadas (PRs #10 e #11, data 12/11/2026); venda fora da lista do que não começou; `menu.js`, `campo.html` e `raiz/` na árvore; anotações de escopo movidas para `docs/escopo.md`; linha solta de credenciais removida (as contas demo seguem documentadas na seção de dados de demonstração). Também atualizados: execução local, variáveis de produção, botão de cadastro. | Documentação fiel ao código. | Manual (leitura). |
| 36 | `docs/adr/0003-geocodificacao-e-fotos.md` | Diz que o CEP do consumidor/ONG também vai ao Nominatim; frase sobre `foto_url` removida. | Correção factual. | Manual. |
| 37 | `docs/adr/0002-revogacao-jwt-e-limite-de-login.md` | Descreve o último valor do cabeçalho, a validação de IP e a premissa de um único proxy confiável. | Alinhar ao item 12. | Manual. |
| 38 | `.github/workflows/ci.yml` | Python 3.13, `pip install`, `manage.py test` com `DJANGO_DEBUG=True` e `check --deploy` com `DJANGO_DEBUG=False`, chave, hosts e `DJANGO_EMAIL_HOST` fictícios. | CI automática. | Os mesmos comandos rodaram localmente; o workflow não rodou no GitHub. |

## 3. Itens pulados

Nenhum.

## 4. O que muda para quem roda o projeto

**Variáveis de ambiente**

| Variável | Mudança |
|---|---|
| `DJANGO_DEBUG` | Padrão agora é `False`. Local, testes e CI precisam de `DJANGO_DEBUG=True` (o `.env.example` já traz). |
| `DJANGO_ADMIN_URL` | Nova, padrão `admin/`. Trocar em produção. |
| `DJANGO_HSTS_SECONDS` | Nova, padrão `3600` (só com `DEBUG=False`). Subir depois de validar o HTTPS. |
| `DJANGO_SSL_REDIRECT` | Nova, padrão `True` (só com `DEBUG=False`). |
| `DJANGO_PROXY_SSL` | Agora **obrigatória** atrás de proxy que termina TLS; antes o redirecionamento só existia com ela. Sem ela, laço de redirecionamento. |
| `DJANGO_PROXY_IP_HEADER` | Passa a usar o último valor do cabeçalho; pressupõe um único proxy confiável. |
| `DJANGO_GEOCODIFICACAO` | Comentada no `.env.example`; se for definida, vale também nos testes. |

**Passos do README que mudaram:** criar o `.env` a partir do `.env.example` antes do `docker compose up` (o arquivo agora é obrigatório);
definir `DJANGO_DEBUG=True` na execução local e nos testes; `criar_dados_demo` só roda com `DEBUG=True` ou com `--forcar`.

**Outras mudanças de comportamento:** o container se chama `prato_cheio_app`; o gunicorn sobe com 3 workers e 2 threads;
com `DEBUG=False` os estáticos exigem `collectstatic` (o Dockerfile já o executa na subida).

**Contas com maiúsculas no e-mail.** O cadastro já gravava em minúsculas, então só ficam de fora contas criadas por outros
caminhos (admin, `createsuperuser`, shell) com maiúsculas. Como o login agora procura em minúsculas, elas **deixam de logar**
até serem regravadas. Não há migration de dados. Para listar e corrigir, no `manage.py shell`:

```python
from django.contrib.auth import get_user_model
U = get_user_model()
for u in U.objects.all():
    if u.email != u.email.lower():
        print(u.pk, u.email)          # conferir
        # u.email = u.email.lower(); u.save(update_fields=['email'])
```

Antes de regravar, confira se não vai colidir com um e-mail já existente em minúsculas.

**CSP ainda em modo só-relatório.** A política está em `SECURE_CSP_REPORT_ONLY` e não bloqueia nada. Próximo passo: com
`DEBUG=False`, navegar pelas telas com o console aberto, procurar violações de "Content-Security-Policy-Report-Only" e,
sem violações, mover o dicionário para `SECURE_CSP`.

**`check --deploy` ainda aponta** `security.W005` (`SECURE_HSTS_INCLUDE_SUBDOMAINS`) e `security.W021` (`SECURE_HSTS_PRELOAD`).
Deixei de fora de propósito: ambos são difíceis de desfazer e dependem de decisão sobre o domínio.

## 5. O que continua aberto

Estrutural (fora do escopo desta rodada):

- Confirmação de retirada depois do fim da janela de retirada.
- Limite de tentativas no login do admin.
- Tokens que sobrevivem à troca de senha.
- Limite em cadastro e recuperação de senha.
- Teto de reservas por usuário.
- Exclusão em cascata do histórico.
- Paginação.
- Tratamento de fotos.
- Geocodificação dentro da transação.

Encontrado no caminho e **não corrigido**:

- O sumário de erros do `cadastro.js` mostra "Nome da instituição:: ..." (dois-pontos duplicados: o rótulo do Django já traz `:` e o JS acrescenta outro).
- O erro escrito pelo JS ao vivo não ganha `aria-describedby` (só o erro renderizado pelo servidor).
- As páginas de acesso (login, recuperação de senha) não têm `noindex`; só as áreas logadas, como pedido.
- O `robots.txt` lista `/admin/` fixo, mesmo com `DJANGO_ADMIN_URL` alterada.
- `og:title` e `og:description` são genéricos.
- O campo `foto_url` do model `Lote` e o código que o lê ainda existem, embora nenhuma tela o exponha (a ADR foi corrigida; remover o campo exigiria migration).
- O console do Chrome registrou um aviso ("form field should have an id or name") em `meus-lotes/novo/`, provavelmente do campo injetado por `autocomplete.js`; não investiguei.

## 6. Verificação final

`python manage.py test` (com `DJANGO_DEBUG=True`):

```
Ran 193 tests in 65.9s
OK
```

`python manage.py check`:

```
System check identified no issues (0 silenced).
```

`python manage.py makemigrations --check --dry-run`:

```
No changes detected
```

`python manage.py check --deploy` com `DJANGO_DEBUG=False`, chave, hosts e `DJANGO_EMAIL_HOST` definidos:

```
WARNINGS:
?: (security.W005) You have not set the SECURE_HSTS_INCLUDE_SUBDOMAINS setting to True. ...
?: (security.W021) You have not set the SECURE_HSTS_PRELOAD setting to True. ...
System check identified 2 issues (0 silenced).
```

`mail.E001`, `security.W004` e `security.W008` sumiram. Sem `DJANGO_EMAIL_HOST`, `mail.E001` volta (por isso o CI define um valor fictício).

## 7. Segunda rodada: correções da revisão

A revisão do commit `c14e9f0` reproduziu os resultados acima e encontrou os pontos abaixo, já corrigidos.
Testes depois desta rodada: **196 OK** (3 novos). `makemigrations --check`: sem mudanças. `check --deploy`: os mesmos
W005 e W021.

| Arquivos | Problema | O que mudou | Verificação |
|---|---|---|---|
| `apps/usuarios/models.py`, `apps/auth/tests.py` | Uma conta criada pelo formulário do admin com maiúsculas no e-mail (`Maria@X.com`) era gravada como digitada e não conseguia mais entrar no site, porque o login passou a procurar em minúsculas. O cadastro ainda a recusava como duplicada. | `Usuario.save()` baixa a caixa e tira espaços do e-mail. Sem migration. | **Teste novo** (reproduzido antes da correção). |
| `apps/auth/limitador.py`, `config/settings.py`, `apps/auth/tests_seguranca.py`, `.env.example`, `README.md`, ADR 0002 | Usar sempre o último valor do cabeçalho só serve com um proxy. Com dois (CDN + nginx), todos os clientes teriam o IP do proxy interno e 20 senhas erradas bloqueariam o login de todos. | Nova `DJANGO_PROXIES_CONFIAVEIS` (padrão 1): o IP do cliente é o N-ésimo valor a partir do fim. Cabeçalho mais curto que N cai para `REMOTE_ADDR`. | **Teste novo** (2 testes). |
| `config/settings.py` | Com `DEBUG=True`, cada mensagem do logger `django` saía duas vezes (handler padrão do Django mais a raiz), e a saída dos testes trazia os avisos da geocodificação. | O logger `django` usa só o handler `console`, sem propagar; nos testes o console fica em silêncio. | Manual: um aviso saía 2 vezes, agora sai 1; saída dos testes limpa. |
| `config/settings.py` | `DJANGO_ADMIN_URL` definida vazia virava `/` e o admin ficava inacessível. | Valor vazio cai no padrão `admin/`. | Manual. |
| `.env.example` | Não dizia como testar o modo produção sem TLS. | Explica `DJANGO_SSL_REDIRECT=False` para `http://localhost` e que fora dele o modo produção exige HTTPS (cookies `Secure`). | Leitura. |
| `README.md` | Linha solta "PAGAFARRA" abaixo do título, repetindo o parágrafo seguinte. | Removida. | Leitura. |

Contas que já estavam gravadas com maiúsculas continuam precisando do ajuste manual descrito na seção 4; o
`save()` só normaliza a partir da próxima gravação.

Segue sem verificação: o build do Docker, o `docker compose up` e a execução do workflow no GitHub.
