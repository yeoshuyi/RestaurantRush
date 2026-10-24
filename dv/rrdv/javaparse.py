"""Bit-exact Python versions of the Java library behaviour the game relies on.

The reference model must interpret input lines and format numbers exactly as
the JVM does, otherwise the scoreboard reports false mismatches.
"""

from __future__ import annotations

import unicodedata
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, List

INT_MIN = -(2 ** 31)
INT_MAX = 2 ** 31 - 1


def java_trim(s: str) -> str:
    """String.trim(): strips every char <= U+0020 from both ends."""
    start, end = 0, len(s)
    while start < end and ord(s[start]) <= 0x20:
        start += 1
    while end > start and ord(s[end - 1]) <= 0x20:
        end -= 1
    return s[start:end]


def java_parse_int(s: str) -> int:
    """Integer.parseInt(s, 10). Raises ValueError where Java throws NumberFormatException.

    Java accepts a single leading '+' or '-' followed by one or more chars for
    which Character.digit(c, 10) != -1 (any Unicode Nd digit), within int32.
    """
    if not s:
        raise ValueError("empty")
    sign = 1
    body = s
    if s[0] in "+-":
        sign = -1 if s[0] == "-" else 1
        body = s[1:]
    if not body:
        raise ValueError("sign only")
    value = 0
    for ch in body:
        if unicodedata.category(ch) != "Nd":
            raise ValueError(f"bad digit {ch!r}")
        value = value * 10 + unicodedata.decimal(ch)
    value *= sign
    if value < INT_MIN or value > INT_MAX:
        raise ValueError("overflow")
    return value


def split_java_lines(text: str) -> List[str]:
    """BufferedReader.readLine() splitting: \\n, \\r or \\r\\n terminate a line."""
    lines: List[str] = []
    buf: List[str] = []
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if ch == "\n" or ch == "\r":
            lines.append("".join(buf))
            buf = []
            if ch == "\r" and i + 1 < n and text[i + 1] == "\n":
                i += 1
        else:
            buf.append(ch)
        i += 1
    if buf:
        lines.append("".join(buf))
    return lines


def format_money(cents: int) -> str:
    """rush.model.Money.format."""
    sign = "-" if cents < 0 else ""
    a = abs(cents)
    return f"{sign}${a // 100}.{a % 100:02d}"


def parse_money(text: str) -> int:
    neg = text.startswith("-")
    t = text.lstrip("-")
    if not t.startswith("$"):
        raise ValueError(text)
    dollars, cents = t[1:].split(".")
    v = int(dollars) * 100 + int(cents)
    return -v if neg else v


def java_format_1dp(x: float) -> str:
    """String.format(Locale.ROOT, "%.1f", x): HALF_UP on the shortest decimal repr."""
    return str(Decimal(repr(float(x))).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def format_average(values: Iterable[int]) -> str:
    """ConsoleUI.formatAverage(IntStream.average())."""
    vals = list(values)
    if not vals:
        return "N/A"
    return java_format_1dp(sum(vals) / len(vals))
