# Arquitetura do sistema meta-ads-mcp

Este documento descreve a arquitetura do projeto `meta-ads-mcp` (estrutura de componentes, fluxos principais e integrações externas). Inclui um diagrama em Mermaid para visualização rápida e notas de implantação e melhorias.

## Visão geral

O `meta-ads-mcp` é uma coleção de ferramentas e módulos para integrar com a API de anúncios da Meta (Facebook/Meta Marketing API), prover automações (ads, adsets, campanhas), relatórios (insights) e integrações com serviços de terceiros como OpenAI. O repositório contém um entrypoint CLI/servidor em `meta_ads_mcp/__main__.py` e os módulos principais em `meta_ads_mcp/core/`.

## Diagrama de arquitetura (Mermaid)

```mermaid
flowchart LR
  %% Clients
  subgraph Clients[Clientes]
    WebUI[Web UI / Frontend / API Clients]
    CLI[CLI / examples/example_http_client.py]
    Scheduler[Scheduler / Batch Jobs / Cron]
  end

  %% App
  subgraph App[Aplicação - meta_ads_mcp]
    Entrypoint[[`meta_ads_mcp/__main__.py`]]
    Server[Server / HTTP handler (`core/server.py`)]
    Callback[Callback Server (`core/callback_server.py`)]
  end

  %% Core modules
  subgraph Core[Core modules (`meta_ads_mcp/core/`)`]
    Auth[Auth / authentication (`auth.py`, `authentication.py`) ]
    APIClient[HTTP Transport & API wrapper (`api.py`, `http_auth_integration.py`) ]
    Accounts[Accounts (`accounts.py`) ]
    Campaigns[Campaigns / Adsets / Ads (`campaigns.py`,`adsets.py`,`ads.py`) ]
    Creatives[Ads Library / Creatives (`ads_library.py`) ]
    Insights[Insights / Reports (`insights.py`, `reports.py`) ]
    Duplication[Duplication helpers (`duplication.py`) ]
    Utils[Utilitários (`utils.py`) ]
    OpenAI[OpenAI integration (`openai_deep_research.py`) ]
  end

  %% External services
  subgraph External[Serviços externos]
    MetaAPI[(Meta Marketing API / Graph API)]
    OpenAIAPI[(OpenAI API)]
    Storage[(Storage / S3 / Blob)]
    Logging[(Logging / Monitoring / Sentry / Prometheus)]
    ClientsWebhooks[(Clientes - Webhooks / Callbacks)]
  end

  %% Flows
  WebUI -->|HTTP/REST| Server
  CLI -->|CLI / HTTP| Entrypoint --> Server
  Scheduler -->|Batch| Server

  Server --> Auth
  Auth --> APIClient

  Server --> Accounts
  Server --> Campaigns
  Server --> Creatives
  Server --> Insights
  Server --> Duplication
  Server --> OpenAI
  Server --> Callback

  Accounts --> APIClient
  Campaigns --> APIClient
  Creatives --> APIClient
  Insights --> APIClient
  Duplication --> APIClient

  APIClient --> MetaAPI
  OpenAI --> OpenAIAPI

  Callback -->|webhook relay| ClientsWebhooks
  Server -->|store artifacts| Storage
  Server -->|emit metrics| Logging

  classDef svc fill:#f9f,stroke:#333,stroke-width:1px;
  class MetaAPI,OpenAIAPI,PipeboardAuth,Storage,Logging svc

``` 

> Observação: o diagrama acima é uma visão simplificada; detalhes de implementação (classes e funções) estão nos arquivos do pacote `meta_ads_mcp/core/`.

## Descrição dos componentes

- Entrypoint (`meta_ads_mcp/__main__.py`): inicializador da aplicação; interpreta argumentos CLI e inicia o servidor local ou executa tarefas ad-hoc.
- `core/server.py`: orquestra as rotas HTTP, endpoints REST e expõe APIs usadas por clientes internos/externos.
- `core/callback_server.py`: recebe webhooks/callbacks da Meta e repassa para processamento.
- Autenticação (`auth.py`, `authentication.py`): gerencia tokens, refresh, e fluxos de autenticação OAuth.
- `api.py` / `http_auth_integration.py`: camada de transporte HTTP com retry, logging, e tratamento de erros específicos da Meta API.
- Módulos de domínio (`accounts.py`, `ads.py`, `adsets.py`, `campaigns.py`, `ads_library.py`): encapsulam operações de negócios sobre contas, campanhas, criativos.
- Insights e Reports (`insights.py`, `reports.py`): coleta e normalização de métricas / ações / valores.
- `openai_deep_research.py`: integração com OpenAI para enriquecimento de dados e automações (onde aplicável).
- `utils.py`: funções auxiliares e helpers.

## Fluxos importantes (resumido)

1. Fluxo de requisição típica:
   - Cliente faz requisição -> `server.py` valida e autentica -> chama módulo de domínio -> módulo usa `api.py` para comunicar com a Meta API -> resposta é normalizada e retornada.
2. Fluxo de webhook/callback:
   - Meta envia callback -> `callback_server.py` valida origem -> publica evento para processamento (sincrono ou enfileirado) -> executa ações (por exemplo, atualização de estado de anúncios).
3. Integração OpenAI:
   - Módulos que precisem de geração/enriquecimento chamam `openai_deep_research.py` -> OpenAI API -> resultado agregado ao payload.

## Notas de implantação

- Contêiner: `Dockerfile` já presente; rodar a partir da imagem garante dependências isoladas.
- Configuração: `server.json` e variáveis de ambiente para credenciais (Meta tokens, OpenAI key).
- Observabilidade: conectar `Logging`/`Monitoring` (Sentry, Prometheus) para métricas e alertas.

## Melhorias e próximos passos sugeridos

- Adicionar um diagrama UML detalhado (classe / sequência) para os fluxos críticos (ex.: criação de campanhas e upload de criativos).
- Criar testes de integração que simulam chamadas à Meta API via mocks (usar VCR ou responses).
- Separar responsabilidades: considerar extrair camada de persistence (se houver necessidade de persistência) e adicionar fila (RabbitMQ / Redis streams) para processamento assíncrono de callbacks.
- Gerar um arquivo `docs/architecture.mmd` com apenas o bloco Mermaid para facilitar reuso e importação.

## Localização dos arquivos relevantes

- Entrypoint: `meta_ads_mcp/__main__.py`
- Módulos principais: `meta_ads_mcp/core/*.py`
- Testes: `tests/` (vários testes unitários e E2E já presentes)

---

Se quiser, eu posso:
- Gerar também `docs/architecture.mmd` apenas com o diagrama (útil para ferramentas que importam `.mmd`).
- Adicionar uma imagem/diagrama exportado (PNG/SVG) do Mermaid.
- Abrir um PR com este arquivo e exemplos de visualização.

Diga qual das opções prefere que eu faça a seguir.
