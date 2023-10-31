FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY /pyproject.toml /app
COPY /poetry.lock /app

RUN pip3 install poetry
RUN poetry config virtualenvs.create false
RUN poetry install

COPY . /app/

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "3000", "--reload"]
