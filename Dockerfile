FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=2.1.1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false

WORKDIR /app

RUN pip install --no-cache-dir "poetry==${POETRY_VERSION}"

# Metadados e README precisam estar presentes para o package mode
COPY pyproject.toml poetry.lock README.md ./

# Código precisa existir antes do install para o pacote ser localizado
COPY src ./src

RUN poetry install --no-interaction --no-ansi --without dev

# Dados entram depois para não invalidar o cache do install
COPY data ./data

EXPOSE 8000

CMD ["uvicorn", "rango_ja.main:app", "--host", "0.0.0.0", "--port", "8000"]