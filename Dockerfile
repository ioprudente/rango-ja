# 1. Imagem base oficial do Python
FROM python:3.11-slim

# 2. Define variáveis de ambiente para o Python não gerar arquivos .pyc e não reter logs no buffer
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    POETRY_VERSION=1.8.2 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# 3. Adiciona o Poetry ao PATH do sistema
ENV PATH="$POETRY_HOME/bin:$PATH"

# 4. Instala dependências do sistema e o Poetry
RUN apt-get update && apt-get install --no-install-recommends -y curl \
    && curl -sSL https://python-poetry.org | python3 - \
    && apt-get purge -y --auto-remove curl \
    && rm -rf /var/lib/apt/lists/*

# 5. Define a pasta de trabalho dentro do container
WORKDIR /app

# 6. Copia apenas os arquivos de dependências primeiro (aproveita o cache do Docker)
COPY pyproject.toml poetry.lock ./

# 7. Instala as dependências de produção (ignora as de desenvolvimento como pytest)
RUN poetry install --no-interaction --no-ansi --no-root --only main

# 8. Copia o resto do código do projeto
COPY src/ ./src/

# 9. Comando para rodar o FastAPI dentro do container
CMD ["poetry", "run", "uvicorn", "src/rango_ja.main:app", "--host", "0.0.0.0", "--port", "8000"]
