FROM ethereum/client-go:v1.13.15

USER root
RUN apk add --no-cache curl

COPY scripts/node-entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
