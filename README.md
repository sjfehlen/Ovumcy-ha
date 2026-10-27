# Ovumcy for Home Assistant

Custom integration (HACS-installable) for [Ovumcy](https://github.com/ovumcy/ovumcy-web), a
self-hosted menstrual cycle tracker. Polls `GET /api/v1/stats/overview` and exposes cycle day,
phase, fertility status, and predicted period/ovulation dates as sensors.

> [!WARNING]
> **Disclaimer.** This is an unofficial, community-built integration. It is not made, endorsed or
> supported by the Ovumcy project. It is provided as is, with no warranty.
>
> **Works only with a fork, for now.** It authenticates with a per-account API key, which stock
> Ovumcy does not have. It currently works only with the
> [sjfehlen/ovumcy-web](https://github.com/sjfehlen/ovumcy-web) fork, which adds API keys. It will
> not connect to upstream `ovumcy/ovumcy-web`.
>
> **Not medical advice, and not contraception.** The phases, fertility status and predicted dates
> it shows are estimates calculated by Ovumcy from the data entered. They can be wrong, and must
> not be used to avoid or achieve pregnancy, to diagnose anything, or to make medical decisions.
> Talk to a healthcare professional for any of those.
>
> **Sensitive data.** The entities carry reproductive-health information. Anyone with access to
> your Home Assistant (users, backups, voice assistants, dashboards, automations) may be able to
> see it. See [This is reproductive-health data](#this-is-reproductive-health-data) below.

## Auth model — read this first

The integration authenticates with a **per-account API key**, sent as `Authorization: Bearer <key>`.
There is no login, no session cookie and no stored password. You create the key in Ovumcy under
**Settings → API key**, choose a scope, and paste it into Home Assistant; it is shown only once.

**This needs an Ovumcy build that supports API keys** — the
[sjfehlen/ovumcy-web](https://github.com/sjfehlen/ovumcy-web) fork. Upstream
`ovumcy/ovumcy-web` has no API keys, so on a stock install this integration cannot sign in.

- **Scope:** a **read-only** key is all this integration needs (it only calls
  `GET /api/v1/stats/overview`). Prefer it: a leaked read-only key can't change anything.
- **Revoking or replacing the key** in Ovumcy makes the next poll fail with "rejected", and Home
  Assistant then asks you for a new key (a "Re-authenticate" prompt
  under Settings → Devices & Services) instead of retrying forever.
- **2FA and SSO accounts work**, because a key skips the sign-in step entirely.
- **The key is stored in Home Assistant's config entry**, like any other token. Anyone who can read
  your HA config storage can read it, so treat HA backups accordingly.

Upgrading from 0.1.x (email/password)? Your existing entry keeps its URL, drops the stored
password, and asks for an API key on the next start — no need to delete and re-add it.

If you'd rather not keep a token in Home Assistant, don't install this — use Ovumcy's built-in
[webhook reminders](https://github.com/ovumcy/ovumcy-web/blob/main/docs/notifications.md) or its
`.ics` calendar feed with HA's calendar integration instead.

## This is reproductive-health data

The entities this integration creates report cycle phase, fertility status, and predicted period/
ovulation dates. Two things Home Assistant does **not** do automatically, that you should set up
yourself:

- **Recorder history.** HA integrations cannot opt entities out of the recorder from code —
  add this integration's entities (or the whole `ovumcy` domain) to your `recorder: exclude:`
  config if you don't want years of cycle history sitting in the HA database:
  ```yaml
  recorder:
    exclude:
      entity_globs:
        - sensor.ovumcy_*
        - binary_sensor.ovumcy_*
  ```
- **Voice assistant exposure.** Alexa/Google Assistant/Assist expose newly-added entities based
  on your HA instance's default exposure settings. Check Settings → Voice Assistants after setup
  and explicitly un-expose these entities unless you want your voice assistant able to answer
  "what's her cycle day" out loud.

## Installation

1. HACS → Integrations → ⋮ → Custom repositories → add this repo URL, category "Integration"
2. Install "Ovumcy", restart Home Assistant
3. In Ovumcy: Settings → API key → choose **Read only** → Generate, and copy the key
4. Settings → Devices & Services → Add Integration → "Ovumcy"; enter your instance's base URL
   (e.g. `https://cycle.fehlenfusion.com`) and paste the key
5. If setup fails with "Could not connect" and you've confirmed the URL works in a browser,
   your HA instance's DNS may not be resolving the hostname (this can happen on HAOS VMs not
   using the same resolver as other LAN clients). Set the optional **IP override** field to
   the server's LAN IP — this pins only the network connection to that IP while still using
   the real hostname for HTTPS/cert verification, so it's safe with `COOKIE_SECURE=true`
   deployments (a bare `http://ip:port` base URL is not, since the auth cookie won't persist
   over plain HTTP)

## Entities

| Entity | Enabled by default | Source field |
|---|---|---|
| `sensor.*_current_cycle_day` | Yes | `current_cycle_day` |
| `sensor.*_current_phase` | Yes | `current_phase` (menstrual/follicular/ovulation/luteal/unknown) |
| `sensor.*_current_fertility` | Yes | `current_fertility` (fertile/not_fertile/unknown) |
| `sensor.*_next_period_start` | Yes | `next_period_start` (projected, may be null) |
| `sensor.*_ovulation_date` | Yes | `ovulation_date` (projected or BBT-confirmed) |
| `binary_sensor.*_period_active` | Yes | derived: `current_phase == "menstrual"` |
| `sensor.*_fertility_window_start` / `_end` | No | fertility window bounds |
| `sensor.*_average_cycle_length` | No | rolling average, in days |
| `sensor.*_luteal_phase` | No | inferred or default luteal phase length |
| `binary_sensor.*_ovulation_confirmed` | No | BBT-confirmed vs. projected |

Any projected field can be `null` — Ovumcy withholds predictions it doesn't have enough history
to stand behind (see `suppression` in the API response) rather than guessing. Sensors will show
`unknown` in that state, which is correct, not a bug.

## Not supported

- Writing data. A "read and log periods" key exists in Ovumcy, but this integration only reads;
  it does not expose start/end-period actions.
- Anything that needs more than `GET /api/v1/stats/overview`.
