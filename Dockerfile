FROM python:3.12-slim

WORKDIR /app

RUN pip install poetry

# Copy dependency definition files
COPY pyproject.toml poetry.lock* ./

# Install project dependencies (production only, including 'api' extras for gunicorn)
RUN poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --without dev --no-root --extras "api"

# Copy application code selectively
COPY core ./core
COPY tools ./tools
COPY cli ./cli
COPY pdfshell_srv ./pdfshell_srv
COPY coreapi ./coreapi
COPY manage.py ./manage.py
# COPY tests ./tests # 您可以根據需要決定是否複製 tests 目錄

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=pdfshell_srv.settings

EXPOSE 8000

# Command to run the application
CMD ["gunicorn", "pdfshell_srv.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2"]
