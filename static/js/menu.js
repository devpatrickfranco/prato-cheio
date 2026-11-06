// Abre e fecha a sidebar como aba lateral nas telas em que ela não fica sempre visível.
(function () {
    'use strict';

    var botao = document.querySelector('[data-menu-abrir]');
    var sidebar = document.getElementById('menu-lateral');
    var fundo = document.querySelector('[data-menu-fundo]');
    var fechar = document.querySelector('[data-menu-fechar]');
    var principal = document.querySelector('.main');
    if (!botao || !sidebar || !fundo || !fechar || !principal) { return; }

    var telaPequena = window.matchMedia('(max-width: 700px)');

    function aberto() {
        return sidebar.classList.contains('aberto');
    }

    function alternar(abrir) {
        sidebar.classList.toggle('aberto', abrir);
        document.body.classList.toggle('menu-aberto', abrir);
        botao.setAttribute('aria-expanded', abrir ? 'true' : 'false');
        fundo.hidden = !abrir;
        principal.inert = abrir;
    }

    function abrirMenu() {
        alternar(true);
        fechar.focus();
    }

    function fecharMenu() {
        if (!aberto()) { return; }
        alternar(false);
        botao.focus();
    }

    botao.addEventListener('click', abrirMenu);
    fechar.addEventListener('click', fecharMenu);
    fundo.addEventListener('click', fecharMenu);
    sidebar.addEventListener('click', function (evento) {
        if (evento.target.closest('a')) { fecharMenu(); }
    });
    document.addEventListener('keydown', function (evento) {
        if (evento.key === 'Escape') { fecharMenu(); }
    });
    // Girar o aparelho ou aumentar a janela não pode deixar a página travada com o menu aberto.
    telaPequena.addEventListener('change', function () {
        if (!telaPequena.matches) { alternar(false); }
    });
    // Voltar pelo navegador pode restaurar a página como estava.
    window.addEventListener('pageshow', function () { alternar(false); });
})();
