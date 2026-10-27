// Validação de formulários marcados com data-validar.
// O HTML traz `novalidate`: a validação nativa (required, pattern, type...) é
// lida aqui via ValidityState e as mensagens aparecem no DOM, sem alert().

// Mensagens em português para cada tipo de erro nativo.
const mensagemDoCampo = (campo) => {
  const estado = campo.validity;
  if (estado.customError) return campo.validationMessage;
  if (estado.valueMissing) return 'Preencha este campo.';
  if (estado.typeMismatch) {
    return campo.type === 'email' ? 'Informe um e-mail válido, como nome@dominio.com.' : 'Valor inválido.';
  }
  if (estado.patternMismatch) return campo.dataset.mensagem || 'O formato informado não é válido.';
  if (estado.tooShort) return `Use pelo menos ${campo.minLength} caracteres.`;
  if (estado.tooLong) return `Use no máximo ${campo.maxLength} caracteres.`;
  if (estado.rangeUnderflow) return `O valor mínimo é ${campo.min}.`;
  if (estado.rangeOverflow) return `O valor máximo é ${campo.max}.`;
  if (estado.stepMismatch) return 'Informe um valor com até duas casas decimais.';
  return 'Valor inválido.';
};

// Nome do campo para o sumário de erros (texto do <label>).
const rotuloDoCampo = (campo) => {
  const rotulo = document.querySelector(`label[for="${campo.id}"]`);
  return rotulo ? rotulo.textContent.trim() : campo.name;
};

// Regras extras que o HTML não cobre: confirmação de senha e tamanho de arquivo.
const aplicarRegrasExtras = (campo) => {
  campo.setCustomValidity('');

  if (campo.dataset.igual) {
    const outro = document.getElementById(campo.dataset.igual);
    if (outro && campo.value !== outro.value) {
      campo.setCustomValidity('As senhas não coincidem.');
    }
  }

  const limite = Number(campo.dataset.tamanhoMax);
  if (campo.type === 'file' && Number.isFinite(limite) && limite > 0) {
    const arquivo = campo.files[0];
    if (arquivo && arquivo.size > limite) {
      campo.setCustomValidity(`A imagem deve ter no máximo ${Math.round(limite / 1048576)} MB.`);
    }
  }
};

// Mostra (ou limpa) a mensagem de um campo e atualiza os atributos de acessibilidade.
const exibirEstadoDoCampo = (campo) => {
  aplicarRegrasExtras(campo);
  const caixa = document.getElementById(`erro-${campo.id}`);
  const invalido = !campo.checkValidity();

  if (invalido) {
    campo.setAttribute('aria-invalid', 'true');
    campo.setAttribute('aria-describedby', `erro-${campo.id}`);
    if (caixa) caixa.textContent = mensagemDoCampo(campo);
  } else {
    campo.removeAttribute('aria-invalid');
    campo.removeAttribute('aria-describedby');
    if (caixa) caixa.textContent = '';
  }
  return !invalido;
};

// Monta o sumário de erros no topo do formulário (links levam até o campo).
const atualizarSumario = (formulario, camposInvalidos) => {
  const sumario = formulario.querySelector('#resumo-erros');
  if (!sumario) return;

  sumario.replaceChildren();
  if (camposInvalidos.length === 0) {
    sumario.hidden = true;
    return;
  }

  const titulo = document.createElement('p');
  const negrito = document.createElement('strong');
  negrito.textContent = 'Corrija os pontos abaixo para continuar:';
  titulo.append(negrito);

  const lista = document.createElement('ul');
  camposInvalidos.forEach((campo) => {
    const item = document.createElement('li');
    const link = document.createElement('a');
    link.href = `#${campo.id}`;
    link.textContent = `${rotuloDoCampo(campo)}: ${mensagemDoCampo(campo)}`;
    item.append(link);
    lista.append(item);
  });

  sumario.append(titulo, lista);
  sumario.hidden = false;
};

// Campos que o usuário pode preencher (ignora botões, hidden e checkboxes de "limpar").
const camposDoFormulario = (formulario) =>
  Array.from(formulario.elements).filter(
    (el) => el.willValidate && el.id && el.type !== 'checkbox' && el.type !== 'hidden',
  );

// O botão de envio fica desabilitado enquanto houver campo inválido.
const atualizarBotao = (formulario) => {
  const botao = formulario.querySelector('[data-envio]');
  if (!botao) return;
  const campos = camposDoFormulario(formulario);
  campos.forEach(aplicarRegrasExtras);
  botao.disabled = !campos.every((campo) => campo.checkValidity());
};

const iniciarFormulario = (formulario) => {
  formulario.noValidate = true;
  const tocados = new Set();

  // Feedback imediato: enquanto digita (campos já tocados) e ao sair do campo.
  formulario.addEventListener('input', (evento) => {
    const campo = evento.target;
    if (campo.id && tocados.has(campo.id)) exibirEstadoDoCampo(campo);
    else if (campo.id) aplicarRegrasExtras(campo);
    // Mudar a senha pode invalidar a confirmação.
    const confirmacao = formulario.querySelector(`[data-igual="${campo.id}"]`);
    if (confirmacao && tocados.has(confirmacao.id)) exibirEstadoDoCampo(confirmacao);
    atualizarBotao(formulario);
  });

  formulario.addEventListener('change', (evento) => {
    if (evento.target.id) {
      tocados.add(evento.target.id);
      exibirEstadoDoCampo(evento.target);
    }
    atualizarBotao(formulario);
  });

  formulario.addEventListener('focusout', (evento) => {
    const campo = evento.target;
    if (campo.id && camposDoFormulario(formulario).includes(campo)) {
      tocados.add(campo.id);
      exibirEstadoDoCampo(campo);
    }
  });

  // Validação final: impede o envio se houver erro e leva o foco ao sumário.
  formulario.addEventListener('submit', (evento) => {
    evento.preventDefault();
    const campos = camposDoFormulario(formulario);
    const invalidos = campos.filter((campo) => !exibirEstadoDoCampo(campo));
    campos.forEach((campo) => tocados.add(campo.id));

    if (invalidos.length > 0) {
      atualizarSumario(formulario, invalidos);
      const sumario = formulario.querySelector('#resumo-erros');
      if (sumario) sumario.focus();
      return;
    }
    atualizarSumario(formulario, []);
    formulario.submit();
  });

  atualizarBotao(formulario);
};

document.querySelectorAll('form[data-validar]').forEach(iniciarFormulario);

// Preenchimento automático do navegador pode não disparar eventos: reavalia ao carregar.
window.addEventListener('pageshow', () => {
  document.querySelectorAll('form[data-validar]').forEach(atualizarBotao);
});
