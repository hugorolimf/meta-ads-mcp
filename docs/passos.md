Resumindo: vou explicar como implementar o fluxo operacional para um cliente SaaS conectar a conta do Facebook Ads e usar o MCP para extrair dados e operar via UI — incluindo fluxo OAuth, chamadas ao MCP via Bearer token, arquitetura multitenant e boas práticas de segurança. Next: apresentar fluxos, exemplos e dicas de implementação.

3 tarefas pendentes criadas

Ótimo — abaixo está um guia prático completo, direto ao ponto, para integrar o Meta Ads MCP em um SaaS onde clientes conectam suas contas do Facebook Ads e extraem dados direto da UI.

---

## 📋 Cenário — o que você quer
Você tem um SaaS multi-tenant. Usuário (cliente) acessa a plataforma e conecta a sua conta do Facebook Ads. A partir daí, ele quer usar a interface do seu SaaS para consultar campanhas, performance, fazer uploads de criativos, etc. A "camada MCP" (`meta-ads-mcp`) é o backend que fala com a API do Meta e expõe essas operações como ferramentas (tools).

---

## 🔄 Arquitetura recomendada (alta-nível)
- Seu SaaS (backend) gerencia tenants (clientes).
- Cada tenant conecta sua conta do Facebook via OAuth (ou informa token manualmente).
- Seu backend armazena token (seguro/encriptado) associado ao tenant.
- Sempre que um tenant interage com a UI (ex.: “listar campanhas”), seu backend chama o MCP Server (streamable-http), usando o token do tenant no header `Authorization: Bearer <user_access_token>`.
- O MCP server é stateless; ele usa o token do header para executar chamadas à Graph API (via `auth.get_current_access_token()`/`http_auth_integration`).
- Opcional: se usar Pipeboard/Remote MCP, esse serviço trata autenticação e você usa tokens MCP (delegação).

Diagrama lógico:
Client UI -> Your SaaS Backend -> (Authorization: Bearer tenant_token) -> Meta Ads MCP Server -> Meta Graph API.

---

## ✅ Passo a passo prático (fluxo típico)

1) Criar ou registrar um Meta App (sua SaaS App)
- Você precisa de um Meta App (App ID + Secret) para usar OAuth com Facebook.
- Configure os scopes necessários, ex: ads_management, ads_read, pages_show_list, business_management, pages_read_engagement, etc.
- Configure redirect URI para o callback no seu SaaS (ex.: `https://your-saas.com/auth/facebook/callback`).

2) Conectar (OAuth) — fluxo no seu SaaS:
- Usuário clica "Conectar Facebook" na UI.
- Seu backend gera redirect para:
  https://www.facebook.com/v22.0/dialog/oauth?client_id=<APP_ID>&redirect_uri=<YOUR_SAAS_CALLBACK>&scope=ads_read,ads_management,...
- Depois que o usuário autentica, o Facebook redireciona para sua URL de callback com token (ou código).
- Seu SaaS troca token *short-lived* por *long-lived* (Graph API: `oauth/access_token?grant_type=fb_exchange_token&client_id=...&client_secret=...&fb_exchange_token=SHORT_TOKEN`).
- Salve a long-lived token (60 dias) **encriptada** no DB do tenant.

3) Mapear conta(s) do tenant:
- No backend, chame MCP tool `get_ad_accounts` usando o token do tenant (ou chamar Graph API direto) para listar contas acessíveis e armazenar `account_id` (ex: `act_12345678`).
- Isso permite ao usuário escolher qual ad account quer manipular.

4) Usar o MCP server para operações:
- Para executar ferramentas, faça chamadas ao MCP server via JSON-RPC endpoint `/mcp/`.
- Envie `Authorization: Bearer <tenant_token>` no header.
- Exemplo para listar campanhas:
  - JSON-RPC method `tools/call` com `name: "get_campaigns"` e arguments `{ "account_id": "act_123", "limit": 30 }`.
- Internamente, o `http_auth_integration` injeta o token no contexto e `meta_api_tool` usa esse token para as requisições Graph API.

5) UI + UX:
- UI chamará seu backend (ou diretamente MCP se você quiser expor).
- Recomendação: chame seu backend para aplicar rate-limiting / logs / RBAC / agregações antes de fazer a chamada ao MCP.
- Seu backend monta a chamada JSON-RPC para o MCP server (ou chama `make_api_request` localmente) e devolve resultado para UI.

---

## 🔐 Segurança e armazenamento de tokens
- Nunca grave `META_ACCESS_TOKEN` (ou tokens do usuário) sem criptografia.
- Armazenamento seguro:
  - Criptografar com KMS (AWS KMS, Azure KeyVault, Hashicorp Vault).
  - Armazenar apenas long-lived token (evitar tokens com permissões desnecessárias).
- Use RBAC por tenant: tokens pertence ao tenant; não compartilhe entre tenants.
- Registre e audite todas chamadas sensíveis (criação de campanha, mudança de orçamento).
- Tokens expiram (60 dias) → esteja pronto para reauth: notifique usuário e solicite reconexão.

---

