# Ovumcy for Home Assistant

Custom integration (HACS-installable) for [Ovumcy](https://github.com/ovumcy/ovumcy-web), a
self-hosted menstrual cycle tracker. Polls `GET /api/v1/stats/overview` and exposes cycle day,
phase, fertility status, and predicted period/ovulation dates as sensors.

## Auth model — read this first

Ovumcy has no API-key or service-account token. This integration signs in with the same
email/password you'd use on the web login, and stores them in the config entry — the same
pattern many camera/NAS integrations use when the vendor never exposed a token API. The session
is requested with `remember_me: true` (30-day cookie); on a `401` the integration re-authenticates
automatically and retries once.

If you'd rather not store a password in Home Assistant, don't install this — use Ovumcy's
built-in [webhook reminders](https://github.com/ovumcy/ovumcy-web/blob/main/docs/notifications.md)
or its `.ics` calendar feed with HA's calendar integration instead. Both need zero credentials
in HA.

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
3. Settings → Devices & Services → Add Integration → "Ovumcy"
4. Enter your instance's base URL (e.g. `https://cycle.fehlenfusion.com`) and the account
   email/password

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

- Accounts with 2FA enabled (the login flow doesn't handle the TOTP challenge step)
- OIDC-only deployments (`OIDC_ENABLED=true` with local sign-in disabled) — this integration only
  does local email/password login

## Development

This was scaffolded against Ovumcy v1.9.2's `docs/openapi.yaml`. If `stats/overview`'s schema
changes upstream, `custom_components/ovumcy/sensor.py`'s `value_fn` lambdas are the only place
that needs updating.
