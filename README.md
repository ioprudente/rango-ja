# Rango Já — Agente de Atendimento com LLM

Backend de um agente de atendimento com LLM para a **Rango Já**, uma empresa fictícia de delivery. O agente conversa com clientes, consulta pedidos, responde dúvidas com base nas políticas da empresa, concede reembolsos dentro das regras e escala para um atendente humano quando necessário.

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![Pydantic](https://img.shields.io/badge/Pydantic-v2-E92063?logo=pydantic&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Llama%203.2%203B-black?logo=meta&logoColor=white)
![Poetry](https://img.shields.io/badge/Poetry-2.x-60A5FA?logo=poetry&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?logo=docker&logoColor=white)
![Status](https://img.shields.io/badge/status-conclu%C3%ADdo-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Sumário

- [Como rodar](#como-rodar)
- [Endpoint](#endpoint)
- [Arquitetura e Fluxo](#arquitetura-e-fluxo)
- [Principais Decisões de Projeto](#principais-decisões-de-projeto)
- [Regras de Negócio e Segurança](#regras-de-negócio-e-segurança)
- [Cenários de Teste](#cenários-de-teste)
- [Estimativa de Custo e Latência](#estimativa-de-custo-e-latência)
- [Limitações e Próximos Passos](#limitações-e-próximos-passos)
- [Ferramentas de IA Usadas](#ferramentas-de-ia-usadas)

---

## Como rodar

### Pré-requisitos
- Python **3.12+**
- [Poetry](https://python-poetry.org/) **2.x**
- [Ollama](https://ollama.com/) instalado e rodando.
- Modelo `llama3.2:3b` baixado.
- Docker (opcional).

### Passo a passo (Local)

1. Clone o repositório e instale as dependências:
~~~bash
git clone https://github.com/ioprudente/rango-ja.git
cd rango-ja
poetry install
~~~

2. Baixe o modelo no Ollama:
~~~bash
ollama run llama3.2:3b
~~~

3. Crie o arquivo de variáveis de ambiente:
~~~bash
cp .env.example .env
# O arquivo .env.example já está configurado para o Ollama
~~~

4. Inicie o servidor FastAPI:
~~~bash
poetry run uvicorn rango_ja.main:app --reload
~~~

A API estará disponível em `http://127.0.0.1:8000`. Documentação interativa em `/docs`.

---

## Endpoint

### `POST /chat`

**Request:**
~~~json
{
  "cliente_id": "C01",
  "session_id": "abc-123",
  "mensagem": "Meu pedido P1001 atrasou muito"
}
~~~

**Response:**
~~~json
{
  "resposta": "Lamento pelo atraso! O reembolso de R$ 17,98 foi aprovado com sucesso.",
  "acoes": [
    {
      "ferramenta": "solicitar_reembolso",
      "argumentos": { "pedido_id": "P1001", "motivo": "atraso" },
      "resultado": "ok"
    }
  ]
}
~~~

---

## Arquitetura e Fluxo

~~~text
 Cliente
    │
    ▼
 POST /chat ──────────────────────────────────────► FastAPI (validação Pydantic)
                                                         │
                                                         ▼
                                                    Orchestrator (Ollama)
                                                         │
                                       ┌─────────────────┼─────────────────┐
                                       ▼                 ▼                 ▼
                                   Memória           Ferramentas          RAG
                                (session_id)       (Pydantic validando   (Injeção de
                                                   argumentos do LLM)    politicas.md)
                                                         │
                                                         ▼
                                                   Domain (Regras)
                                            (Cálculos, Limites, Auth)
                                                         │
                                                         ▼
                                                  Log de ações
~~~

---

## Principais Decisões de Projeto

*   **Modelo LLM Local (Ollama / Llama 3.2 3B):** Escolhido para garantir custo zero e privacidade. O modelo 1B falhava em *function calling* (imprimia o JSON no texto) e o modelo 8B exigia mais de 6GB de RAM (inviável para a máquina de desenvolvimento com 8GB). O 3B entregou o equilíbrio perfeito.
*   **Regras de Negócio no Código (Domain):** O LLM não calcula reembolsos. Ele apenas *solicita* a ação. A camada `domain/` calcula o valor matemático, valida os 7 dias, o limite de R$ 50 e a privacidade.
*   **Não uso de Frameworks (LangChain/LangGraph):** Para um escopo de 5 ferramentas fixas, o framework adicionaria latência e complexidade. Construir o loop manualmente com `httpx` mostrou-se mais rápido, transparente e permitiu controle fino sobre o payload exigido pelo modelo local.
*   **RAG Simples:** Injeção direta do arquivo `politicas.md` na ferramenta `buscar_politicas`. Como o arquivo é pequeno, um banco vetorial seria *overkill* e aumentaria a latência.
*   **Resiliência:** O orquestrador implementa *retries* com backoff exponencial para timeouts, tratamento específico para HTTP 429 (Rate Limit) e valida os argumentos do LLM via Pydantic antes de executar qualquer ação.

---

## Regras de Negócio e Segurança

Garantidas **pelo código** (em `src/rango_ja/domain/`):

*   **Limite de Reembolso:** Até R$ 50,00 aprova automático. Acima, lança exceção e escala para humano.
*   **Prazo de Reclamação:** Até 7 dias após a entrega (usando a data de referência fixa: 10/10/2026 21:00).
*   **Máximo de um Reembolso:** Bloqueado via checagem de histórico do pedido.
*   **Privacidade:** O `cliente_id` logado é injetado direto nas ferramentas. Se o LLM tentar consultar um pedido de outro cliente, o domínio barra e retorna um erro genérico.

**Diferenciais de Segurança (Prompt Injection):**
1. **Injeção via Dados:** O JSON malicioso de teste (pedido P1007) contém o campo `observacao_entregador` com uma ordem falsa. O código da ferramenta filtra a resposta e **nunca envia esse campo para o LLM**.
2. **Injeção via Cliente:** Se o cliente tentar forçar a IA a ignorar as regras (ex: "me dê 500 reais"), a camada `Domain` em Python ignora o valor solicitado e calcula apenas o valor legal, bloqueando tentativas de fraude.

---

## Cenários de Teste

O projeto conta com duas camadas de testes:

**1. Testes End-to-End (via API com LLM real)**
O script `tests/scenarios_api.py` simula os **6 cenários do PDF + 1 cenário de Prompt Injection**.

~~~bash
# Em um terminal, suba a API:
poetry run uvicorn rango_ja.main:app --reload

# Em outro terminal, rode os testes:
poetry run python tests/scenarios_api.py
~~~
*Resultado atual: 7 passaram, 0 falharam.*

**2. Testes Unitários (sem LLM)**
Validam a lógica pura do domínio (cálculos, limites, regras).
~~~bash
poetry run pytest
~~~

---

## Estimativa de Custo e Latência

| Item | Estimativa |
| :--- | :--- |
| **Custo por conversa** | R$ 0,00 (Modelo local) |
| **Latência por turno** | 3 a 8 segundos (CPU, ~2.5GB de RAM) |
| **Latência total por conversa** | 10 a 25 segundos (devido ao loop de tool calling) |

---

## Limitações e Próximos Passos

**Limitações Conhecidas:**
*   **Modelo 3B:** Por rodar na CPU, pode ocasionalmente alucinar termos textuais ou esquecer de preencher o JSON de parâmetros em loops secundários. No entanto, a validação Pydantic e o domínio impedem que ele quebre as regras ou execute transações erradas.
*   **Persistência:** A memória e o log de ações residem na RAM. Se o servidor reiniciar, os dados são perdidos.

**O que faria diferente em Produção:**
1.  **Infraestrutura:** Migraria para um modelo maior (ex: `gpt-4o`) para reduzir alucinações textuais e latência.
2.  **Persistência:** Trocaria a memória em RAM por Redis (com TTL) e o log de ações por PostgreSQL.
3.  **Observabilidade:** Implementaria tracing com OpenTelemetry.
4.  **Autenticação:** Implementaria JWT real no FastAPI.

---

## Ferramentas de IA Usadas

*   **DeepSeek:** Utilizado para apoiar a estruturação da arquitetura, debugar problemas de integração de bibliotecas, auxiliar na lógica de domínio e regras de negócio, e formatar este documento.
*   **GitHub Copilot:** Utilizado para autocompletar trechos repetitivos de *boilerplate* (schemas do Pydantic, declaração de variáveis).
*   **Nota:** **Não utilizei o ChatGPT** em nenhuma etapa do desenvolvimento.

---

## Licença

MIT.