## ⚙️ Como usar o MCP server na prática (exemplo com seu backend)
- Backend recebe requisição do cliente (ex.: GET /campaigns?accountId=act_123).
- Backend recupera o token do tenant do DB.
- Backend faz uma chamada HTTP POST para o MCP server (`http://mcp-host:8080/mcp/`), com header:
  - Authorization: Bearer <token_do_tenant>
- Payload JSON:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "id": 42,
  "params": {
    "name": "get_campaigns",
    "arguments": {
      "account_id": "act_123",
      "limit": 20
    }
  }
}
```
- MCP server valida token (via header), executa `get_campaigns` e retorna JSON.
- Backend parsea e devolve JSON para o cliente.

---

## 🧩 Estratégias de integração (comparação rápida)

- A) Backend faz tudo (recomendado):
  - Seu backend detém os tokens (seguros).
  - UI chama backend → backend chama MCP.
  - Simples, seguro, permite logs e validações.
  - Multi-tenant mais fácil de isolar.

- B) UI chama MCP diretamente com token:
  - Usuario obtém token e coloca no frontend (risco CORS/segurança).
  - Fornece acesso direto ao MCP server — você precisa garantir proteção e CORS.
  - Útil para clientes que querem usar MCP direto em LLM clients.

- C) Pipeboard / serviço remoto:
  - Delegar autenticação para remote MCP (Pipeboard).
  - Reduz complexidade de autenticação; é a recomendação do README.
  - Você ainda precisa saber como mapear tokens para tenants.

---

## 🧪 Exemplo completo em Python (backend)
Exemplo simples de rota Flask que chama o MCP:

```python
# app.py (backend)
import os
import json
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)
MCP_URL = "http://localhost:8080/mcp/"

def call_mcp(tool_name, arguments, tenant_token):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {tenant_token}"
    }
    payload = {
        "jsonrpc": "2.0",
        "method": "tools/call",
        "id": 1,
        "params": {
            "name": tool_name,
            "arguments": arguments
        }
    }
    r = requests.post(MCP_URL, headers=headers, json=payload, timeout=30)
    return r.json()

@app.route('/campaigns')
def get_campaigns():
    # Recupera token associado ao tenant (do usuário logado)
    tenant_id = request.args.get("tenant_id")
    # token retrieval (ex: from DB) - aqui simulação
    tenant_token = os.environ.get("TENNAT_TOKEN_TEST")
    account_id = request.args.get("account_id")
    resp = call_mcp("get_campaigns", {"account_id": account_id, "limit": 10}, tenant_token)
    return jsonify(resp)

if __name__ == "__main__":
    app.run(port=5000)
```

---

## 🔁 Estrutura multi-tenant e rota de reconexão
- Armazene:
  - tenant_id
  - meta_app_id (se aplicável)
  - access_token_encrypted
  - token_created_at
  - last_successful_use
- Se `make_api_request` retornar erro auth (401/403), no api.py o `auth_manager.invalidate_token()` vai invalidar e você loga notificação para reconexão.
- Forneça botão na UI: “Reautenticar Facebook Ads” que dispara o mesmo OAuth flow.

---

## 🛠️ Considerações práticas & dicas
- Use `get_ad_accounts` para mostrar quais contas o usuário pode usar e deixar que ele escolha.
- Faça paginação apropriada quando listar campanhas/ads — a Meta API retorna cursor.
- Evite expor `META_APP_SECRET` no frontend.
- Se você precisar de ação persistente (agendamento), use tokens armazenados no backend; MCP server é stateless e aceita token por requisição.
- Cuidado com permissões: usuários precisam ser admins das contas de anúncios para criação/atualização.
- Use logs em `meta_ads_debug.log` (o `utils.setup_logging()` já cria o arquivo).
- Use testes E2E com mocks (responses/pytest) para cada integração.

---

## 🧭 Exemplo de UX completo (produto)
1. Usuário entra em SaaS → Clicar “Conectar Facebook Ads”
2. OAuth flow (redirect/consent)
3. Backend troca token e salva
4. Backend lista accounts do usuário (`get_ad_accounts`) e mostra dropdown
5. Usuário seleciona account
6. UI chama sua API para listar campanhas/ad sets/ads via backend → backend chama MCP (`get_campaigns`, `get_adsets`, etc)
7. Usuário quer criar uma campanha → UI envia dados para seu backend → backend chama `create_campaign` no MCP com token do tenant

---

## ❗ Problemas comuns e troubleshooting
- Exit code 1 ao iniciar MCP server:
  - Verifique logs em `meta_ads_debug.log`.
  - Falta de dependências (Python >=3.10).
  - Porta em uso ou permissões.
- Token inválido:
  - Recebe 401/403 → sinalizar usuário e invalidar token.
- Permissão insuficiente:
  - Alguns endpoints necessitam `ads_management` ou role admin do ad account.
- Campos não aparecem:
  - Meta esconde campos se não houver permissão correta ou não aplicável.

---

Se quiser, da próxima etapa eu posso:
- a) Escrever o **exemplo completo** em Node/Express (rota) + UI mínimo que mostra lista de campanhas e call para `get_insights`.
- b) Criar um **script de exemplo que simula o fluxo OAuth** no seu SaaS (troca do código e armazenamento de token).
- c) **Depurar o exit code 1** do seu servidor local — me envie a saída do terminal / `meta_ads_debug.log` e eu investigarei.

Qual opção prefere seguir agora?