// Pede confirmação antes de enviar formulários marcados com data-confirmar="mensagem".
document.querySelectorAll('form[data-confirmar]').forEach(function (form) {
    form.addEventListener('submit', function (evento) {
        if (!window.confirm(form.getAttribute('data-confirmar'))) {
            evento.preventDefault();
        }
    });
});
