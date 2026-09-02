FROM python:3.10.14-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# CPU-only PyTorch; PyPI as extra index so deps (typing-extensions, etc.) resolve.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir \
        torch==2.5.1+cpu torchvision==0.20.1+cpu \
        --index-url https://download.pytorch.org/whl/cpu \
        --extra-index-url https://pypi.org/simple \
    && pip install --no-cache-dir \
        $(grep -vE '^(torch|torchvision|#|$)' requirements.txt | tr '\n' ' ')

COPY . .
ENV PYTHONPATH=/app
CMD ["bash", "run_all.sh"]
