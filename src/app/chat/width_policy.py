from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtGui import QFontMetrics

from app.chat.models import ChatMessage


@dataclass(slots=True)
class BubbleWidthPolicy:
    min_width: int = 240
    outgoing_max_ratio: float = 0.48
    incoming_max_ratio: float = 0.62
    absolute_max_width: int = 760
    outer_row_padding: int = 48

    def resolve_width(self, *, viewport_width: int, message: ChatMessage, metrics: QFontMetrics) -> int:
        available = max(280, viewport_width - self.outer_row_padding)
        ratio = self.outgoing_max_ratio if message.role == 'outgoing_right' else self.incoming_max_ratio
        max_width = min(self.absolute_max_width, int(available * ratio))
        preferred = self._preferred_width(message, metrics)
        return max(self.min_width, min(max_width, preferred))

    def _preferred_width(self, message: ChatMessage, metrics: QFontMetrics) -> int:
        longest = 0
        for block in message.blocks:
            for line in block.text.splitlines() or ['']:
                text = line.strip()
                if not text:
                    continue
                soft_cap = min(len(text), 64)
                width = metrics.horizontalAdvance(text[:soft_cap]) + 64
                longest = max(longest, width)
        if longest <= 0:
            longest = self.min_width
        return max(self.min_width, longest)
