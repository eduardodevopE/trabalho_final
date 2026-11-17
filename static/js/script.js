// Garimpo — frontend vanilla JS. Fala com o backend Flask via fetch().

const estado = {
  usuario: null,
  categorias: [],
};

const $ = (seletor) => document.querySelector(seletor);
const $$ = (seletor) => document.querySelectorAll(seletor);

function formatarMoeda(valor) {
  if (valor === null || valor === undefined) return "—";
  return valor.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}

async function api(caminho, opcoes = {}) {
  const resposta = await fetch(caminho, {
    headers: { "Content-Type": "application/json" },
    ...opcoes,
  });
  const dados = await resposta.json().catch(() => null);
  if (!resposta.ok) {
    const mensagem = (dados && dados.erro) || "Algo deu errado. Tente novamente.";
    throw new Error(mensagem);
  }
  return dados;
}

// ----------------------------------------------------------------- views --

function mostrarView(nome) {
  $$(".view").forEach((v) => (v.hidden = true));
  $("#view-auth").hidden = true;

  if (!estado.usuario) {
    $("#view-auth").hidden = false;
    return;
  }

  const view = document.getElementById(`view-${nome}`);
  if (view) view.hidden = false;

  $$(".nav__item").forEach((btn) => {
    btn.classList.toggle("is-ativa", btn.dataset.view === nome);
  });

  if (nome === "catalogo") carregarCatalogo();
  if (nome === "lista") carregarLista();
  if (nome === "melhores") carregarMelhores();
}

function atualizarCabecalho() {
  const nav = $("#nav-app");
  const nomeEl = $("#usuario-nome");
  const btnSair = $("#btn-sair");

  if (estado.usuario) {
    nav.hidden = false;
    nomeEl.hidden = false;
    btnSair.hidden = false;
    nomeEl.textContent = estado.usuario.nome;
  } else {
    nav.hidden = true;
    nomeEl.hidden = true;
    btnSair.hidden = true;
  }
}

// -------------------------------------------------------------- cartões --

function criarCartaoProduto(produto) {
  const modelo = document.getElementById("modelo-cartao").content.cloneNode(true);
  const cartao = modelo.querySelector(".cartao-produto");

  cartao.querySelector(".cartao-produto__categoria").textContent = produto.categoria;
  const descontoEl = cartao.querySelector(".cartao-produto__desconto");
  if (produto.desconto > 0) {
    descontoEl.textContent = `-${produto.desconto}%`;
  } else {
    descontoEl.remove();
  }

  cartao.querySelector(".cartao-produto__nome").textContent = produto.nome;
  cartao.querySelector(".cartao-produto__preco-original").textContent =
    produto.preco_original && produto.preco_original > produto.melhor_preco
      ? formatarMoeda(produto.preco_original)
      : "";
  cartao.querySelector(".cartao-produto__preco-atual").textContent = formatarMoeda(produto.melhor_preco);
  cartao.querySelector(".cartao-produto__loja").textContent = produto.melhor_loja || "—";
  cartao.querySelector(".cartao-produto__lojas-count").textContent =
    produto.total_lojas === 1 ? "1 loja" : `${produto.total_lojas} lojas`;

  const botaoAcao = cartao.querySelector(".cartao-produto__acao");
  const aplicarEstiloBotao = (naLista) => {
    botaoAcao.textContent = naLista ? "Remover da lista" : "Acompanhar preço";
    botaoAcao.classList.toggle("botao--marcado", naLista);
    botaoAcao.classList.toggle("botao--linha", !naLista);
  };
  aplicarEstiloBotao(produto.na_lista);

  botaoAcao.addEventListener("click", async () => {
    if (!estado.usuario) return;
    botaoAcao.disabled = true;
    try {
      if (produto.na_lista) {
        await api(`/api/lista/${produto.id}`, { method: "DELETE" });
        produto.na_lista = false;
      } else {
        await api("/api/lista", { method: "POST", body: JSON.stringify({ produto_id: produto.id }) });
        produto.na_lista = true;
      }
      aplicarEstiloBotao(produto.na_lista);
    } catch (erro) {
      alert(erro.message);
    } finally {
      botaoAcao.disabled = false;
    }
  });

  return cartao;
}

// ------------------------------------------------------------- catálogo --

async function carregarCategorias() {
  if (estado.categorias.length) return;
  estado.categorias = await api("/api/categorias");
  const select = $("#campo-categoria");
  estado.categorias.forEach((cat) => {
    const option = document.createElement("option");
    option.value = cat;
    option.textContent = cat;
    select.appendChild(option);
  });
}

async function carregarCatalogo() {
  await carregarCategorias();
  const busca = $("#campo-busca").value.trim();
  const categoria = $("#campo-categoria").value;
  const params = new URLSearchParams();
  if (busca) params.set("busca", busca);
  if (categoria) params.set("categoria", categoria);

  const produtos = await api(`/api/produtos?${params.toString()}`);
  const grade = $("#grade-catalogo");
  grade.innerHTML = "";
  produtos.forEach((p) => grade.appendChild(criarCartaoProduto(p)));
}

