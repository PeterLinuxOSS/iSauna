"""Tests for the iSauna protocol layer and the idle push gate.

Everything here exercises pure functions: no Home Assistant, no network, no
controller. See tests/_pure.py for how the modules are loaded.
"""

from __future__ import annotations

import pytest
from _pure import const, protocol

PASSWORD = "testpass"

# A 30-character payload: finnish mode, 45 min left, floor heating on at 35 C.
#          0123456789...
PAYLOAD = (
    "AB"  # [0:2]   header
    "F"  # [2]     mode = finn
    "7"  # [3]     infra1 = 70
    "0"  # [4]     infra2 = 0
    "3c"  # [5:7]   desired temperature = 60
    "00"  # [7:9]   minutes high byte
    "2d"  # [9:11]  minutes low byte = 45
    "00"  # [11:13] seconds
    "1"  # [13]    light bitmask = light on
    "1a"  # [14:16] current temperature = 26
    "28"  # [16:18] current steam = 40
    "0"  # [18]    fan time
    "0"  # [19]    padding
    "37"  # [20:22] steam_on = 55
    "0"  # [22]    air time
    "0"  # [23]    sauna status
    "55"  # [24:26] floor setpoint raw = 85 -> on, 35 C
    "07"  # [26:28] floortemp = 7 (differs from the default, so a stale
    "1e"  # [28:30] current floor temperature = 30   default would show up)
)

# Absolute offsets into the string encode_settings produces, verified against
# a real encode. A shift here is exactly the bug class these tests guard.
ENC_LIGHT = 17
ENC_STEAM_ON = slice(24, 26)
ENC_FLOOR_SETPOINT = slice(28, 30)
ENC_FLOORTEMP = slice(30, 32)


def _decoded() -> dict:
    return protocol.decode_state(PAYLOAD, hwversion=3)


# --- A2/A3/A4: fields the encoder reads must be the fields the decoder writes ---


def test_encoder_inputs_are_all_produced_by_the_decoder():
    """Every key encode_settings reads back must survive a decode round-trip."""
    data = _decoded()
    for key in ("floorheattemp", "floortemp", "steam_on"):
        assert key in data, f"{key} is encoded but never decoded"


def _encode(data: dict, **over) -> str:
    state = {**const.DATA_TEMPLATE, **data, "set_mode": "finn", "set_min": 45, **over}
    return protocol.encode_settings(state, PASSWORD)


def test_floor_heating_survives_a_round_trip():
    data = _decoded()
    assert data["floorheaton"] is True
    assert data["floorheattemp"] == 35
    assert _encode(data)[ENC_FLOOR_SETPOINT] == "55"


def test_floor_heating_off_keeps_its_raw_value():
    off_payload = PAYLOAD[:24] + "14" + PAYLOAD[26:]  # raw 20 -> below the 40 cut
    data = protocol.decode_state(off_payload, hwversion=3)
    assert data["floorheaton"] is False
    assert data["floorheattemp"] == 20
    assert _encode(data)[ENC_FLOOR_SETPOINT] == "14"


def test_floortemp_is_not_replaced_by_its_default():
    data = _decoded()
    assert data["floortemp"] == 7 != const.DATA_TEMPLATE["floortemp"]
    assert _encode(data)[ENC_FLOORTEMP] == "07"


def test_steam_setpoint_is_not_zeroed_by_a_write():
    data = _decoded()
    assert data["steam_on"] == 55
    assert _encode(data, set_mode="steam")[ENC_STEAM_ON] == "37"


def test_watererror_is_a_bool_not_a_string():
    steam_payload = PAYLOAD[:2] + "G" + PAYLOAD[3:]
    data = protocol.decode_state(steam_payload, hwversion=3)
    assert data["watererror"] is False


# --- A1: the staged timer must be recoverable from a poll ---


def test_decode_reports_raw_remaining_minutes():
    assert _decoded()["timer_minutes"] == 45
    assert _decoded()["timer"] == "0:45:0"


# --- C1: the idle push gate ---


def _state(**over) -> dict:
    return {**const.DATA_TEMPLATE, "mode": "off", "set_mode": "off", **over}


@pytest.mark.parametrize(
    ("set_mode", "set_min", "expected"),
    [
        ("off", 0, True),
        ("off", 45, True),
        ("finn", 0, True),
        ("finn", 45, False),
    ],
)
def test_is_idle_target(set_mode, set_min, expected):
    state = _state(set_mode=set_mode, set_min=set_min)
    assert protocol.is_idle_target(state) is expected


def test_setpoint_change_is_staged_while_the_sauna_stands_idle():
    state = _state(set_mode="finn", set_min=0, set_temperature=90)
    assert protocol.should_push(state, {"set_temperature"}) is False


def test_staged_changes_are_sent_once_a_real_start_is_requested():
    state = _state(set_mode="finn", set_min=45)
    assert protocol.should_push(state, {"set_min"}) is True


def test_stopping_a_running_sauna_is_never_suppressed():
    """The stop request is itself an idle target -- it must still be sent."""
    for stop in ({"set_min": 0}, {"set_mode": "off"}):
        state = _state(mode="finn", set_mode="finn", set_min=45)
        state.update(stop)
        assert protocol.is_idle_target(state) is True
        assert protocol.should_push(state, set(stop)) is True


def test_setpoint_change_reaches_a_running_sauna_immediately():
    state = _state(mode="finn", set_mode="finn", set_min=45)
    assert protocol.should_push(state, {"set_temperature"}) is True


def test_first_poll_seeds_the_staged_setpoints():
    """A restart must recover set_min, or a later write truncates the session."""
    assert protocol.follows_controller(_state(mode="finn"), seeded=False) is True
    assert protocol.follows_controller(_state(mode="off"), seeded=False) is True


def test_a_running_sauna_owns_the_staged_setpoints():
    assert protocol.follows_controller(_state(mode="finn"), seeded=True) is True


def test_a_poll_never_wipes_a_session_staged_while_the_sauna_is_off():
    """Staging 40 min, then toggling a light, must not reset the 40 min."""
    assert protocol.follows_controller(_state(mode="off"), seeded=True) is False


def test_switches_are_never_staged():
    state = _state(set_mode="off", set_min=0)
    for key in const.SWITCH_KEYS:
        assert protocol.should_push(state, {key}) is True


def test_salt_wall_has_a_switch_and_round_trips_through_the_bitmask():
    assert "salt_wall" in const.SWITCH_KEYS
    payload = PAYLOAD[:13] + chr(0x08 + 48) + PAYLOAD[14:]
    data = protocol.decode_state(payload, hwversion=3)
    assert data["salt_wall"] is True
    assert data["light"] is False

    assert _encode(data)[ENC_LIGHT] == chr(0x08 + 48)


# --- guards against the class of bug that started this ---


def test_every_writable_key_exists_in_the_default_state():
    for key in const.WRITABLE_KEYS:
        assert key in const.DATA_TEMPLATE, f"{key} is writable but has no default"


def test_every_mirrored_setpoint_has_a_source_the_decoder_produces():
    data = _decoded()
    for staged, reported in const.PENDING_SOURCE.items():
        assert staged in const.DATA_TEMPLATE
        assert reported in data, f"{staged} mirrors {reported}, which is never decoded"
