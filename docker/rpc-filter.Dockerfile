FROM python:3.12-alpine
RUN pip install --no-cache-dir websockets eth-account web3
COPY scripts/rpc-filter.py /app/rpc-filter.py
CMD ["python", "/app/rpc-filter.py"]
