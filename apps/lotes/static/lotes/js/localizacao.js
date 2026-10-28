// Preenche lat/lon do formulário com a localização do navegador e reenvia o filtro.
document.querySelectorAll('[data-usar-localizacao]').forEach(function (botao) {
    botao.addEventListener('click', function () {
        if (!navigator.geolocation) {
            alert('Seu navegador não permite obter a localização.');
            return;
        }
        navigator.geolocation.getCurrentPosition(function (posicao) {
            var form = botao.form;
            form.elements.lat.value = posicao.coords.latitude.toFixed(6);
            form.elements.lon.value = posicao.coords.longitude.toFixed(6);
            form.submit();
        }, function () {
            alert('Não foi possível obter sua localização.');
        });
    });
});
