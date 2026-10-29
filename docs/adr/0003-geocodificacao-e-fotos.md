# ADR 0003 — Geocodificação de endereço e armazenamento de fotos

- **Data:** 28/10/2026
- **Status:** aceita

## Contexto
A vitrine calcula distância (Haversine) a partir de latitude/longitude, que ninguém preenchia manualmente.
Doadores também precisam enviar fotos dos lotes.

## Alternativas
- **Geocodificação:** Google Maps (pago, exige chave), ViaCEP + base própria, Nominatim/OpenStreetMap (gratuito, sem chave).
- **Fotos:** apenas URL externa (já existia `foto_url`), `ImageField` em disco, armazenamento de objetos (S3).

## Decisão
- `apps/usuarios/geocodificacao.py` consulta o Nominatim com `urllib` (sem nova dependência), com timeout de 5 s e
  consultas progressivamente menos específicas (rua → CEP → cidade). Qualquer falha devolve `None` e o cadastro
  prossegue sem coordenadas. Só roda no cadastro e quando o endereço muda. Desligável por `DJANGO_GEOCODIFICACAO`;
  desligada nos testes. Envia apenas o endereço do estabelecimento, nunca dados pessoais.
- Fotos em `ImageField` (Pillow) sob `MEDIA_ROOT`, limitadas a JPG/PNG/WebP até 5 MB; `foto_url` segue como
  alternativa. Servidas por `django.views.static.serve` (suficiente neste porte).

## Consequências
- Dependência de um serviço externo gratuito e com política de uso (uma requisição por vez, User-Agent próprio).
- Endereços não encontrados ficam sem distância; a tela "Meu Estabelecimento" avisa e permite corrigir.
- Em produção com mais tráfego, servir `/media/` por servidor web ou armazenamento de objetos.
