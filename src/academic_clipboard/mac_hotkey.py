"""Register a single Carbon hotkey, without a keyboard hook or Accessibility access."""

from __future__ import annotations

import ctypes as C
from collections.abc import Callable

# Apple HIToolbox Events.h virtual key codes (ANSI physical keyboard positions).
KEY_CODES = dict(
    zip(
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        (
            0,
            11,
            8,
            2,
            14,
            3,
            5,
            4,
            34,
            38,
            40,
            37,
            46,
            45,
            31,
            35,
            12,
            15,
            1,
            17,
            32,
            9,
            13,
            7,
            16,
            6,
            29,
            18,
            19,
            20,
            21,
            23,
            22,
            26,
            28,
            25,
        ),
    )
)
KEY_CODES.update({" ": 49, "\t": 48, "\r": 36, "\x1b": 53})
FUNCTION_KEYS = (122, 120, 99, 118, 96, 97, 98, 100, 101, 109, 103, 111, 105, 107, 113, 106, 64, 79, 80, 90)


class EventType(C.Structure):
    _fields_ = [("event_class", C.c_uint32), ("kind", C.c_uint32)]


class HotkeyID(C.Structure):
    _fields_ = [("signature", C.c_uint32), ("identifier", C.c_uint32)]


Handler = C.CFUNCTYPE(C.c_int32, C.c_void_p, C.c_void_p, C.c_void_p)


class MacHotkey:
    def __init__(self, callback: Callable[[], None]):
        self._callback = callback
        self._reference = C.c_void_p()
        self._handler = C.c_void_p()
        self._function = Handler(self._pressed)
        self._carbon = C.CDLL("/System/Library/Frameworks/Carbon.framework/Carbon")
        signatures = {
            "GetApplicationEventTarget": ([], C.c_void_p),
            "InstallEventHandler": (
                [C.c_void_p, Handler, C.c_uint32, C.POINTER(EventType), C.c_void_p, C.POINTER(C.c_void_p)],
                C.c_int32,
            ),
            "RegisterEventHotKey": (
                [C.c_uint32, C.c_uint32, HotkeyID, C.c_void_p, C.c_uint32, C.POINTER(C.c_void_p)],
                C.c_int32,
            ),
            "UnregisterEventHotKey": ([C.c_void_p], C.c_int32),
            "RemoveEventHandler": ([C.c_void_p], C.c_int32),
            "GetEventParameter": (
                [C.c_void_p, C.c_uint32, C.c_uint32, C.c_void_p, C.c_uint32, C.c_void_p, C.c_void_p],
                C.c_int32,
            ),
        }
        for name, (arguments, result) in signatures.items():
            function = getattr(self._carbon, name)
            function.argtypes, function.restype = arguments, result

    def _pressed(self, _call, event, _data) -> int:
        identifier = HotkeyID()
        status = self._carbon.GetEventParameter(
            event,
            int.from_bytes(b"----", "big"),
            int.from_bytes(b"hkid", "big"),
            None,
            C.sizeof(identifier),
            None,
            C.byref(identifier),
        )
        if status == 0 and identifier.signature == int.from_bytes(b"AcCb", "big"):
            self._callback()
            return 0
        return -9874  # eventNotHandledErr: do not swallow other applications' events.

    def start(self, modifiers: int, virtual_key: int) -> tuple[bool, str]:
        if 0x70 <= virtual_key <= 0x83:
            key = FUNCTION_KEYS[virtual_key - 0x70]
        else:
            key = KEY_CODES.get(chr(virtual_key))
        if key is None:
            return False, "unsupported macOS key (use A–Z, digits, Space or F1–F20)"
        # Windows-independent parser flags -> Carbon cmd/shift/option/control bits.
        flags = sum(bit for mask, bit in ((1, 2048), (2, 4096), (4, 512), (8, 256)) if modifiers & mask)
        target = self._carbon.GetApplicationEventTarget()
        event_type = EventType(int.from_bytes(b"keyb", "big"), 5)
        status = self._carbon.InstallEventHandler(
            target, self._function, 1, C.byref(event_type), None, C.byref(self._handler)
        )
        if status == 0:
            status = self._carbon.RegisterEventHotKey(
                key,
                flags,
                HotkeyID(int.from_bytes(b"AcCb", "big"), 1),
                target,
                0,
                C.byref(self._reference),
            )
        if status:
            self.stop()
            return False, f"macOS could not register hotkey (status {status}); try another combination"
        return True, ""

    def stop(self) -> None:
        if self._reference.value:
            self._carbon.UnregisterEventHotKey(self._reference)
            self._reference = C.c_void_p()
        if self._handler.value:
            self._carbon.RemoveEventHandler(self._handler)
            self._handler = C.c_void_p()
