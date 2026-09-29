"""Constants for the Ovumcy integration."""

DOMAIN = "ovumcy"

CONF_BASE_URL = "base_url"
CONF_IP_OVERRIDE = "ip_override"

DEFAULT_SCAN_INTERVAL_MINUTES = 60

AUTH_COOKIE = "ovumcy_auth"
CSRF_COOKIE = "ovumcy_csrf"
CSRF_HEADER = "X-CSRF-Token"

# Entities in this integration surface reproductive-health data. They are
# excluded from the recorder by default (see __init__.py) and should never
# be exposed to voice assistants unless the user explicitly opts in.
SENSITIVE_ENTITY_CATEGORY_NOTE = (
    "Ovumcy sensors carry reproductive-health data — recorder history is "
    "disabled by default for this integration's entities."
)
