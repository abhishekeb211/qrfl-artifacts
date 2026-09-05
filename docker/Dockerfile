# abhi211b/qrfl:latest — reproducibility pipeline image (CPU)
# Hardened: current slim base, OS security upgrades, patched build tooling,
# torch>=2.6 (CVE-2025-32434), cryptography/msgpack/setuptools/wheel pins.
# Multi-stage drops build-essential from the runtime image.

ARG PYTHON_BASE=python:3.12-slim-trixie

# ---------- builder ----------
FROM ${PYTHON_BASE} AS builder

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONDONTWRITEBYTECODE=1

RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
        build-essential \
        libssl-dev \
        git \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .

# Patched build tooling + app deps. CPU torch from pytorch.org.
# torch>=2.6 closes CVE-2025-32434; keep torchvision matched to torch minor.
# flwr pins cryptography<45; we then force a CVE-fixed cryptography (48+)
# because Flower does not use the vulnerable packaging paths in this image.
RUN python -m pip install --no-cache-dir --upgrade \
        "pip>=25.0" \
        "setuptools>=78.1.1" \
        "wheel>=0.46.2" \
    && python -m pip install --no-cache-dir \
        "torch==2.11.0+cpu" "torchvision==0.26.0+cpu" \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
    && python -m pip install --no-cache-dir \
        "msgpack>=1.2.1" \
        $(grep -vE '^(torch|torchvision|#|$)' requirements.txt | tr '\n' ' ') \
    && python -m pip install --no-cache-dir --upgrade \
        "cryptography>=48.0.1,<51" \
        "setuptools>=78.1.1" \
        "wheel>=0.46.2" \
        "msgpack>=1.2.1" \
    && python -c "import torch,flwr,cryptography,msgpack,setuptools,wheel; print('ok', torch.__version__, cryptography.__version__)"

# ---------- runtime ----------
FROM ${PYTHON_BASE}

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# OS security upgrades only — no compilers in the final image.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 --shell /usr/sbin/nologin qrfl

# Replace base /usr/local entirely so ensurepip leftovers (old setuptools/msgpack)
# are not left beside upgraded dist-info (Docker COPY merges directories).
RUN rm -rf /usr/local
COPY --from=builder /usr/local /usr/local

WORKDIR /app
COPY . .

RUN chown -R qrfl:qrfl /app
USER qrfl

CMD ["bash", "run_all.sh"]
