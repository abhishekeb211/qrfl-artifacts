FROM python:3.10.14-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
# CPU-only PyTorch keeps the image build tractable on non-GPU hosts.
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cpu \
    && pip install --no-cache-dir $(grep -v '^torch' requirements.txt | grep -v '^torchvision' | grep -v '^#' | grep -v '^$' | tr '\n' ' ')

COPY . .
ENV PYTHONPATH=/app
CMD ["bash", "run_all.sh"]