let temporizadorBusca = null;
$("#campo-busca").addEventListener("input", () => {
  clearTimeout(temporizadorBusca);
  temporizadorBusca = setTimeout(carregarCatalogo, 300);
});
$("#campo-categoria").addEventListener("change", carregarCatalogo);

// -------------------------------------------------------- minha lista --

async function carregarLista() {
  const produtos = await api("/api/lista");
  const vazio = $("#lista-vazia");
  const recibo = $("#recibo-lista");

  if (produtos.length === 0) {
    vazio.hidden = false;
    recibo.hidden = true;
    return;
  }
  vazio.hidden = true;
  recibo.hidden = false;

  const itensEl = $("#recibo-itens");
  itensEl.innerHTML = "";
  let economiaTotal = 0;

  produtos.forEach((p) => {
    const item = document.createElement("div");
    item.className = "recibo__item";

    const temDesconto = p.preco_original && p.preco_original > p.melhor_preco;
    if (temDesconto) economiaTotal += p.preco_original - p.melhor_preco;

    item.innerHTML = `
      <div class="recibo__item-info">
        <span class="recibo__item-nome">${p.nome}</span>
        <span class="recibo__item-loja">menor preço em ${p.melhor_loja || "—"}</span>
        <button class="recibo__item-remover">remover da lista</button>
      </div>
      <div class="recibo__item-precos">
        ${temDesconto ? `<span class="recibo__item-preco-original">${formatarMoeda(p.preco_original)}</span>` : ""}
        <span class="recibo__item-preco-atual">${formatarMoeda(p.melhor_preco)}</span>
      </div>
    `;

    item.querySelector(".recibo__item-remover").addEventListener("click", async () => {
      await api(`/api/lista/${p.id}`, { method: "DELETE" });
      carregarLista();
    });

    itensEl.appendChild(item);
  });

  $("#recibo-total-valor").textContent = formatarMoeda(economiaTotal);
}

// ---------------------------------------------------------- melhores ofertas --

async function carregarMelhores() {
  const apenasLista = $("#filtro-apenas-lista").checked;
  const params = apenasLista ? "?apenas_lista=1" : "";
  try {
    const produtos = await api(`/api/melhores-ofertas${params}`);
    const grade = $("#grade-melhores");
    grade.innerHTML = "";
    if (produtos.length === 0) {
      grade.innerHTML = `<p class="estado-vazio">Nenhuma oferta encontrada para esse filtro.</p>`;
      return;
    }
    produtos.forEach((p) => grade.appendChild(criarCartaoProduto(p)));
  } catch (erro) {
    alert(erro.message);
  }
}

$("#filtro-apenas-lista").addEventListener("change", carregarMelhores);

// ------------------------------------------------------------------ nav --

$$(".nav__item").forEach((btn) => {
  btn.addEventListener("click", () => mostrarView(btn.dataset.view));
});

$("#btn-sair").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  estado.usuario = null;
  atualizarCabecalho();
  mostrarView("catalogo");
});

// ---------------------------------------------------------------- auth --

$$(".auth__aba").forEach((aba) => {
  aba.addEventListener("click", () => {
    $$(".auth__aba").forEach((a) => a.classList.remove("is-ativa"));
    aba.classList.add("is-ativa");
    const alvo = aba.dataset.aba;
    $("#form-login").hidden = alvo !== "login";
    $("#form-registro").hidden = alvo !== "registro";
  });
});

function mostrarErroAuth(id, mensagem) {
  const el = document.getElementById(id);
  el.textContent = mensagem;
  el.hidden = false;
}

async function entrarComoUsuario(usuario) {
  estado.usuario = usuario;
  atualizarCabecalho();
  mostrarView("catalogo");
}

$("#form-login").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  $("#erro-login").hidden = true;
  const dados = Object.fromEntries(new FormData(evento.target));
  try {
    const usuario = await api("/api/login", { method: "POST", body: JSON.stringify(dados) });
    evento.target.reset();
    entrarComoUsuario(usuario);
  } catch (erro) {
    mostrarErroAuth("erro-login", erro.message);
  }
});

$("#form-registro").addEventListener("submit", async (evento) => {
  evento.preventDefault();
  $("#erro-registro").hidden = true;
  const dados = Object.fromEntries(new FormData(evento.target));
  try {
    const usuario = await api("/api/registrar", { method: "POST", body: JSON.stringify(dados) });
    evento.target.reset();
    entrarComoUsuario(usuario);
  } catch (erro) {
    mostrarErroAuth("erro-registro", erro.message);
  }
});

// --------------------------------------------------------------- início --

(async function iniciar() {
  try {
    const sessao = await api("/api/sessao");
    if (sessao) {
      estado.usuario = sessao;
      atualizarCabecalho();
      mostrarView("catalogo");
      return;
    }
  } catch (erro) {
    console.error(erro);
  }
  atualizarCabecalho();
  mostrarView("catalogo"); // vai cair na tela de auth pois não há usuário
})();
