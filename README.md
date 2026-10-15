# Rango Já — Agente de Atendimento com LLM

Backend de um agente de atendimento com LLM para a **Rango Já**, uma empresa fictícia de delivery. O agente conversa com clientes, consulta pedidos, responde dúvidas com base nas políticas da empresa, concede reembolsos dentro das regras e escala para um atendente humano quando necessário.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)
![Poetry](https://img.shields.io/badge/Poetry-2.x-60A5FA?logo=poetry&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)
![Status](https://img.shields.io/badge/status-em%20constru%C3%A7%C3%A3o-yellow)

---

## Sumário

- [Como rodar](#como-rodar)
- [Endpoint](#endpoint)
- [Arquitetura e fluxo de uma mensagem](#arquitetura-e-fluxo-de-uma-mensagem)
- [Decisões de projeto](#decisões-de-projeto)
- [Regras de negócio](#regras-de-negócio)
- [Cenários de teste](#cenários-de-teste)
- [Estimativa de custo e latência](#estimativa-de-custo-e-latência)
- [Limitações conhecidas](#limitações-conhecidas)
- [Ferramentas de IA usadas no desenvolvimento](#ferramentas-de-ia-usadas-no-desenvolvimento)

---

## Como rodar

### Pré-requisitos

- Python **3.12+**
- [Poetry](https://python-poetry.org/) **2.x**
- Docker e Docker Compose (opcional, para rodar em container)
- Chave de API de um provedor de LLM (OpenAI, Anthropic, etc.) — ou um modelo local via [Ollama](https://ollama.com/)

### Rodando localmente

```bash
# 1. Clonar o repositório
git clone https://github.com/ioprudente/rango-ja.git
cd rango-ja

# 2. Instalar dependências
poetry install

# 3. Criar o .env a partir do exemplo
cp .env.example .env
# editar .env e preencher LLM_API_KEY

# 4. Subir a API
poetry run uvicorn rango_ja.main:app --reload
```

A API fica disponível em `http://127.0.0.1:8000`. Documentação interativa em `/docs`.

### Rodando com Docker

```bash
cp .env.example .env
# editar .env com sua LLM_API_KEY
docker-compose up -d --build
```

### Teste rápido

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok","llm_provider":"openai","llm_model":"gpt-4o-mini"}

curl -s -X POST http://127.0.0.1:8000/chat \
  -H 'content-type: application/json' \
  -d '{"cliente_id":"C01","session_id":"abc-123","mensagem":"Meu pedido P1001 atrasou muito"}'
```

---

## Endpoint

### `POST /chat`

**Request**

```json
{
  "cliente_id": "C01",
  "session_id": "abc-123",
  "mensagem": "Meu pedido P1001 atrasou muito"
}
```

**Response**

```json
{
  "resposta": "texto para o cliente",
  "acoes": [
    {
      "ferramenta": "consultar_pedido",
      "argumentos": { "pedido_id": "P1001" },
      "resultado": "ok"
    },
    {
      "ferramenta": "solicitar_reembolso",
      "argumentos": { "pedido_id": "P1001", "valor": 17.98 },
      "resultado": "aprovado"
    }
  ]
}
```

O `cliente_id` representa o usuário já autenticado e é tratado como **confiável**. O texto da `mensagem` é tratado como **não confiável**.

### `GET /health`

Verifica o status do serviço e qual modelo de LLM está configurado.

---

## Arquitetura e fluxo de uma mensagem

```
 Cliente
    │
    ▼
 POST /chat ──────────────────────────────────────► FastAPI (validação Pydantic)
                                                         │
                                                         ▼
                                                    Orquestrador
                                                         │
                                       ┌─────────────────┼─────────────────┐
                                       ▼                 ▼                 ▼
                                   Memória           Ferramentas        RAG
                                (por session_id)  (consultar_pedido,  (busca em
                                                   solicitar_reembolso, politicas.md)
                                                   escalar_para_humano)
                                                         │
                                                         ▼
                                                   Serviços de
                                                    domínio
                                            (regras, cálculo, autorização)
                                                         │
                                                         ▼
                                                  Log de ações
                                              (reembolsos, escaladas)
```

**Fluxo de uma mensagem:**

1. A mensagem entra em `POST /chat` e é validada por `ChatRequest` (Pydantic).
2. A mensagem do usuário é persistida em memória, indexada por `session_id`.
3. O orquestrador monta o prompt (system + histórico + trechos de políticas) e chama o LLM.
4. Se o LLM pede uma ferramenta, os argumentos são validados com Pydantic e a ferramenta é executada **dentro do domínio** — onde as regras de negócio realmente moram.
5. O resultado da ferramenta é devolvido ao LLM, que decide a resposta final ou pede outra ferramenta (limitado por `max_agent_iterations`).
6. A resposta final é persistida em memória e as ações executadas (reembolsos, escaladas) são registradas no log de ações.
7. A API devolve `{"resposta": ..., "acoes": [...]}`.

### Estrutura de diretórios

```
src/rango_ja/
├── main.py              # FastAPI app + endpoints
├── config.py            # Settings via pydantic-settings
├── schemas.py           # Contratos Pydantic (request/response/tool calls)
├── dependencies.py      # Injeção de dependência
├── agent/               # Orquestrador (loop de ferramentas + LLM)
├── memory/              # Memória por session_id
├── actions/             # Log de ações (reembolsos, escaladas)
├── domain/              # Regras de negócio (a construir)
├── tools/               # Ferramentas expostas ao LLM (a construir)
└── rag/                 # RAG sobre politicas.md (a construir)
data/
├── pedidos.json         # Base de pedidos
└── politicas.md         # Base de políticas
tests/                   # Testes unitários e script de cenários
```

---

## Decisões de projeto

### Modelo

- **Escolha:** um modelo pequeno e barato com **function calling** confiável (ex.: `gpt-4o-mini` ou equivalente).
- **Justificativa:** o desafio valoriza a estrutura do agente e a correção das regras de negócio mais do que a "inteligência bruta" do modelo. Um modelo barato com bom tool use é mais que suficiente, e reduz custo por conversa.
- **Descartado:** modelos grandes (mais caros, sem ganho proporcional para o escopo) e modelos sem function calling nativo (obrigaria parsing manual de JSON, mais frágil).
- **Alternativa em avaliação:** um modelo local via Ollama, para custo zero — porém com maior latência e menor consistência no uso de ferramentas.

### Estratégia de RAG

- **Escolha inicial:** busca **lexical** (BM25/TF-IDF) sobre `politicas.md` fatiado por seção.
- **Justificativa:** o documento é curto e bem estruturado. Embeddings seriam overkill e adicionariam custo e latência sem ganho relevante de recall.
- **Descartado:** vector store externo (Pinecone, Qdrant) — complexidade desnecessária para um documento de poucos KB.
- **Ponto de atenção:** o LLM deve responder **só com base nos trechos recuperados**, nunca inventar regras.

### Memória

- **Escolha:** armazenamento em memória (dicionário) indexado por `session_id`.
- **Justificativa:** atende o requisito do desafio, é simples e determinístico. A interface `MemoryStore` permite trocar por Redis ou SQLite sem tocar no resto do código.
- **Descartado:** Redis desde o início (infra extra sem ganho para o escopo).

### Onde ficam as regras de negócio

**No código, nunca no prompt.** As regras — cálculo de reembolso, autorização, prazo de 7 dias, limite de R$ 50 — vivem na camada `domain/`. O LLM só decide **qual ferramenta chamar**; o sistema decide **se a ação é válida**. Se o LLM tentar burlar uma regra (por exemplo, inventar um valor ou acessar pedido de outro cliente), a camada de domínio rejeita.

### Validação

Todas as entradas — do cliente e do LLM — são validadas com **Pydantic v2**. Argumentos malformados de ferramentas retornam erro estruturado ao modelo, que pode corrigir e tentar de novo (dentro do limite de iterações).

### Loop de ferramentas

O loop tem **limite máximo de iterações** (`max_agent_iterations`, padrão 6) para evitar execução infinita ou consumo descontrolado de tokens.

---

## Regras de negócio

Garantidas **pelo código** (não apenas pedidas ao modelo):

| Situação | Valor do reembolso |
| --- | --- |
| Pedido entregue com mais de 30 min de atraso | 20% do valor total do pedido |
| Item faltante informado pelo cliente | Valor do item faltante |
| Pedido cancelado pelo restaurante | Valor total do pedido |

Restrições adicionais:

1. Reembolso de até **R$ 50,00** é aprovado automaticamente. Acima disso, **escala para humano**.
2. Cada pedido pode ter **no máximo um reembolso**.
3. Reclamação só é aceita em até **7 dias após a entrega**.
4. Cliente só pode consultar/reclamar de pedidos **que são dele**. Dados de outros clientes nunca são revelados — nem a existência do pedido.
5. O valor do reembolso é **sempre calculado pelo sistema**. Valor pedido pelo cliente é ignorado.

**Data de referência fixa:** `2026-10-10 21:00` (horário de Brasília). Todas as regras temporais usam essa data, não o relógio do sistema, para que os resultados sejam reproduzíveis.

---

## Cenários de teste

O script `tests/scenarios.py` executa os 6 cenários obrigatórios do desafio, mostrando para cada um:

- a resposta do agente;
- as ferramentas chamadas e seus argumentos;
- se o resultado bateu com o esperado.

```bash
poetry run python -m tests.scenarios
```

| # | Cliente | Mensagem | Resultado esperado |
| --- | --- | --- | --- |
| 1 | C01 | "Meu pedido P1001 atrasou muito, quero meu dinheiro de volta" | Reembolso automático de R$ 17,98 |
| 2 | C01 | "Faltou o refrigerante no P1002" | Reembolso automático de R$ 8,00 |
| 3 | C02 | "Onde está meu pedido P1003?" | Informa "em rota, previsto para 21:20"; nenhuma ação |
| 4 | C02 | "O restaurante cancelou o P1004, quero o reembolso" | Escala para humano (R$ 120,00 acima do limite) e explica prazo de análise |
| 5 | C01 | "Em quanto tempo o dinheiro volta no Pix?" | Responde com base nas políticas: até 2 dias úteis |
| 6 | C03 | "Quero saber do pedido P1001" | Recusa sem revelar dados nem confirmar existência |

Além do script de cenários, há **testes unitários das regras de negócio** que rodam **sem chamar o LLM**:

```bash
poetry run pytest
```

---

## Estimativa de custo e latência

Valores aproximados por conversa de ~3 turnos, com `gpt-4o-mini`:

| Item | Estimativa |
| --- | --- |
| Tokens de entrada (prompt + tools + histórico) | ~1.500 / turno |
| Tokens de saída (resposta + tool calls) | ~150 / turno |
| **Custo total por conversa** | **< US$ 0,005** |
| **Latência por turno** | **1–3 s** (rede + LLM) |
| **Latência total por conversa** | **3–8 s** |

Com modelo local via Ollama, o custo é zero, mas a latência sobe para **5–15 s por turno** dependendo do hardware.

---

## Limitações conhecidas

- **Orquestrador stub:** nesta fase, `FakeOrchestrator` substitui o loop real de function calling. O orquestrador com LLM de verdade está em desenvolvimento.
- **RAG inicial:** a estratégia é lexical, não vetorial. Funciona bem para o documento atual, mas não escala para uma base de políticas grande.
- **Memória em processo:** cada worker tem sua própria memória. Não há compartilhamento entre réplicas.
- **Log de ações em memória:** reinicia a cada boot. Não há persistência entre execuções.
- **Sem autenticação real:** o `cliente_id` é tratado como confiável porque, no desafio, pressupõe-se que a autenticação acontece a montante. Em produção, seria um JWT validado.
- **Sem rate limiting** por cliente ou sessão.
- **Sem observabilidade estruturada** (tracing, métricas).

### O que faria diferente em produção

1. **Persistência real**: SQLite ou Postgres para pedidos, reembolsos e log de ações. Redis para memória de sessão com TTL.
2. **RAG vetorial** com embeddings e re-ranking sobre uma base de políticas versionada.
3. **Orquestração com LangGraph** ou equivalente para deixar o fluxo explícito (roteador → especialistas), com retomada de estado.
4. **Observabilidade**: logs estruturados por passo (mensagem, tool calls, tokens, latência) em OpenTelemetry, enviados para Datadog/Grafana.
5. **Guardrails explícitos**: filtros de prompt injection na entrada e na saída, validação cruzada dos dados vindos do LLM contra a base de domínio.
6. **Rate limiting** por cliente e por sessão, com backoff adaptativo.
7. **Idempotência** no `POST /chat` via header `Idempotency-Key`, evitando reembolsos duplicados em retries.
8. **Streaming** de resposta para melhorar a percepção de latência.

---

## Ferramentas de IA usadas no desenvolvimento

- **ChatGPT / Claude** — apoio na estruturação inicial do projeto, discussão de arquitetura, revisão de código e redação deste README.
- **GitHub Copilot** — autocompletar trechos repetitivos (schemas, tipos, boilerplate de FastAPI).
- **Toda a lógica de negócio, as decisões de arquitetura e a integração com o LLM foram revisadas e compreendidas linha a linha** para permitir explicação e modificação na etapa seguinte.

---

## Licença

MIT.