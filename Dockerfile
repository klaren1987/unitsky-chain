FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "from solcx import install_solc; install_solc('0.8.20')"

COPY contracts/ contracts/
COPY miner/ miner/
COPY scripts/ scripts/
RUN chmod +x scripts/*.sh

ENV PYTHONUNBUFFERED=1 \
    USST_RPC=http://usst-node:8545 \
    USST_CHAIN_ID=778889 \
    USST_DEPLOYED_PATH=/data/deployed.json \
    USST_FUND_ETHER=10000

CMD ["python", "-m", "miner.usst_miner"]
