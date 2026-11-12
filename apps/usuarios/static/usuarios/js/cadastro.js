// Validação em tempo real do cadastro (melhoria progressiva: o servidor valida de novo).
// Eventos usados: input (contador e força da senha), blur (validação do campo),
// change (revalida) e submit (validação final). O botão fica sempre habilitado: ao enviar com erros, o
// submit é barrado, os erros aparecem e o foco vai para o primeiro campo inválido.
(function () {
    'use strict';

    let form = document.querySelector('form[data-validar]');
    if (!form) {
        return;
    }

    let resumo = document.querySelector('[data-resumo-erros]');
    let campos = Array.prototype.slice.call(form.querySelectorAll('input, select, textarea'))
        .filter(function (campo) { return campo.type !== 'hidden'; });
    let tocados = {};
    let EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

    function rotulo(campo) {
        let label = form.querySelector('label[for="' + campo.id + '"]');
        return label ? label.textContent.trim() : campo.name;
    }

    function digitos(valor) {
        return valor.replace(/\D/g, '');
    }

    // Devolve a mensagem de erro do campo, ou '' quando ele está válido.
    function validar(campo) {
        let valor = campo.value.trim();
        let nome = campo.name;
        if (!valor) {
            return campo.required ? 'Preencha este campo.' : '';
        }
        if (campo.type === 'email' && !EMAIL.test(valor)) {
            return 'Informe um e-mail válido, como nome@dominio.com.';
        }
        if (nome === 'senha') {
            // O mínimo vem do atributo minlength, renderizado a partir de settings.SENHA_MIN_CARACTERES.
            let minimo = Number(campo.getAttribute('minlength'));
            if (minimo && campo.value.length < minimo) {
                return 'A senha precisa de pelo menos ' + minimo + ' caracteres.';
            }
        }
        if (nome === 'confirmar_senha') {
            let senha = form.elements.senha;
            if (senha && campo.value !== senha.value) {
                return 'As senhas não conferem.';
            }
        }
        if (nome === 'documento') {
            let tamanho = digitos(valor).length;
            // data-documento ("cpf" ou "cnpj") vem do perfil da página; sem ele, aceita os dois.
            let tipo = campo.getAttribute('data-documento');
            if (tipo === 'cpf' && tamanho !== 11) {
                return 'O CPF tem 11 dígitos.';
            }
            if (tipo === 'cnpj' && tamanho !== 14) {
                return 'O CNPJ tem 14 dígitos.';
            }
            if (!tipo && tamanho !== 11 && tamanho !== 14) {
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
        let area = form.querySelector('[data-erro-de="' + campo.id + '"]');
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
        let pendentes = campos.filter(function (campo) { return tocados[campo.id] && validar(campo); });
        resumo.innerHTML = '';
        resumo.hidden = pendentes.length === 0;
        if (!pendentes.length) {
            return;
        }
        let titulo = document.createElement('strong');
        titulo.textContent = 'Corrija para continuar:';
        let lista = document.createElement('ul');
        pendentes.forEach(function (campo) {
            let item = document.createElement('li');
            let link = document.createElement('a');
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

    function revalidar(campo) {
        mostrarErro(campo, tocados[campo.id] ? validar(campo) : '');
        atualizarResumo();
    }

    // Contador de caracteres do nome.
    let contador = form.querySelector('[data-contador-de]');
    if (contador) {
        let campoNome = document.getElementById(contador.getAttribute('data-contador-de'));
        let atualizarContador = function () {
            let limite = campoNome.maxLength;
            contador.textContent = campoNome.value.length + '/' + limite;
        };
        campoNome.addEventListener('input', atualizarContador);
        atualizarContador();
    }

    // Indicador de força da senha: fraca, média ou forte.
    let forca = form.querySelector('[data-forca-senha]');
    function pontuarSenha(senha) {
        let pontos = 0;
        if (senha.length >= 8) { pontos += 1; }
        if (senha.length >= 12) { pontos += 1; }
        if (/[a-z]/.test(senha) && /[A-Z]/.test(senha)) { pontos += 1; }
        if (/\d/.test(senha)) { pontos += 1; }
        if (/[^A-Za-z0-9]/.test(senha)) { pontos += 1; }
        return pontos;
    }
    function atualizarForca() {
        let senha = form.elements.senha.value;
        let nivel = !senha ? '' : pontuarSenha(senha) <= 2 ? 'fraca' : pontuarSenha(senha) <= 3 ? 'media' : 'forte';
        let textos = { fraca: 'Senha fraca', media: 'Senha média', forte: 'Senha forte', '': '' };
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
            let primeiro = campos.filter(function (campo) { return validar(campo); })[0];
            if (primeiro) {
                primeiro.focus();
            }
        }
    });
})();
