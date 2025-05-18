# Stage 1: Build stage to prepare dependencies
FROM python:3.12-slim AS builder
WORKDIR /app

# Install curl and upgrade pip, setuptools, wheel
RUN apt-get update && apt-get install -y curl \
    && pip install --no-cache-dir --upgrade pip setuptools wheel \
    && rm -rf /var/lib/apt/lists/*

# Forcefully remove any old versions of Poetry from pip and common system paths
# This is important to avoid conflicts with the pip-installed version below.
RUN pip uninstall -y poetry || true \
    && rm -f /usr/local/bin/poetry || true \
    && rm -f /root/.local/bin/poetry || true # Also try to remove from official installer path

# Install a specific version of Poetry using pip directly from PyPI official source with force-reinstall
# Using poetry==1.7.1 as suggested, as it's known to have the export command.
RUN echo "Attempting to install Poetry version 1.7.1..." \
    && pip install --no-cache-dir --force-reinstall "poetry==1.7.1" -i https://pypi.org/simple

# Verify Poetry version and available commands
RUN echo "Verifying installed Poetry version:" \
    && poetry --version
RUN echo "Displaying Poetry help (to check for export command):" \
    && poetry help

COPY pyproject.toml poetry.lock* ./

# Export dependencies to requirements.txt using the installed poetry
RUN echo "Attempting to run poetry export..." \
    && poetry export --format=requirements.txt --output requirements.txt --extras "api" --without dev
RUN pip install --no-cache-dir -r requirements.txt

# Stage 2: Production stage
FROM python:3.12-slim
WORKDIR /app

# Create a non-root user and group for security
# -r: create a system user
# -s /bin/false: user cannot log in
RUN groupadd -r appuser && useradd -r -s /bin/false -g appuser appuser

# Copy installed Python packages (system-wide) and executables from the builder stage
# Poetry (installed via official script) and its shims will be in /root/.local/bin in builder
# Packages installed by pip -r requirements.txt will be in system site-packages
COPY --from=builder /usr/local/lib/python3.12/site-packages/ /usr/local/lib/python3.12/site-packages/
# Copy Gunicorn and other executables installed by pip in the builder stage
COPY --from=builder /usr/local/bin/ /usr/local/bin/
# We also need to copy Poetry itself if we want to use it in the final stage (e.g., for plugins or dynamic installs)
# However, for a production image where dependencies are already baked in, Poetry might not be needed.
# For now, we only copy what's installed by requirements.txt and system-wide pip executables.
# If Gunicorn or other tools are installed via Poetry into its managed environment, this might need adjustment.
# But since we pip install -r requirements.txt, gunicorn should be in /usr/local/bin if listed there.

# Copy application code
# Ensure the appuser owns these files
COPY --chown=appuser:appuser core ./core
COPY --chown=appuser:appuser tools ./tools
COPY --chown=appuser:appuser cli ./cli
COPY --chown=appuser:appuser pdfshell_srv ./pdfshell_srv
COPY --chown=appuser:appuser coreapi ./coreapi
COPY --chown=appuser:appuser manage.py ./manage.py
# COPY tests ./tests # 您可以根據需要決定是否複製 tests 目錄 (通常不用於生產映像)

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=pdfshell_srv.settings
# Default port, can be overridden by PaaS environment
ENV PORT=8000
# Default Gunicorn workers
ENV GUNICORN_WORKERS=2

# Switch to the non-root user
USER appuser

# EXPOSE is informational; Gunicorn binds to $PORT in CMD
EXPOSE $PORT

# Command to run the application using Gunicorn
# Using sh -c allows $GUNICORN_WORKERS to be expanded.
# Gunicorn should be in PATH due to COPY --from=builder /usr/local/bin/
CMD sh -c "gunicorn pdfshell_srv.wsgi:application --bind 0.0.0.0:$PORT --workers $GUNICORN_WORKERS"
