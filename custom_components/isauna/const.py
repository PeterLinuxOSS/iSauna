"""Constants for the iSauna integration."""

from __future__ import annotations

import logging
from datetime import timedelta

DOMAIN = "isauna"
LOGGER = logging.getLogger(__package__)

PLATFORMS: list[str] = [
    "binary_sensor",
    "climate",
    "sensor",
    "switch",
    "number",
    "select",
]

# Config entry keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_TCP_PASSWORD = "tcp_password"

DEFAULT_PORT = 80
DEFAULT_TCP_PASSWORD = "ajlpybvmb"

# Networking
SOCKET_TIMEOUT = 10
HW_VERSION = 3

# The controller is a tiny embedded server that frequently refuses connections
# while busy. Retry within a single poll, and tolerate a few failed polls
# before marking entities unavailable so they don't flap to "stale".
CONNECT_RETRIES = 3
CONNECT_RETRY_DELAY = 1.5
MAX_TOLERATED_FAILURES = 3

# Seconds to coalesce rapid control changes before sending one packet.
APPLY_DEBOUNCE = 0.5

# Retries for a failed write before the change is left staged for the next one.
APPLY_RETRIES = 2

# Grace given to the controller before reading back after a write. Replaces the
# HA default of 10 s, which made every change look like it took ten seconds.
READBACK_DELAY = 2.0

# Polling: faster while running, slower while off.
SCAN_INTERVAL_ACTIVE = timedelta(seconds=10)
SCAN_INTERVAL_IDLE = timedelta(seconds=30)

# The fixed read command sent to the controller to request its current state.
# The trailing password is appended at runtime from the config entry.
READ_COMMAND = "$$$c0000000000000000000000$3"

# Characters the controller wraps its response payload with.
CHARS_TO_REMOVE = ["$$$", "$$A", "$$B", "$$C", "&&&"]

# Operating modes reported / accepted by the controller.
MODE_OFF = "off"
MODES = ["off", "infra", "finn", "steam"]

# Heating modes exposed as climate presets, and the one picked when the
# thermostat is switched to "heat" without a prior selection.
HEAT_MODES = ["infra", "finn", "steam"]
DEFAULT_HEAT_MODE = "finn"

# Default run time (minutes) applied to the timer when a mode is started from
# the thermostat. Steam is shorter since humidity makes sessions intense.
DEFAULT_DURATIONS = {"infra": 45, "finn": 90, "steam": 60}

# Thermostat temperature bounds (match the Set temperature number).
MIN_TEMP = 20
MAX_TEMP = 120
TEMP_STEP = 2

# Maps the controller's single-character mode flag to a mode name (decode).
DECODE_MODE_FLAGS = {"I": "infra", "F": "finn", "G": "steam", "0": "off"}
# Maps a mode name to the controller's two-character write flag (encode).
ENCODE_MODE_FLAGS = {"infra": "WI", "finn": "WF", "steam": "WG", "off": "S0"}

# On/off outputs encoded into the light bitmask of the write command.
SWITCH_KEYS = ["light", "mood_light", "starry_sky", "salt_wall", "air"]

# Reading the controller sends when a probe is absent or not measuring yet.
SENTINEL_ABSENT = 255

# Error flags worth exposing. steamerror and floorheaterror are deliberately
# left out: both are just SENTINEL_ABSENT, which this sauna reports whenever
# the probe is idle, so as "problem" flags they would cry wolf permanently.
ERROR_KEYS = ["temperaturerror", "watererror"]

# Sensors whose hardware is optional; skipped when the first poll reads absent.
OPTIONAL_SENSOR_KEYS = {"floorheatcurtemp"}

# Default device state used to seed the coordinator and to fill in fields the
# controller does not report but the encoder needs.
DATA_TEMPLATE: dict = {
    "hwversion": HW_VERSION,
    "mode": "off",
    "set_mode": "off",
    "desired_temperature": 0,
    "set_temperature": 30,
    "infra1": 0,
    "infra2": 0,
    "set_infra1": 0,
    "set_infra2": 0,
    "timer": "0:0:0",
    "timer_minutes": 0,
    "set_min": 0,
    "light": False,
    "mood_light": False,
    "starry_sky": False,
    "salt_wall": False,
    "air": False,
    "temperaturerror": True,
    "currentsaunatemp": 255,
    "steamerror": True,
    "currentsteam": 255,
    "airtimer": "0:0:0",
    "watererror": True,
    "floorheaton": False,
    "floorheattemp": 0,
    "steam_on": 0,
    "floortemp": 5,
}

# Staged setpoint -> the controller-reported key it mirrors. Re-synced on every
# poll so changes made on the physical panel reach HA, and so a stale set_min
# can never truncate a running session.
PENDING_SOURCE = {
    "set_mode": "mode",
    "set_temperature": "desired_temperature",
    "set_infra1": "infra1",
    "set_infra2": "infra2",
    "set_min": "timer_minutes",
}

# Staged numeric/select setpoints applied via the debounced write command.
# steam_on is reported under its own name, so it needs no mirror entry.
PENDING_KEYS = [*PENDING_SOURCE, "steam_on"]

# Every key a control entity may write locally before the debounced apply.
WRITABLE_KEYS = SWITCH_KEYS + PENDING_KEYS
