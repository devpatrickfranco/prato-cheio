// Mostra o campo de preço só quando o lote é uma venda.
(function () {
    'use strict';

    var modalidade = document.getElementById('id_modalidade');
    var preco = document.getElementById('id_preco');
    if (!modalidade || !preco) { return; }

    var campo = preco.closest('.field');

    function atualizar() {
        campo.hidden = modalidade.value !== 'venda';
    }

    modalidade.addEventListener('change', atualizar);
    atualizar();
})();
