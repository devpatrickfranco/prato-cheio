// Mostra o campo de preço só quando o lote é uma venda.
(function () {
    'use strict';

    const modalidade = document.getElementById('id_modalidade');
    const preco = document.getElementById('id_preco');
    if (!modalidade || !preco) { return; }

    const campo = preco.closest('.field');

    function atualizar() {
        campo.hidden = modalidade.value !== 'venda';
    }

    modalidade.addEventListener('change', atualizar);
    atualizar();
})();
