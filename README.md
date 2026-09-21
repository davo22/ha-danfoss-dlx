# Danfoss DLX Solar Inverter — Home Assistant integration

Local-polling Home Assistant integration for **Danfoss DLX** series PV inverters
(DLX 2.0 / 2.9 / 3.8 / 4.6) with the built-in "Theia" web server. No cloud, no
extra hardware, no RS-485 adapter — it talks directly to the inverter's own
web interface over HTTP.

Developed and tested against a **DLX 2.9**.

## How it works

The DLX web server exposes a JSON-RPC endpoint at `/rpc/GeteNexusData` that the
inverter's own front-end uses to render its dashboard. Data points are addressed
as `eNEXUS_xxxx[s:<system>,t:<systemType>]` paths. This integration reads the
whole set of values in a single batched request every 30 seconds.

Reading data requires **no authentication** — the same is true for the inverter's
own web UI, which fetches these values before you log in.

The `system` / `systemType` identifiers are discovered automatically at setup
time from `/file/systemList.json`, so multi-inverter installations and other
DLX models should work as well.

## Installation

### HACS (custom repository)

1. HACS → Integrations → ⋮ → Custom repositories
2. Add this repository's URL, category "Integration"
3. Install "Danfoss DLX Solar Inverter", then restart Home Assistant

### Manual

Copy `custom_components/danfoss_dlx/` into your Home Assistant
`<config>/custom_components/` directory and restart.

## Configuration

Settings → Devices & Services → Add Integration → **Danfoss DLX Solar Inverter**,
then enter the inverter's IP address (e.g. `192.168.1.50`).

Note that the inverter serves plain HTTP on port 80; HTTPS is not available.

## Entities

| Entity | Unit | Notes |
| --- | --- | --- |
| AC power | W | current production |
| DC power | W | disabled by default |
| Reactive power | var | disabled by default |
| Energy today | kWh | Energy Dashboard compatible |
| Energy this month | kWh | disabled by default |
| Energy this year | kWh | disabled by default |
| Energy total | kWh | lifetime production |
| Peak power today | W | disabled by default |
| DC voltage / current | V / A | diagnostic |
| AC voltage / current | V / A | diagnostic |
| AC frequency | Hz | diagnostic, disabled by default |
| Temperature | °C | diagnostic |
| Operating hours | h | diagnostic, disabled by default |
| Insulation resistance | kOhm | diagnostic, disabled by default |
| Status | enum | normal / warning / alarm |
| Mode | enum | off / sleeping / startup / running / derating / shutting down / shutdown / service |

Entities marked "disabled by default" can be enabled individually in the entity
settings.

For the Energy Dashboard, use **Energy total** (or **Energy today**) as a solar
production source.

## Requirements

Home Assistant 2024.6.0 or newer.

## Notes

- All values are read-only. The integration never writes to the inverter.
- At night the inverter reports mode `off` and zeroes for power/voltage values —
  this mirrors the device's own behaviour rather than going unavailable.
- Anyone on your LAN can read these values from the inverter without
  credentials; this is how the device's firmware works and this integration
  does not change it.
