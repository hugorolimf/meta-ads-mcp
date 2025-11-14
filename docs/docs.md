

## 💡 O que é o Meta Ads MCP?
O Meta Ads MCP é um servidor MCP (Model Context Protocol) que expõe a API de anúncios da Meta (Facebook / Instagram) como um conjunto de ferramentas que LLMs e clientes MCP podem usar. Ele facilita análise, criação/edição de campanhas, upload de criativos, coleta de insights e integrações com serviços de IA (ex.: OpenAI).  

- Repositório principal: `meta-ads-mcp/`
- Entrypoint CLI: __main__.py
- Transportes suportados: `stdio` (padrão) e `streamable-http` (HTTP JSON/SSE)

---

## 🏗 Arquitetura (visão geral)
Arquitetura central (componentes principais):

- Entrypoint
  - __main__.py – inicia a aplicação e transportes.
- Servidor / Orquestração
  - server.py – configura o `FastMCP` (servidor MCP) e inicializa todas as ferramentas.
  - `StreamableHTTPHandler` — handler de solicitações http "stateless" explicito no código.
- Autenticação
  - auth.py — gerenciamento de token (caching, troca para long-lived token, fluxo OAuth com callback).
  - authentication.py — exposes `get_login_link` e integra com `auth_manager`.
  - http_auth_integration.py — middleware & integração para injetar tokens via cabeçalho HTTP (Authorization: Bearer …).
- Camada de API
  - api.py — wrapper genérico para chamado do Graph API (`make_api_request`), tratamento de erros e logs.
  - http_auth_integration.py — integra token do header na execução `auth.get_current_access_token`.
- Domínio (tools)
  - accounts.py, campaigns.py, `adsets.py`, ads.py, insights.py, `ads_library.py`, etc. — cada arquivo implementa ferramentas (MCP tools) para operar sobre contas, campanhas, criativos, insights, etc.
- Recursos & imagens
  - utils.py, resources.py — manipulação de download, conversão e exposição de imagens como recursos MCP (`meta-ads://images/{resource_id}`).
- Integração LLM/Deep Research
  - openai_deep_research.py — fornece `search` e `fetch` para ChatGPT Deep Research / OpenAI integrations.

Diagrama (resumido no arquivo architecture.md) mostra o server e os fluxos para Meta API / OpenAI / Storage / Logging.

---

## 🔐 Autenticação: como funciona e ordem de precedência
Auth possui múltiplas formas. Ordem/atuais:

1. **Token direto (HIGH precedence)**:
   - Variável de ambiente `META_ACCESS_TOKEN` → usado diretamente (ideal para scripts).
2. **Bearer token no header HTTP**:
   - Header `Authorization: Bearer <token>` — recomendado para `streamable-http`. O middleware `AuthInjectionMiddleware` detecta e injeta via contextvars.
3. **OAuth App (Meta App)**:
   - `META_APP_ID` (e `META_APP_SECRET`) → fluxo OAuth com callback server local (token inicial short-lived, trocado por long-lived em `auth.exchange_token_for_long_lived`).
   - Ferramentas: `get_login_link` (authentication.py) e `auth.login()` CLI.
4. **Pipeboard / Remote MCP**:
   - Integração para usar autenticação gerenciada em nuvem (pipeboard.co) — fallback recomendado por README.

Tokens são **cacheados** por `AuthManager` (salvo em `token_cache.json` em um diretório apropriado), com checks de expiração e mecanismos de invalidar token (ex.: erro 401/403 força invalidation).

Dica: se usar `streamable-http`, o melhor é enviar `Authorization: Bearer <token>` para cada requisição (estático, ou token de Pipeboard).

---

## 🔌 Ferramentas (MCP tools) — padrões e exemplos
- Ferramentas são registradas com `@mcp_server.tool()` (FastMCP).
- A função `@meta_api_tool` (decorator) adiciona autenticação e tratamento de erros comum a todas as ferramentas.
- Exemplos principais:
  - `get_ad_accounts` — lista contas
  - `get_account_info` — detalhes de conta
  - `get_campaigns` / `get_campaign_details` / `create_campaign` / `update_campaign`
  - `get_adsets`, `get_adset_details`, `create_adset`, `update_adset`
  - `get_ads`, `create_ad`, `get_ad_details`, `get_ad_creatives`, `get_ad_image` (download + visualização)
  - `upload_ad_image`, `create_ad_creative`, `update_ad_creative`
  - `get_insights` — coleta de métricas e relatórios
  - `mcp_meta_ads_search_*` — buscas (interesses, locais, etc.)
  - `search` & `fetch` — implementações para OpenAI Deep Research (busca & fetch)
- As ferramentas retornam JSON strings (ou JSON dict) normalizadas.

Exemplo de uso (client HTTP):
- example_http_client.py demonstra `initialize`, `tools/list`, `tools/call` e header Authorization.

---

## 🖼️ Como imagens e recursos são tratados
- `ads.get_ad_image` tenta:
  1. Obter `image_hash` do `creative` (via API `adimages`).
  2. Usar `adimages` endpoint para obter URL do CDN.
  3. Fazer download com `utils.download_image` (várias tentativas, cookies, headers).
  4. Converte para bytes e retorna um objeto `Image` para LLM/cliente.
