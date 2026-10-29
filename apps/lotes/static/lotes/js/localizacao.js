// Preenche lat/lon do formulário com a localização do navegador e reenvia o filtro.
document.querySelectorAll('[data-usar-localizacao]').forEach(function (botao) {
    var form = botao.form;
    var status = form.querySelector('[data-localizacao-status]');

    function avisar(texto) {
        if (status) {
            status.textContent = texto;
        }
    }

    botao.addEventListener('click', function () {
        if (!navigator.geolocation) {
            avisar('Seu navegador não permite obter a localização.');
            return;
        }
        avisar('Obtendo sua localização...');
        navigator.geolocation.getCurrentPosition(function (posicao) {
            form.elements.lat.value = posicao.coords.latitude.toFixed(6);
            form.elements.lon.value = posicao.coords.longitude.toFixed(6);
            form.submit();
        }, function () {
            avisar('Não foi possível obter sua localização. Verifique a permissão do navegador.');
        });
    });
});
