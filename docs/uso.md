

## 🔁 Fluxos práticos (“o que eu faço em sequência”)

1) **Listar contas**
- Ferramenta: `get_ad_accounts`.
- Forneça `access_token` via header `Authorization` ou deixe o `auth_manager` usar `META_ACCESS_TOKEN`.

2) **Selecionar conta** (pegar `account_id` do passo anterior)

3) **Criar uma campanha**:
- Tool: `create_campaign`
- Exemplo: `account_id`, `name`, `objective`, `daily_budget`...
```json
{"name":"create_campaign","arguments":{
  "account_id":"act_1234","name":"Nova Campanha","objective":"OUTCOME_TRAFFIC",
  "status":"PAUSED","daily_budget":1000}}
```

4) **Criar adset** (adset.connect to campaign) — use `create_adset` (ver `adsets.py`)
- Forneça `campaign_id`, `targeting`, `daily_budget`, `optimization_goal`, etc.

5) **Upload de imagem -> obter image_hash**:
- Tool: `upload_ad_image`
- Inputs: `account_id`, `file` (base64 data) ou `image_url`
- Retorna `image_hash` que será usado para criar creatives.

6) **Criar creative com image_hash**:
- Tool: `create_ad_creative`
- Inputs: `account_id`, `image_hash`, `page_id`, `message`, `link_url`, etc.
- Retorna creative ID.

7) **Criar anúncio (ad)**:
- Tool: `create_ad`
- Inputs: `account_id`, `adset_id`, `creative_id`, `name`, etc.
- Retorna ad ID.

8) **Ver performance (insights)**:
- Tool: `get_insights`
- Inputs: `object_id` (ad/adset/campaign/account), `time_range`, `breakdown`, `level`.
- Retorna métricas (impressions, clicks, spend, actions, action_values…).

9) **Buscar & analisar (search/fetch)**:
- Tool `search(query)` e `fetch(id)`: úteis com OpenAI Deep Research (retorna registros com contexto pra LLMs).

---

## 🖼️ Como extrair/imagens / visualização:
- `get_ad_image` tenta: pegar `creative.image_hash` → `adimages` endpoint → baixar imagem (funções com retry/headers) → retorna `Image` (objeto `mcp.server.fastmcp.Image`).
- `resources.list_resources()` e `resources.get_resource()` expõem imagens como `meta-ads://images/{resource_id}` (usando `ad_creative_images` cache).

---

## 🚨 Principais regras/práticas e limitações
- Objetivos: novas campanhas exigem objetivos ODAX (ex.: `OUTCOME_TRAFFIC`). Objetivos antigos (`LINK_CLICKS`, `CONVERSIONS`) podem estar deprecados.
- Visibilidade de campos: alguns campos não aparecem (ex.: frequency caps) dependendo do tipo de otimização.
- Auth: se token for inválido → 401/403 → `auth_manager` invalidará token e sugerirá reauth.
- Rate-limits e erros do Graph API devem ser tratados/checados no wrapper `make_api_request`.
- `META_APP_ID`/`META_APP_SECRET` são necessários para OAuth. Se usar `META_ACCESS_TOKEN`, não é obrigatório.

---

## 🧰 Debug / Problemas comuns (incluindo exit code 1)
Se iniciar o servidor com `python -m meta_ads_mcp --transport streamable-http --port 8080` e falhar:
1. Verifique **versionamento Python**: `python --version` (pyproject pede >= 3.10).
2. Verifique se dependências estão instaladas:
   ```bash
   pip install -r requirements.txt
   ```
3. Verifique `APPDATA` logs: `meta_ads_debug.log` (utilizando `utils.setup_logging()`).
4. Faltando variáveis de ambiente: `META_ACCESS_TOKEN` ou `META_APP_ID`/`META_APP_SECRET` poderão impedir o fluxo.
5. Problemas de porta/host: verifique `--port`/`--host` ou se a porta está em uso.
6. Execute em modo `stdio` para ver logs diretos:
   ```bash
   python -m meta_ads_mcp --transport stdio
   ```
7. Ler erro completo no terminal e verificar tracebacks no log.

---

## ✅ Dicas práticas & recomendações
- Use `META_ACCESS_TOKEN` (long-lived) para scripts e integrações.
- Para desenvolvimento, use `--login` (inicia fluxo OAuth) ou `get_login_link` para gerar link de autenticação.
- Teste com example_http_client.py para confirmar o servidor responde e as tools estão registradas.
- Habilite logs (o `utils` já configura arquivo `meta_ads_debug.log`).
- Para LLMs, preferir `streamable-http` com `Authorization: Bearer` header para cada requisição (stateless).

---

## Next steps — quer que eu faça qual?
- Deseja que eu:
  - 1) **Verifique por que seu processo retornou exit code 1** (preciso do log/erro exato do terminal);
  - 2) **Crie um script de exemplo** para criar campanha/creative/ad e depois buscar insights com 1 requisição;
  - 3) **Adicione um pequeno README** com quickstart simplificado para rodar localmente com `META_ACCESS_TOKEN`;
  - 4) **Executar (ou ajudar a executar) o servidor localmente** e testar com example_http_client.py agora (se você disponibilizar saída do erro ou autorizar execução).

Diga qual opção preferir — eu sigo com isso. 💡