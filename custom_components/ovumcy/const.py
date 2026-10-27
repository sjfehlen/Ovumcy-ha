"""Constants for the Ovumcy integration."""

DOMAIN = "ovumcy"

CONF_BASE_URL = "base_url"
CONF_API_KEY = "api_key"
CONF_IP_OVERRIDE = "ip_override"

DEFAULT_SCAN_INTERVAL_MINUTES = 60

# Every Ovumcy API key starts with this fixed, non-secret prefix.
API_KEY_PREFIX = "ovk_"

# Entities in this integration surface reproductive-health data. They are
# excluded from the recorder by default (see __init__.py) and should never
# be exposed to voice assistants unless the user explicitly opts in.
SENSITIVE_ENTITY_CATEGORY_NOTE = (
    "Ovumcy sensors carry reproductive-health data — recorder history is "
    "disabled by default for this integration's entities."
)
