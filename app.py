"""
Garimpo — protótipo de rastreador de ofertas
---------------------------------------------
Backend em Flask + SQLite.

Funcionalidades:
- Cadastro e login de usuários (sessão em cookie assinado pelo Flask)
- Catálogo de produtos com ofertas de várias lojas fictícias
- Lista de interesse (wishlist) por usuário
- Cálculo automático da melhor oferta (menor preço) e do desconto de cada produto
- Painel de "Melhores Ofertas" (maiores descontos, geral ou só da lista do usuário)

Como rodar:
    pip install flask
    python app.py
    Acesse http://localhost:5000
"""

import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, g, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "garimpo.db")
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="/static")
# Em produção, defina FLASK_SECRET_KEY como variável de ambiente.
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "chave-de-desenvolvimento-garimpo")


# ---------------------------------------------------------------------------
# Banco de dados
# ---------------------------------------------------------------------------

def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    primeira_vez = not os.path.exists(DB_PATH)
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            senha_hash TEXT NOT NULL,
            criado_em TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS produtos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            categoria TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ofertas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            produto_id INTEGER NOT NULL,
            loja TEXT NOT NULL,
            preco REAL NOT NULL,
            preco_original REAL NOT NULL,
            link TEXT NOT NULL,
            atualizado_em TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS lista_interesse (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER NOT NULL,
            produto_id INTEGER NOT NULL,
            adicionado_em TEXT DEFAULT (datetime('now')),
            UNIQUE(usuario_id, produto_id),
            FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
            FOREIGN KEY (produto_id) REFERENCES produtos(id) ON DELETE CASCADE
        );
        """
    )
    db.commit()

    if primeira_vez:
        _semear_catalogo(db)
    db.close()


def _semear_catalogo(db):
    """Popula o catálogo com produtos e ofertas de lojas fictícias (dados de demonstração)."""
    produtos = [
        ("Fone de Ouvido Bluetooth XT200", "Eletrônicos"),
        ("Smartwatch Fit Pro", "Eletrônicos"),
        ("Caixa de Som Bluetooth à Prova D'água", "Eletrônicos"),
        ("Notebook Core i5 8GB 256GB SSD", "Informática"),
        ("Monitor 24\" Full HD IPS", "Informática"),
        ("Teclado Mecânico RGB ABNT2", "Informática"),
        ("Mouse Gamer 12000 DPI", "Informática"),
        ("Air Fryer 4L Digital", "Casa"),
        ("Liquidificador Turbo 1200W", "Casa"),
        ("Cadeira Gamer Reclinável", "Games"),
        ("Console Portátil RetroPlay 64GB", "Games"),
        ("Tênis Esportivo Corrida", "Moda"),
        ("Mochila para Notebook Anti-furto", "Moda"),
    ]
    cur = db.cursor()
    cur.executemany("INSERT INTO produtos (nome, categoria) VALUES (?, ?)", produtos)
    db.commit()

    linhas_produtos = cur.execute("SELECT id, nome FROM produtos").fetchall()
    ids = {nome: pid for pid, nome in linhas_produtos}

    lojas = ["Loja Azul", "Mega Tech", "Compre Bem", "Oferta Certa", "Depósito Popular", "ZipShop"]

    # (produto, [(loja, preco_original, preco), ...]) — preco é o valor atual na loja
    ofertas_por_produto = {
        "Fone de Ouvido Bluetooth XT200": [
            ("Loja Azul", 249.90, 179.90),
            ("Mega Tech", 229.90, 199.90),
            ("Oferta Certa", 259.90, 219.00),
        ],
        "Smartwatch Fit Pro": [
            ("Compre Bem", 499.00, 349.00),
            ("ZipShop", 459.00, 399.00),
            ("Loja Azul", 479.90, 429.90),
        ],
        "Caixa de Som Bluetooth à Prova D'água": [
            ("Mega Tech", 189.90, 129.90),
            ("Depósito Popular", 179.90, 149.90),
        ],
        "Notebook Core i5 8GB 256GB SSD": [
            ("Mega Tech", 3299.00, 2699.00),
            ("Compre Bem", 3199.00, 2899.00),
            ("ZipShop", 3399.00, 2999.00),
        ],
        "Monitor 24\" Full HD IPS": [
            ("Loja Azul", 899.00, 699.00),
            ("Oferta Certa", 849.00, 749.00),
        ],
        "Teclado Mecânico RGB ABNT2": [
            ("Mega Tech", 329.90, 219.90),
            ("ZipShop", 299.90, 239.90),
            ("Compre Bem", 349.90, 259.90),
        ],
        "Mouse Gamer 12000 DPI": [
            ("Depósito Popular", 159.90, 99.90),
            ("Loja Azul", 139.90, 109.90),
        ],
        "Air Fryer 4L Digital": [
            ("Compre Bem", 429.00, 299.00),
            ("Oferta Certa", 399.00, 329.00),
            ("ZipShop", 449.00, 349.00),
        ],
        "Liquidificador Turbo 1200W": [
            ("Depósito Popular", 229.90, 159.90),
            ("Loja Azul", 219.90, 179.90),
        ],
        "Cadeira Gamer Reclinável": [
            ("Mega Tech", 1299.00, 899.00),
            ("ZipShop", 1199.00, 999.00),
        ],
        "Console Portátil RetroPlay 64GB": [
            ("Compre Bem", 599.00, 449.00),
            ("Oferta Certa", 549.00, 479.00),
            ("Loja Azul", 579.00, 499.00),
        ],
        "Tênis Esportivo Corrida": [
            ("ZipShop", 349.90, 199.90),
            ("Depósito Popular", 299.90, 229.90),
        ],
        "Mochila para Notebook Anti-furto": [
            ("Loja Azul", 199.90, 119.90),
            ("Mega Tech", 179.90, 139.90),
            ("Compre Bem", 189.90, 149.90),
        ],
    }

    linhas = []
    for nome_produto, lista_ofertas in ofertas_por_produto.items():
        produto_id = ids[nome_produto]
        for loja, preco_original, preco in lista_ofertas:
            link = f"https://exemplo-{loja.lower().replace(' ', '')}.com.br/produto/{produto_id}"
            linhas.append((produto_id, loja, preco, preco_original, link))

    cur.executemany(
        "INSERT INTO ofertas (produto_id, loja, preco, preco_original, link) VALUES (?, ?, ?, ?, ?)",
        linhas,
    )
    db.commit()


# ---------------------------------------------------------------------------
# Autenticação
# ---------------------------------------------------------------------------

def login_requerido(f):
    @wraps(f)
    def decorado(*args, **kwargs):
        if "usuario_id" not in session:
            return jsonify({"erro": "É necessário estar logado."}), 401
        return f(*args, **kwargs)
    return decorado


@app.post("/api/registrar")
def registrar():
    dados = request.get_json(silent=True) or {}
    nome = (dados.get("nome") or "").strip()
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    if not nome or not email or not senha:
        return jsonify({"erro": "Preencha nome, e-mail e senha."}), 400
    if len(senha) < 4:
        return jsonify({"erro": "A senha precisa ter pelo menos 4 caracteres."}), 400

    db = get_db()
    existente = db.execute("SELECT id FROM usuarios WHERE email = ?", (email,)).fetchone()
    if existente:
        return jsonify({"erro": "Já existe uma conta com esse e-mail."}), 409

    senha_hash = generate_password_hash(senha)
    cur = db.execute(
        "INSERT INTO usuarios (nome, email, senha_hash) VALUES (?, ?, ?)",
        (nome, email, senha_hash),
    )
    db.commit()

    session["usuario_id"] = cur.lastrowid
    session["usuario_nome"] = nome
    return jsonify({"id": cur.lastrowid, "nome": nome, "email": email}), 201


@app.post("/api/login")
def login():
    dados = request.get_json(silent=True) or {}
    email = (dados.get("email") or "").strip().lower()
    senha = dados.get("senha") or ""

    db = get_db()
    usuario = db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
    if not usuario or not check_password_hash(usuario["senha_hash"], senha):
        return jsonify({"erro": "E-mail ou senha inválidos."}), 401

    session["usuario_id"] = usuario["id"]
    session["usuario_nome"] = usuario["nome"]
    return jsonify({"id": usuario["id"], "nome": usuario["nome"], "email": usuario["email"]})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.get("/api/sessao")
def sessao_atual():
    if "usuario_id" not in session:
        return jsonify(None)
    return jsonify({"id": session["usuario_id"], "nome": session["usuario_nome"]})


# ---------------------------------------------------------------------------
# Produtos e ofertas
# ---------------------------------------------------------------------------

def _produto_resumo(db, row, usuario_id=None):
    """Monta o resumo de um produto: melhor oferta, loja, desconto e se está na lista do usuário."""
    ofertas = db.execute(
        "SELECT * FROM ofertas WHERE produto_id = ? ORDER BY preco ASC", (row["id"],)
    ).fetchall()
    melhor = ofertas[0] if ofertas else None

    na_lista = False
    if usuario_id:
        item = db.execute(
            "SELECT id FROM lista_interesse WHERE usuario_id = ? AND produto_id = ?",
            (usuario_id, row["id"]),
        ).fetchone()
        na_lista = item is not None

    desconto = 0
    if melhor and melhor["preco_original"] > 0:
        desconto = round((1 - melhor["preco"] / melhor["preco_original"]) * 100)

    return {
        "id": row["id"],
        "nome": row["nome"],
        "categoria": row["categoria"],
        "melhor_preco": melhor["preco"] if melhor else None,
        "preco_original": melhor["preco_original"] if melhor else None,
        "melhor_loja": melhor["loja"] if melhor else None,
        "desconto": desconto,
        "total_lojas": len(ofertas),
        "na_lista": na_lista,
    }


@app.get("/api/produtos")
def listar_produtos():
    busca = (request.args.get("busca") or "").strip().lower()
    categoria = (request.args.get("categoria") or "").strip()
    usuario_id = session.get("usuario_id")

    db = get_db()
    query = "SELECT * FROM produtos WHERE 1=1"
    params = []
    if busca:
        query += " AND LOWER(nome) LIKE ?"
        params.append(f"%{busca}%")
    if categoria:
        query += " AND categoria = ?"
        params.append(categoria)
    query += " ORDER BY nome ASC"

    produtos = db.execute(query, params).fetchall()
    resultado = [_produto_resumo(db, p, usuario_id) for p in produtos]
    return jsonify(resultado)


@app.get("/api/categorias")
def listar_categorias():
    db = get_db()
    linhas = db.execute("SELECT DISTINCT categoria FROM produtos ORDER BY categoria").fetchall()
    return jsonify([linha["categoria"] for linha in linhas])


@app.get("/api/produtos/<int:produto_id>")
def detalhe_produto(produto_id):
    db = get_db()
    produto = db.execute("SELECT * FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    if not produto:
        return jsonify({"erro": "Produto não encontrado."}), 404

    ofertas = db.execute(
        "SELECT loja, preco, preco_original, link, atualizado_em FROM ofertas "
        "WHERE produto_id = ? ORDER BY preco ASC",
        (produto_id,),
    ).fetchall()

    return jsonify({
        "id": produto["id"],
        "nome": produto["nome"],
        "categoria": produto["categoria"],
        "ofertas": [dict(o) for o in ofertas],
    })


# ---------------------------------------------------------------------------
# Lista de interesse
# ---------------------------------------------------------------------------

@app.get("/api/lista")
@login_requerido
def ver_lista():
    usuario_id = session["usuario_id"]
    db = get_db()
    produtos = db.execute(
        """
        SELECT p.* FROM produtos p
        JOIN lista_interesse li ON li.produto_id = p.id
        WHERE li.usuario_id = ?
        ORDER BY li.adicionado_em DESC
        """,
        (usuario_id,),
    ).fetchall()
    resultado = [_produto_resumo(db, p, usuario_id) for p in produtos]
    return jsonify(resultado)


@app.post("/api/lista")
@login_requerido
def adicionar_na_lista():
    dados = request.get_json(silent=True) or {}
    produto_id = dados.get("produto_id")
    if not produto_id:
        return jsonify({"erro": "Informe o produto_id."}), 400

    db = get_db()
    produto = db.execute("SELECT id FROM produtos WHERE id = ?", (produto_id,)).fetchone()
    if not produto:
        return jsonify({"erro": "Produto não encontrado."}), 404

    try:
        db.execute(
            "INSERT INTO lista_interesse (usuario_id, produto_id) VALUES (?, ?)",
            (session["usuario_id"], produto_id),
        )
        db.commit()
    except sqlite3.IntegrityError:
        pass  # já estava na lista — ok, não é erro

    return jsonify({"ok": True}), 201


@app.delete("/api/lista/<int:produto_id>")
@login_requerido
def remover_da_lista(produto_id):
    db = get_db()
    db.execute(
        "DELETE FROM lista_interesse WHERE usuario_id = ? AND produto_id = ?",
        (session["usuario_id"], produto_id),
    )
    db.commit()
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Melhores ofertas
# ---------------------------------------------------------------------------

@app.get("/api/melhores-ofertas")
def melhores_ofertas():
    apenas_lista = request.args.get("apenas_lista") == "1"
    usuario_id = session.get("usuario_id")

    db = get_db()
    if apenas_lista:
        if not usuario_id:
            return jsonify({"erro": "É necessário estar logado."}), 401
        produtos = db.execute(
            """
            SELECT p.* FROM produtos p
            JOIN lista_interesse li ON li.produto_id = p.id
            WHERE li.usuario_id = ?
            """,
            (usuario_id,),
        ).fetchall()
    else:
        produtos = db.execute("SELECT * FROM produtos").fetchall()

    resumos = [_produto_resumo(db, p, usuario_id) for p in produtos]
    resumos = [r for r in resumos if r["melhor_preco"] is not None]
    resumos.sort(key=lambda r: r["desconto"], reverse=True)
    return jsonify(resumos[:10])


# ---------------------------------------------------------------------------
# Páginas estáticas
# ---------------------------------------------------------------------------

@app.get("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
