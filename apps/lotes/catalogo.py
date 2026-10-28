"""Classificação dos alimentos do CSV de pegadas nas categorias de venda.

O item mantém a descrição original (ex.: "arroz integral"); apenas ganha uma
categoria (ex.: "Grãos e cereais"). A regra parte do grupo da fonte e, quando
o grupo não corresponde à prateleira em que o item é vendido, aproxima pelo
nome do item.
"""

CATEGORIAS = {
    'Hortifruti': 'Frutas, legumes, verduras, cocos e castanhas',
    'Grãos e cereais': 'Arroz, feijão, leguminosas, farinhas e massas',
    'Padaria': 'Pães, bolos, biscoitos e produtos de panificação',
    'Laticínio': 'Leite, queijos, iogurtes e derivados',
    'Carnes e aves': 'Carnes bovina, suína, caprina, de aves e industrializadas',
    'Ovos': 'Ovos de galinha e de codorna',
    'Pescados': 'Peixes e frutos do mar',
    'Doces': 'Açúcares, doces, chocolates e sobremesas',
    'Bebidas': 'Bebidas, sucos, refrescos, cafés e chás',
    'Não perecíveis': 'Enlatados, conservas, condimentos, óleos e gorduras',
    'Pronto': 'Refeições, lanches e pratos preparados',
}

CATEGORIA_POR_GRUPO = {
    'frutas': 'Hortifruti',
    'hortaliças tuberosas': 'Hortifruti',
    'hortaliças folhosas, frutosas e outras': 'Hortifruti',
    'cocos, castanhas e nozes': 'Hortifruti',
    'cereais e leguminosas': 'Grãos e cereais',
    'farinhas, féculas e massas': 'Grãos e cereais',
    'panificados': 'Padaria',
    'laticínios': 'Laticínio',
    'carnes e vísceras': 'Carnes e aves',
    'carnes industrializadas': 'Carnes e aves',
    'aves e ovos': 'Carnes e aves',
    'pescados e frutos do mar': 'Pescados',
    'açúcares e produtos de confeitaria': 'Doces',
    'bebidas alcoólicas': 'Bebidas',
    'bebidas não alcoólicas e infusões': 'Bebidas',
    'enlatados e conservas': 'Não perecíveis',
    'sais e condimentos': 'Não perecíveis',
    'óleos e gorduras': 'Não perecíveis',
    'miscelâneas': 'Pronto',
}

# Aproximações por nome, aplicadas antes da regra do grupo. O grupo de origem
# restringe cada regra para evitar falsos positivos (ex.: "ovo de páscoa" é doce).
_POR_NOME = [
    ('aves e ovos', ('ovo de ',), 'Ovos'),
    ('miscelâneas', ('suco', 'vitamina', 'refresco', 'café'), 'Bebidas'),
    ('miscelâneas', ('chocolate',), 'Doces'),
    ('miscelâneas', ('salada de frutas',), 'Hortifruti'),
    ('miscelâneas', ('costela', 'galeto'), 'Carnes e aves'),
]

# Itens de "miscelâneas" que começam com uma palavra-chave, mas são refeições.
_EXCECOES = {'café da manhã': 'Pronto'}

CATEGORIA_PADRAO = 'Pronto'

# Preparos que representam o alimento como é vendido: cru ou "não se aplica".
PREPAROS_DE_VAREJO = {1, 99}


def categoria_do_alimento(grupo, descricao):
    grupo = grupo.strip().lower()
    nome = descricao.strip().lower()
    if nome in _EXCECOES:
        return _EXCECOES[nome]
    for grupo_regra, prefixos, categoria in _POR_NOME:
        if grupo == grupo_regra and nome.startswith(prefixos):
            return categoria
    return CATEGORIA_POR_GRUPO.get(grupo, CATEGORIA_PADRAO)
