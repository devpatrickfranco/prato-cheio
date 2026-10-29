// Autocomplete para o <select> de alimento (mais de mil opções).
// O <select> continua sendo o campo enviado ao servidor; o texto digitado só filtra e escolhe a opção.
(function () {
    'use strict';

    var LIMITE = 30;

    function semAcento(texto) {
        return texto.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
    }

    document.querySelectorAll('select[data-autocomplete]').forEach(function (select) {
        var opcoes = Array.prototype.slice.call(select.options)
            .filter(function (opcao) { return opcao.value !== ''; })
            .map(function (opcao) {
                return { valor: opcao.value, texto: opcao.text, grupo: opcao.parentNode.label || '', chave: semAcento(opcao.text) };
            });

        var caixa = document.createElement('input');
        caixa.type = 'search';
        caixa.className = 'search';
        caixa.placeholder = 'Digite para buscar o alimento...';
        caixa.autocomplete = 'off';
        caixa.setAttribute('role', 'combobox');
        caixa.setAttribute('aria-expanded', 'false');
        caixa.setAttribute('aria-controls', select.id + '-lista');
        caixa.setAttribute('aria-autocomplete', 'list');
        caixa.setAttribute('aria-label', 'Buscar alimento');

        var lista = document.createElement('ul');
        lista.id = select.id + '-lista';
        lista.className = 'autocomplete-lista';
        lista.setAttribute('role', 'listbox');
        lista.hidden = true;

        var aviso = document.createElement('small');
        aviso.className = 'muted';
        aviso.setAttribute('aria-live', 'polite');

        var atual = -1;

        function selecionadoTexto() {
            var opcao = select.options[select.selectedIndex];
            return opcao && opcao.value ? opcao.text : '';
        }

        function fechar() {
            lista.hidden = true;
            caixa.setAttribute('aria-expanded', 'false');
            atual = -1;
        }

        function escolher(opcao) {
            select.value = opcao ? opcao.valor : '';
            caixa.value = opcao ? opcao.texto : '';
            aviso.textContent = opcao ? 'Selecionado: ' + opcao.texto : 'Nenhum alimento selecionado.';
            select.dispatchEvent(new Event('change', { bubbles: true }));
            fechar();
        }

        function destacar(indice) {
            var itens = lista.children;
            Array.prototype.forEach.call(itens, function (item, i) {
                item.setAttribute('aria-selected', i === indice ? 'true' : 'false');
            });
            atual = indice;
            if (itens[indice]) {
                itens[indice].scrollIntoView({ block: 'nearest' });
            }
        }

        function mostrar() {
            var termo = semAcento(caixa.value.trim());
            var achados = opcoes.filter(function (opcao) { return !termo || opcao.chave.indexOf(termo) !== -1; });
            lista.innerHTML = '';
            achados.slice(0, LIMITE).forEach(function (opcao) {
                var item = document.createElement('li');
                item.setAttribute('role', 'option');
                item.setAttribute('aria-selected', 'false');
                item.textContent = opcao.texto + (opcao.grupo ? ' — ' + opcao.grupo : '');
                item.addEventListener('mousedown', function (evento) {
                    evento.preventDefault();
                    escolher(opcao);
                });
                lista.appendChild(item);
            });
            if (!achados.length) {
                var vazio = document.createElement('li');
                vazio.className = 'autocomplete-vazio';
                vazio.textContent = 'Nenhum alimento encontrado.';
                lista.appendChild(vazio);
            }
            lista.hidden = false;
            caixa.setAttribute('aria-expanded', 'true');
            atual = -1;
            aviso.textContent = achados.length > LIMITE
                ? 'Mostrando ' + LIMITE + ' de ' + achados.length + ' alimentos. Continue digitando para refinar.'
                : achados.length + ' alimento(s) encontrado(s).';
        }

        caixa.addEventListener('input', function () {
            if (caixa.value.trim() === '') {
                select.value = '';
            }
            mostrar();
        });
        caixa.addEventListener('focus', mostrar);
        caixa.addEventListener('blur', function () {
            fechar();
            caixa.value = selecionadoTexto();
        });
        caixa.addEventListener('keydown', function (evento) {
            var itens = lista.querySelectorAll('[role="option"]');
            if (evento.key === 'ArrowDown') {
                evento.preventDefault();
                if (lista.hidden) { mostrar(); }
                destacar(Math.min(atual + 1, itens.length - 1));
            } else if (evento.key === 'ArrowUp') {
                evento.preventDefault();
                destacar(Math.max(atual - 1, 0));
            } else if (evento.key === 'Enter' && atual >= 0) {
                evento.preventDefault();
                itens[atual].dispatchEvent(new MouseEvent('mousedown'));
            } else if (evento.key === 'Escape') {
                fechar();
            }
        });

        caixa.value = selecionadoTexto();
        select.hidden = true;
        select.parentNode.insertBefore(caixa, select);
        select.parentNode.insertBefore(lista, select);
        select.parentNode.insertBefore(aviso, select.nextSibling);
    });
})();
