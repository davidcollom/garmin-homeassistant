# syntax=docker/dockerfile:1
#
# Container image for the Garmin Home Assistant bridge.
#
# The image only contains the bridge.  The Home Assistant custom integration
# is installed into Home Assistant itself, see docs/installation.md.

FROM python:3.13-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install the dependencies first so that the layer is cached.
COPY bridge/pyproject.toml bridge/README.md ./bridge/
RUN python -m pip install --upgrade pip \
 && python -m pip install "fastapi>=0.110" "uvicorn>=0.27" "aiohttp>=3.9" "pydantic>=2.6"

COPY bridge/src ./bridge/src
RUN python -m pip install --no-deps ./bridge

# The bridge runs as an unprivileged user.
RUN useradd --create-home --uid 10001 bridge
USER bridge

EXPOSE 8099

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8099/v1/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["garmin-bridge"]
