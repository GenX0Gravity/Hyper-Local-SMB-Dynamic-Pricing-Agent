"""Inbound WhatsApp command parser."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


class CommandType(str, Enum):
    APPROVE = "approve"
    REJECT = "reject"
    APPROVE_ALL = "approve_all"
    REJECT_ALL = "reject_all"
    AUTO_ON = "auto_on"
    AUTO_OFF = "auto_off"
    SUMMARY = "summary"
    STATUS = "status"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    type: CommandType
    index: int | None = None  # 1-based item number


class InboundCommandParser:
    """Parse owner replies: APPROVE, REJECT 2, YES, NO, AUTO ON, etc."""

    _APPROVE_ALL = re.compile(
        r"^(approve\s*all|yes\s*all|accept\s*all|ok\s*all)$", re.I
    )
    _REJECT_ALL = re.compile(
        r"^(reject\s*all|no\s*all|decline\s*all|cancel\s*all)$", re.I
    )
    _APPROVE = re.compile(
        r"^(approve|yes|ok|accept|confirm)(\s+(\d+))?$", re.I
    )
    _REJECT = re.compile(
        r"^(reject|no|decline|cancel|skip)(\s+(\d+))?$", re.I
    )
    _AUTO_ON = re.compile(r"^(auto\s*on|auto-approve\s*on|autoon)$", re.I)
    _AUTO_OFF = re.compile(r"^(auto\s*off|auto-approve\s*off|autooff)$", re.I)
    _SUMMARY = re.compile(r"^(summary|report|daily)$", re.I)
    _STATUS = re.compile(r"^(status|pending)$", re.I)
    _HELP = re.compile(r"^(help|\?|commands)$", re.I)
    _DIGIT_ONLY = re.compile(r"^(\d+)$")

    def parse(self, body: str) -> ParsedCommand:
        text = (body or "").strip()
        if not text:
            return ParsedCommand(CommandType.UNKNOWN)

        if self._HELP.match(text):
            return ParsedCommand(CommandType.HELP)
        if self._SUMMARY.match(text):
            return ParsedCommand(CommandType.SUMMARY)
        if self._STATUS.match(text):
            return ParsedCommand(CommandType.STATUS)
        if self._AUTO_ON.match(text):
            return ParsedCommand(CommandType.AUTO_ON)
        if self._AUTO_OFF.match(text):
            return ParsedCommand(CommandType.AUTO_OFF)
        if self._APPROVE_ALL.match(text):
            return ParsedCommand(CommandType.APPROVE_ALL)
        if self._REJECT_ALL.match(text):
            return ParsedCommand(CommandType.REJECT_ALL)

        m = self._APPROVE.match(text)
        if m:
            idx = int(m.group(3)) if m.group(3) else None
            return ParsedCommand(CommandType.APPROVE, index=idx)

        m = self._REJECT.match(text)
        if m:
            idx = int(m.group(3)) if m.group(3) else None
            return ParsedCommand(CommandType.REJECT, index=idx)

        m = self._DIGIT_ONLY.match(text)
        if m:
            return ParsedCommand(CommandType.APPROVE, index=int(m.group(1)))

        return ParsedCommand(CommandType.UNKNOWN)
