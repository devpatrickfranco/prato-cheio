// Validação em tempo real do cadastro (melhoria progressiva: o servidor valida de novo).
// Eventos usados: input (contador e força da senha), blur (validação do campo),
// change (revalida) e submit (validação final). O botão só habilita com tudo válido.
(function () {
    'use strict';

    var form = document.querySelector('form[data-validar]');
    if (!form) {
        return;
    }

    var botao = form.querySelector('[data-enviar]');
    var resumo = document.querySelector('[data-resumo-erros]');
    var campos = Array.prototype.slice.call(form.querySelectorAll('input, select, textarea'))
        .filter(function (campo) { return campo.type !== 'hidden'; });
    var tocados = {};
    var EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

    function rotulo(campo) {
        var label = form.querySelector('label[for="' + campo.id + '"]');
        return label ? label.textContent.trim() : campo.name;
    }

    function digitos(valor) {
        return valor.replace(/\D/g, '');
    }

    // Devolve a mensagem de erro do campo, ou '' quando ele está válido.
    function validar(campo) {
        var valor = campo.value.trim();
        var nome = campo.name;
        if (!valor) {
            return campo.required || campo.hasAttribute('data-obrigatorio') ? 'Preencha este campo.' : '';
        }
        if (campo.type === 'email' && !EMAIL.test(valor)) {
            return 'Informe um e-mail válido, como nome@dominio.com.';
        }
        if (nome === 'senha' && campo.value.length < 8) {
            return 'A senha precisa de pelo menos 8 caracteres.';
        }
        if (nome === 'confirmar_senha') {
            var senha = form.elements.senha;
            if (senha && campo.value !== senha.value) {
                return 'As senhas não conferem.';
            }
        }
        if (nome === 'documento') {
            var tamanho = digitos(valor).length;
            if (tamanho !== 11 && tamanho !== 14) {
                return 'Informe o CPF (11 dígitos) ou CNPJ (14 dígitos).';
            }
        }
        if (nome === 'cnpj' && digitos(valor).length !== 14) {
            return 'O CNPJ tem 14 dígitos.';
        }
        if (nome === 'cep' && digitos(valor).length !== 8) {
            return 'O CEP tem 8 dígitos.';
        }
        if (nome === 'uf' && !/^[A-Za-z]{2}$/.test(valor)) {
            return 'Informe a sigla do estado com 2 letras.';
        }
        return '';
    }

    function mostrarErro(campo, mensagem) {
        var area = form.querySelector('[data-erro-de="' + campo.id + '"]');
        if (area) {
            area.textContent = mensagem;
        }
        campo.classList.toggle('erro', Boolean(mensagem));
        campo.classList.toggle('ok', !mensagem && campo.value.trim() !== '');
        if (mensagem) {
            campo.setAttribute('aria-invalid', 'true');
        } else {
            campo.removeAttribute('aria-invalid');
        }
    }

    // Sumário de erros: lista os campos pendentes depois que o usuário interagiu com o formulário.
    function atualizarResumo() {
        if (!resumo) {
            return;
        }
        var pendentes = campos.filter(function (campo) { return tocados[campo.id] && validar(campo); });
        resumo.innerHTML = '';
        resumo.hidden = pendentes.length === 0;
        if (!pendentes.length) {
            return;
        }
        var titulo = document.createElement('strong');
        titulo.textContent = 'Corrija para continuar:';
        var lista = document.createElement('ul');
        pendentes.forEach(function (campo) {
            var item = document.createElement('li');
            var link = document.createElement('a');
            link.href = '#' + campo.id;
            link.textContent = rotulo(campo) + ': ' + validar(campo);
            item.appendChild(link);
            lista.appendChild(item);
        });
        resumo.appendChild(titulo);
        resumo.appendChild(lista);
    }

    function formularioValido() {
        return campos.every(function (campo) { return validar(campo) === ''; });
    }

    function atualizarBotao() {
        if (botao) {
            botao.disabled = !formularioValido();
        }
    }

    function revalidar(campo) {
        mostrarErro(campo, tocados[campo.id] ? validar(campo) : '');
        atualizarResumo();
        atualizarBotao();
    }

    // Contador de caracteres do nome.
    var contador = form.querySelector('[data-contador-de]');
    if (contador) {
        var campoNome = document.getElementById(contador.getAttribute('data-contador-de'));
        var atualizarContador = function () {
            var limite = campoNome.maxLength;
            contador.textContent = campoNome.value.length + '/' + limite;
        };
        campoNome.addEventListener('input', atualizarContador);
        atualizarContador();
    }

    // Indicador de força da senha: fraca, média ou forte.
    var forca = form.querySelector('[data-forca-senha]');
    function pontuarSenha(senha) {
        var pontos = 0;
        if (senha.length >= 8) { pontos += 1; }
        if (senha.length >= 12) { pontos += 1; }
        if (/[a-z]/.test(senha) && /[A-Z]/.test(senha)) { pontos += 1; }
        if (/\d/.test(senha)) { pontos += 1; }
        if (/[^A-Za-z0-9]/.test(senha)) { pontos += 1; }
        return pontos;
    }
    function atualizarForca() {
        var senha = form.elements.senha.value;
        var nivel = !senha ? '' : pontuarSenha(senha) <= 2 ? 'fraca' : pontuarSenha(senha) <= 3 ? 'media' : 'forte';
        var textos = { fraca: 'Senha fraca', media: 'Senha média', forte: 'Senha forte', '': '' };
        forca.setAttribute('data-nivel', nivel);
        forca.querySelector('.forca-texto').textContent = textos[nivel];
    }
    if (forca && form.elements.senha) {
        form.elements.senha.addEventListener('input', atualizarForca);
        atualizarForca();
    }

    campos.forEach(function (campo) {
        campo.addEventListener('blur', function () {
            tocados[campo.id] = true;
            revalidar(campo);
        });
        campo.addEventListener('input', function () {
            revalidar(campo);
            // A confirmação depende da senha: revalida junto.
            if (campo.name === 'senha' && form.elements.confirmar_senha) {
                revalidar(form.elements.confirmar_senha);
            }
        });
        campo.addEventListener('change', function () { revalidar(campo); });
    });

    form.addEventListener('submit', function (evento) {
        campos.forEach(function (campo) { tocados[campo.id] = true; mostrarErro(campo, validar(campo)); });
        atualizarResumo();
        if (!formularioValido()) {
            evento.preventDefault();
            var primeiro = campos.filter(function (campo) { return validar(campo); })[0];
            if (primeiro) {
                primeiro.focus();
            }
        }
    });

    // Estado inicial: o servidor pode devolver o formulário já preenchido.
    atualizarBotao();
})();
