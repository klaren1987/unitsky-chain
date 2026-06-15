#!/usr/bin/env bash
# Install or update WireGuard server config with USST node port forwarding.
# Run on the Linux VPS as root:
#   sudo ./scripts/install-wireguard-server.sh
#
# Environment (optional):
#   WAN_IFACE=eth0          public network interface
#   WG_CONF=/etc/wireguard/wg0.conf
#   TEMPLATE=config/wireguard/wg0.server.conf.example

set -euo pipefail

cd "$(dirname "$0")/.."

WAN_IFACE="${WAN_IFACE:-eth0}"
WG_CONF="${WG_CONF:-/etc/wireguard/wg0.conf}"
TEMPLATE="${TEMPLATE:-config/wireguard/wg0.server.conf.example}"

if [ "$(id -u)" -ne 0 ]; then
  echo "Run as root: sudo $0" >&2
  exit 1
fi

if [ ! -f "$TEMPLATE" ]; then
  echo "Template not found: $TEMPLATE" >&2
  exit 1
fi

SERVER_PRIVATE_KEY=""
CLIENT_PUBLIC_KEY=""

if [ -f "$WG_CONF" ]; then
  SERVER_PRIVATE_KEY="$(awk -F' = ' '/^PrivateKey/ {print $2; exit}' "$WG_CONF")"
  CLIENT_PUBLIC_KEY="$(awk -F' = ' '/^PublicKey/ {print $2; exit}' "$WG_CONF")"
  cp "$WG_CONF" "${WG_CONF}.bak.$(date +%Y%m%d%H%M%S)"
  echo "Backed up existing $WG_CONF"
fi

if ! ip link show "$WAN_IFACE" >/dev/null 2>&1; then
  echo "Warning: interface $WAN_IFACE not found. Set WAN_IFACE=your_iface" >&2
  echo "Available interfaces:" >&2
  ip -o link show | awk -F': ' '{print "  " $2}' >&2
fi

SERVER_PRIVATE_KEY="${SERVER_PRIVATE_KEY:-SERVER_PRIVATE_KEY}"
CLIENT_PUBLIC_KEY="${CLIENT_PUBLIC_KEY:-CLIENT_PUBLIC_KEY}"

sed \
  -e "s/SERVER_PRIVATE_KEY/${SERVER_PRIVATE_KEY}/" \
  -e "s/CLIENT_PUBLIC_KEY/${CLIENT_PUBLIC_KEY}/" \
  -e "s/-i eth0/-i ${WAN_IFACE}/g" \
  "$TEMPLATE" > "$WG_CONF"

chmod 600 "$WG_CONF"
echo "Wrote $WG_CONF"

if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
  echo "Opening ports in ufw..."
  ufw allow 51820/udp comment "WireGuard" || true
  ufw allow 8545/tcp comment "USST RPC" || true
  ufw allow 8546/tcp comment "USST WS" || true
  ufw allow 30303/tcp comment "USST P2P" || true
  ufw allow 80/tcp comment "UST HTTPS" || true
  ufw allow 443/tcp comment "UST HTTPS" || true
fi

systemctl enable wg-quick@wg0 2>/dev/null || true
systemctl restart wg-quick@wg0

echo ""
echo "WireGuard restarted. Verify:"
echo "  wg show"
echo "  curl -s http://10.13.13.2:8545  # from VPS, after Windows client connects"
echo ""
echo "Also open TCP 8545, 8546, 30303 in your cloud provider firewall (Hetzner, etc.)."
