# Josh Clean Rebuild

## Goal
Preserve the stable Pwnagotchi runtime/event/UI model and add Heimdall features as plugins/adapters instead of maintaining parallel scanner, display, Bluetooth, and Android state engines.

## Recovery point
The branch `heimdall-recovery-e26a872` preserves the current experimental stack at commit `e26a872916077c0fc0a6de46a2152d4679b646fb`.

## Selected foundation
Use `jayofelony/pwnagotchi` branch `noai` as the runtime baseline. It is currently the repository default branch and supports Pi Zero W, Zero 2 W, Pi 3, Pi 4, and Pi 5. Its configuration already supports `ui.display.enabled = false`, allowing the same runtime to be used for headless nodes.

Do not replace Pwnagotchi's native face/event/UI state engine. Heimdall should consume native plugin callbacks such as UI update, Wi-Fi update, channel hop, epoch, peer, and handshake events.

## Heimdall observation profile
For observation-focused Heimdall nodes, default active interaction off:

```toml
[personality]
deauth = false
associate = false

[ui.display]
enabled = true # false on headless nodes
```

Use existing whitelist / authorized-scope controls for protected networks.

## Target architecture

```text
             PWNAGOTCHI CORE
                   |
            one node state
                   |
       +-----------+-----------+
       |           |           |
   e-paper      web/API    companion bridge
                               |
                          Android app
```

The Heimdall plugin adds OVN identity, authorized passive inventory, Odin/Bifrost export, and Josh-specific UI additions. It must not create duplicate NET/CLI/CAP/CH/scan counters.

## Node profiles

- `epaper`: local Waveshare display enabled.
- `headless`: display disabled; node is visible only through the app/web/fleet interfaces.

Both profiles run the same core and expose the same state.

## Ragnar
Ragnar is a strong candidate for a later intelligence/fleet layer. It already supports Raspberry Pi e-paper, headless/server deployments, web management, mesh/fleet concepts, GPS, Wi-Fi analysis, monitoring, and update flows. Keep it behind the stable Josh runtime initially rather than making it the source of personality/state.

## Milestones
1. Boot stock Jayofelony `noai` on separate test media and verify stock Pwnagotchi behavior.
2. Add Heimdall identity/reskin only; verify stock face/event behavior remains intact.
3. Add a single read-only Heimdall state snapshot generated from native runtime state.
4. Point e-paper, Bluetooth/app bridge, and web views at that same snapshot.
5. Add headless profile and multi-node selector in the Android app.
6. Evaluate Ragnar integration for fleet/network intelligence.

Do not overwrite OVN-002's current SD card until milestones 1 and 2 are proven on separate media.
