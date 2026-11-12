// Calendário de seleção múltipla para os dias de retirada do lote.
// O campo de texto continua sendo o enviado ao servidor; o calendário só preenche as datas (AAAA-MM-DD, separadas por vírgula).
(function () {
    'use strict';

    const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'];
    const SEMANA = ['Dom', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'];

    function doisDigitos(numero) {
        return String(numero).padStart(2, '0');
    }

    function iso(ano, mes, dia) {
        return ano + '-' + doisDigitos(mes + 1) + '-' + doisDigitos(dia);
    }

    function curta(data) {
        const partes = data.split('-');
        return partes[2] + '/' + partes[1];
    }

    function criar(tag, classe, texto) {
        const elemento = document.createElement(tag);
        elemento.className = classe;
        if (texto) { elemento.textContent = texto; }
        return elemento;
    }

    document.querySelectorAll('input[data-calendario]').forEach(function (campo) {
        const validade = campo.form.elements.data_validade;
        const agora = new Date();
        const hoje = iso(agora.getFullYear(), agora.getMonth(), agora.getDate());
        let dias = campo.value.split(',').map(function (dia) { return dia.trim(); }).filter(Boolean).sort();
        const inicial = (dias[0] || hoje).split('-');
        let ano = Number(inicial[0]);
        let mes = Number(inicial[1]) - 1;

        const caixa = criar('div', 'calendario');
        const topo = criar('div', 'calendario-topo');
        const anterior = criar('button', 'btn btn-secondary btn-pequeno', 'Anterior');
        const proximo = criar('button', 'btn btn-secondary btn-pequeno', 'Próximo');
        const titulo = criar('strong', 'calendario-mes');
        const grade = criar('div', 'calendario-grade');
        const resumo = criar('small', 'muted');

        anterior.type = 'button';
        proximo.type = 'button';
        titulo.setAttribute('aria-live', 'polite');
        resumo.setAttribute('aria-live', 'polite');
        caixa.setAttribute('role', 'group');
        if (campo.labels.length) {
            campo.labels[0].id = campo.id + '-rotulo';
            caixa.setAttribute('aria-labelledby', campo.labels[0].id);
        }

        function limite() {
            return validade && validade.value ? validade.value : '';
        }

        function disponivel(data) {
            return data >= hoje && (!limite() || data <= limite());
        }

        function sincronizar() {
            dias.sort();
            campo.value = dias.join(',');
            resumo.textContent = dias.length
                ? dias.length + (dias.length === 1 ? ' dia selecionado: ' : ' dias selecionados: ') + dias.map(curta).join(', ')
                : 'Nenhum dia selecionado.';
        }

        function alternar(data, botao) {
            const posicao = dias.indexOf(data);
            if (posicao === -1) {
                dias.push(data);
            } else {
                dias.splice(posicao, 1);
            }
            botao.setAttribute('aria-pressed', posicao === -1 ? 'true' : 'false');
            sincronizar();
        }

        function desenhar() {
            titulo.textContent = MESES[mes] + ' de ' + ano;
            anterior.disabled = iso(ano, mes, 31) < hoje || (ano + '-' + doisDigitos(mes + 1)) === hoje.slice(0, 7);
            proximo.disabled = Boolean(limite()) && (ano + '-' + doisDigitos(mes + 1)) >= limite().slice(0, 7);
            grade.innerHTML = '';
            SEMANA.forEach(function (nome) {
                grade.appendChild(criar('span', 'calendario-semana', nome));
            });
            for (let vazio = new Date(ano, mes, 1).getDay(); vazio > 0; vazio -= 1) {
                grade.appendChild(document.createElement('span'));
            }
            const total = new Date(ano, mes + 1, 0).getDate();
            for (let dia = 1; dia <= total; dia += 1) {
                grade.appendChild(botaoDoDia(dia));
            }
        }

        function botaoDoDia(dia) {
            const data = iso(ano, mes, dia);
            const botao = criar('button', 'calendario-dia', String(dia));
            botao.type = 'button';
            botao.disabled = !disponivel(data);
            botao.setAttribute('aria-pressed', dias.indexOf(data) !== -1 ? 'true' : 'false');
            botao.setAttribute('aria-label', dia + ' de ' + MESES[mes] + ' de ' + ano);
            botao.addEventListener('click', function () { alternar(data, botao); });
            return botao;
        }

        function mudarMes(passo) {
            const alvo = new Date(ano, mes + passo, 1);
            ano = alvo.getFullYear();
            mes = alvo.getMonth();
            desenhar();
        }

        anterior.addEventListener('click', function () { mudarMes(-1); });
        proximo.addEventListener('click', function () { mudarMes(1); });
        if (validade) {
            validade.addEventListener('change', function () {
                dias = dias.filter(disponivel);
                sincronizar();
                desenhar();
            });
        }

        topo.appendChild(anterior);
        topo.appendChild(titulo);
        topo.appendChild(proximo);
        caixa.appendChild(topo);
        caixa.appendChild(grade);
        campo.hidden = true;
        campo.parentNode.insertBefore(caixa, campo);
        campo.parentNode.insertBefore(resumo, campo);
        sincronizar();
        desenhar();
    });
})();
