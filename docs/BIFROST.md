# Bifrost Remote Management — Heimdall

Bifrost is Project Odin's private remote-management transport for Heimdall field nodes.

## Goals

- Keep a stable private identity for Heimdall even when the local Wi-Fi/IP changes.
- Permit remote SSH and dashboard access from authorized tailnet devices.
- Avoid exposing Heimdall's dashboard publicly or directly to an untrusted venue LAN.
- Fail closed: loss of the VPN must not cause public fallback exposure.

## Current transport

Bifrost v0.1 uses Tailscale (WireGuard-based) as the encrypted overlay transport.

The Heimdall Flask dashboard should listen on `127.0.0.1:8080`. Tailscale Serve proxies that localhost service into the tailnet. Tailscale Funnel is intentionally not configured.

## Bootstrap

After updating Josh to the current `heimdall-dev` branch:

```bash
cd ~/Heimdall
chmod +x scripts/bifrost-bootstrap scripts/bifrost-status
bash scripts/bifrost-bootstrap
```

The first run prints a Tailscale authentication URL. Open it on an authorized device and approve Josh. Rerun the script if authentication was not finished before the script exits.

## Verify

```bash
bash ~/Heimdall/scripts/bifrost-status
```

Expected healthy state:

```text
Internet  : ONLINE
tailscaled : ACTIVE
VPN state : CONNECTED
SSH       : ACTIVE
Heimdall  : ACTIVE
```

Use `tailscale serve status` to obtain the private dashboard URL.

## Remote SSH

From another device enrolled in the same tailnet:

```bash
ssh nabzaf@<JOSH_TAILSCALE_IP>
```

The Tailscale address remains stable across ordinary venue/home Wi-Fi changes.

## Security boundary

- Do not configure router port forwarding for Heimdall.
- Do not use Tailscale Funnel for the Heimdall dashboard.
- Keep the dashboard backend bound to localhost.
- Use tailnet access controls to limit which users/devices can reach Josh.
- Protected network names and BSSIDs remain local and must not be committed to Git.
- If Bifrost disconnects, local observation can continue; remote administration should remain unavailable until the private overlay reconnects.

## Later integration

Heimdall heartbeat will expose Bifrost state to Odin: connected/disconnected, tailnet IP, last successful private heartbeat, and current transport state without exposing local protected SSIDs.