- `utils.ad_creative_images` mantém imagens em cache (para disponibilizar como recursos localmente).
- `resources.list_resources()` e `resources.get_resource(resource_id)` expõem recursos no formato `meta-ads://images/{resource_id}` para clientes MCP.

---

## 🚀 Como executar localmente (quick start)
1. Clone repo & instale dependências:
```bash
git clone https://github.com/nictuku/meta-ads-mcp.git
cd meta-ads-mcp
pip install -r requirements.txt
```
2. Configure credenciais (exemplos):
```bash
# Usar token direto:
export META_ACCESS_TOKEN="EAAGm0ZC..."
# ou: usar app ID/secret para OAuth:
export META_APP_ID="123456..."
export META_APP_SECRET="YOUR_SECRET"
```
3. Iniciar server (HTTP):
```bash
python -m meta_ads_mcp --transport streamable-http --port 8080
```
4. Testar com example_http_client.py:
```bash
python examples/example_http_client.py
```
- Ele vai usar `Authorization: Bearer <token>` header se você setar `BEARER_TOKEN` ou `META_ACCESS_TOKEN`.

Transport `stdio`:
```bash
python -m meta_ads_mcp
# (fica em modo stdio para clientes MCP compatíveis via STDIO)
```

---

## 🧪 Testes e validações
- Testes unitários e e2e: tests — há testes para `get_ad_image`, `get_campaigns`, `insights`, HTTP transport, etc.
- Teste manual (HTTP): test_http_transport.py (demonstrates initialize, list tools, call a tool).
- Considerações de teste: muitas ferramentas dependem de Meta API & tokens; use mocks para unit tests ou variáveis de ambiente.

---

## ⚠️ Limitações & notas importantes
- Frequency cap visibility: campos como `frequency_control_specs` só aparecem via API para adsets com otimização REACH (conforme META_API_NOTES.md).
- Visibility de campos: campos podem não aparecer mesmo quando configurados (Meta filtra).
- Objetivos (objectives) e mapeamento: a Meta mudou para objetivos ODAX — algumas opções antigas são inválidas.
- Tokens: trocas de token e expiração são importantes; `AuthManager` cuida de caching, mas você precisa cuidar da renovação e tratamento de erros 401/403.
- Verifique resultados no Meta Ads Manager UI para confirmar mudanças: a API pode não expor tudo.
- Algumas operações (upload, criação) exigem permissões corretas no token.

---

## 💾 Segurança e configuração
Variáveis importantes:
- `META_APP_ID` — ID do App (necessário para OAuth)
- `META_APP_SECRET` — secreto (usado para trocar long-lived token)
- `META_ACCESS_TOKEN` — token direto (mais simples)
- `META_ADS_DISABLE_CALLBACK_SERVER` — desabilita callback server para OAuth
- `META_ADS_DISABLE_LOGIN_LINK` — desabilita `get_login_link` tool
- `META_ADS_ENABLE_SAVE_AD_IMAGE_LOCALLY` — permite `save_ad_image_locally` (salvar imagens localmente)

Logs:
- `core/utils.setup_logging()` grava em local apropriado (`APPDATA`/config) com nível DEBUG.

---

## 🔧 Como estender / adicionar ferramentas
- Crie nova função Python no diretório core.
- Adicione os decorators:
  - `@mcp_server.tool()` — registra a ferramenta no MCP
  - `@meta_api_tool` — garante tratamento de acesso/autenticação
- Use `make_api_request(endpoint, access_token, params, method="GET/POST")` para chamar Graph API.
- Adicione testes correspondentes (tests).
- Se precisar de autenticação via header, `http_auth_integration` já injeta tokens no contexto.

---

## 🔭 Integração com LLMs & OpenAI
- openai_deep_research.py adiciona suporte para `search` + `fetch` (formato usado por ChatGPT Deep Research).
- Esses endpoints agregam dados para enriquecer prompts com informações do Meta Ads.

---

## ✅ Resumo rápido
- O Meta Ads MCP é uma camada MCP em volta da Meta Marketing API: abstrai chamadas da API como tools e integra com LLM clients.
- server.py inicia `FastMCP` e registra as tools.
- Autenticação: `META_ACCESS_TOKEN` > `Authorization: Bearer` header > OAuth app flow (OAuth callback), com cache por `AuthManager`.
- Ferramentas são declaradas com `@mcp_server.tool()` & `@meta_api_tool`.
- Imagens são tratadas via `utils` e expostas como recursos `meta-ads://images/{resource_id}`.
- Testes e exemplos estão prontos (example_http_client.py, `tests/*`) para facilitar testes.
- Leia README.md e architecture.md para mais detalhes.

---

Se quiser, posso:
- 🔄 Gerar um tutorial passo-a-passo com exemplos reais (criando campanha, upload de imagem, criar ad).
- 🖼️ Criar um diagrama PNG/SVG a partir do Mermaid em architecture.md.
- 🔐 Ajudar a configurar OAuth local (`META_APP_SECRET` / callback) com exemplos.
- 🧪 Executar / adicionar testes E2E práticos (mockando a Meta API).

Qual desses você prefere que eu faça agora?