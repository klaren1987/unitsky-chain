#!/bin/bash
# ============================================================
#  fix-vps-wireguard.sh
#  Run on the VPS (root@147.45.143.23) to restore WireGuard
#  and the DNAT rules for Unitsky String Technologies.
#
#  Usage:
#    ssh root@147.45.143.23
#    bash <(curl -fsSL https://raw.githubusercontent.com/klaren1987/unitsky-chain/main/scripts/fix-vps-wireguard.sh)
#  OR copy-paste the content manually.
# ============================================================

set -e

IFACE=${1:-eth0}   # public interface — change if needed
WG_IFACE=wg0
WIN_IP=10.13.13.2  # Windows WireGuard peer IP

echo "=== 1. Check WireGuard service ==="
systemctl is-active wg-quick@${WG_IFACE} && {
    echo "WireGuard is already running — restarting to reapply rules..."
    systemctl restart wg-quick@${WG_IFACE}
} || {
    echo "WireGuard is stopped — starting..."
    systemctl start wg-quick@${WG_IFACE}
}

echo "=== 2. Enable and persist WireGuard ==="
systemctl enable wg-quick@${WG_IFACE}

echo "=== 3. Verify tunnel is up ==="
sleep 2
wg show ${WG_IFACE} 2>/dev/null && echo "Tunnel OK" || echo "WARNING: wg show failed — check /etc/wireguard/wg0.conf"

echo "=== 4. Apply DNAT rules (idempotent) ==="
apply_dnat() {
    local proto=$1 src_port=$2 dst_port=$3
    iptables -t nat -C PREROUTING -i ${IFACE} -p ${proto} --dport ${src_port} -j DNAT --to-destination ${WIN_IP}:${dst_port} 2>/dev/null \
        || iptables -t nat -A PREROUTING -i ${IFACE} -p ${proto} --dport ${src_port} -j DNAT --to-destination ${WIN_IP}:${dst_port}
}
apply_dnat tcp 80  80
apply_dnat tcp 443 443
apply_dnat tcp 8545 8545
apply_dnat tcp 8546 8546
apply_dnat tcp 30303 30303

# FORWARD rules
iptables -C FORWARD -i ${IFACE} -o ${WG_IFACE} -j ACCEPT 2>/dev/null \
    || iptables -A FORWARD -i ${IFACE} -o ${WG_IFACE} -j ACCEPT
iptables -C FORWARD -i ${WG_IFACE} -o ${IFACE} -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null \
    || iptables -A FORWARD -i ${WG_IFACE} -o ${IFACE} -m state --state RELATED,ESTABLISHED -j ACCEPT

# Masquerade
iptables -t nat -C POSTROUTING -o ${WG_IFACE} -j MASQUERADE 2>/dev/null \
    || iptables -t nat -A POSTROUTING -o ${WG_IFACE} -j MASQUERADE

echo "=== 5. Save iptables rules for persistence ==="
if command -v iptables-save > /dev/null; then
    iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
fi
if command -v netfilter-persistent > /dev/null; then
    netfilter-persistent save
fi

echo "=== 6. Current DNAT rules ==="
iptables -t nat -L PREROUTING -n --line-numbers

echo ""
echo "=== Done! Test from Windows: ==="
echo "  curl -s https://147-45-143-23.sslip.io/"
echo "  curl -s -X POST https://147-45-143-23.sslip.io/rpc -H 'Content-Type: application/json' -d '{\"jsonrpc\":\"2.0\",\"method\":\"eth_blockNumber\",\"params\":[],\"id\":1}'"
