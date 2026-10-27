// Lembra os filtros da vitrine no navegador (Web Storage).
// Preferência de interface, sem dado sensível: usa localStorage com prefixo padronizado.

const PREFIXO = 'pratocheio:filtro:';
const NOMES = ['q', 'bairro', 'categoria'];

// Só usa o armazenamento se o navegador oferecer (e permitir) o recurso.
const armazenamento = () => {
  try {
    return typeof Storage !== 'undefined' ? window.localStorage : null;
  } catch (erro) {
    return null;
  }
};

const formulario = document.querySelector('form[data-filtros]');
const memoria = armazenamento();

if (formulario && memoria) {
  const campos = NOMES.map((nome) => formulario.elements[nome]).filter(Boolean);
  const chave = (campo) => `${PREFIXO}${campo.name}`;

  // Ao entrar sem filtro na URL, reaplica o último filtro salvo.
  const urlSemFiltros = new URLSearchParams(window.location.search).size === 0;
  if (urlSemFiltros) {
    const salvos = campos.filter((campo) => {
      const valor = memoria.getItem(chave(campo));
      if (valor) campo.value = JSON.parse(valor);
      return Boolean(campo.value);
    });
    if (salvos.length > 0) formulario.requestSubmit();
  }

  // Ao filtrar, guarda os valores escolhidos (vazio apaga a preferência).
  formulario.addEventListener('submit', () => {
    campos.forEach((campo) => {
      if (campo.value) memoria.setItem(chave(campo), JSON.stringify(campo.value));
      else memoria.removeItem(chave(campo));
    });
  });

  // "Limpar filtros" também esquece o que estava salvo.
  const limpar = formulario.querySelector('[data-limpar-filtros]');
  if (limpar) {
    limpar.addEventListener('click', () => {
      campos.forEach((campo) => memoria.removeItem(chave(campo)));
    });
  }
}
