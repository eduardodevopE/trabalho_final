# Garimpo — protótipo de rastreador de ofertas

Protótipo full-stack de um site para **rastrear vendas, acompanhar produtos de
interesse e encontrar as melhores ofertas** entre lojas fictícias.

## Stack

- **Backend:** Python (Flask) + SQLite
- **Frontend:** HTML, CSS e JavaScript puro (sem frameworks), consumindo a API via `fetch`
- **Autenticação:** sessão em cookie assinado pelo Flask, senha com hash (`werkzeug.security`)

## Como rodar

```bash
# 1. (opcional, recomendado) crie um ambiente virtual
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. instale as dependências
pip install -r requirements.txt

# 3. rode o servidor
python app.py
```

Acesse **http://localhost:5000** no navegador. Na primeira execução, o arquivo
`garimpo.db` é criado automaticamente e populado com um catálogo de
demonstração (13 produtos, cada um com ofertas de 2 a 4 lojas fictícias).

Crie uma conta pela aba "Criar conta" — não existe usuário pré-cadastrado.

## Funcionalidades

- **Login e cadastro** de usuários (`/api/registrar`, `/api/login`, `/api/logout`)
- **Catálogo de produtos** com busca por nome e filtro por categoria
- **Lista de interesse**: adicionar/remover produtos para acompanhar ("Acompanhar preço")
- **Melhores ofertas**: ranking dos maiores descontos do catálogo, com opção de
  olhar só os produtos da sua lista
- Cada produto mostra automaticamente a **loja com o menor preço** e o
  **percentual de desconto**, calculados a partir das ofertas cadastradas

## Estrutura de pastas

```
garimpo/
├── app.py                 # backend Flask (rotas da API + lógica de negócio)
├── requirements.txt
├── garimpo.db              # criado automaticamente na primeira execução
└── static/
    ├── index.html          # single-page app (login, catálogo, lista, ofertas)
    ├── css/style.css
    └── js/script.js        # chamadas à API e renderização dinâmica
```

## Banco de dados

4 tabelas em SQLite:

- `usuarios` (id, nome, email, senha_hash)
- `produtos` (id, nome, categoria)
- `ofertas` (id, produto_id, loja, preco, preco_original, link) — cada produto
  pode ter várias ofertas, uma por loja
- `lista_interesse` (usuario_id, produto_id) — tabela de associação da wishlist

## Próximos passos possíveis

Por ser um protótipo, há espaço natural para evoluir, por exemplo:
- Histórico de preços por oferta (gráfico de variação ao longo do tempo)
- Alertas por e-mail quando um produto da lista cair abaixo de um preço-alvo
- Web scraping ou integração com APIs reais de lojas para popular `ofertas`
  automaticamente, em vez dos dados de demonstração
- Paginação no catálogo e avaliações/reviews de produtos
