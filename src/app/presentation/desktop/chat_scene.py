from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QVBoxLayout, QWidget


class ChatBackgroundWidget(QWidget):
    """
    Fixed decorative background for the central chat scene.

    The widget always stays behind the content layer, never scrolls,
    and scales the source image with a "cover" strategy while preserving
    aspect ratio.
    """

    def __init__(self, image_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._image_path = image_path
        self._source = QPixmap(str(image_path)) if image_path.exists() else QPixmap()
        self._scaled = QPixmap()
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAutoFillBackground(False)

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        self._rebuild_scaled_pixmap()
        super().resizeEvent(event)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.fillRect(self.rect(), QColor('#ffffff'))
        if not self._scaled.isNull():
            x = (self.width() - self._scaled.width()) // 2
            y = (self.height() - self._scaled.height()) // 2
            painter.drawPixmap(x, y, self._scaled)

    def _rebuild_scaled_pixmap(self) -> None:
        if self.width() <= 0 or self.height() <= 0 or self._source.isNull():
            self._scaled = QPixmap()
            return
        scale = max(self.width() / self._source.width(), self.height() / self._source.height())
        target_width = max(1, int(self._source.width() * scale))
        target_height = max(1, int(self._source.height() * scale))
        self._scaled = self._source.scaled(
            target_width,
            target_height,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation,
        )


class ChatSceneHost(QWidget):
    """
    Messenger-like scene host for the central working area.

    It keeps a fixed background layer under a full-size content layer.
    The content layer hosts filters, timeline and composer, while the
    background remains pinned and never participates in scrolling.
    """

    def __init__(self, image_path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName('centerSceneHost')
        self.setAutoFillBackground(False)

        self.background = ChatBackgroundWidget(image_path, self)
        self.background.setObjectName('centerSceneBackground')

        self.content = QWidget(self)
        self.content.setObjectName('centerSceneContent')
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(8, 12, 8, 12)
        self.content_layout.setSpacing(12)

        self._sync_layers()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        self._sync_layers()
        super().resizeEvent(event)

    def _sync_layers(self) -> None:
        rect = self.rect()
        self.background.setGeometry(rect)
        self.content.setGeometry(rect)
        self.background.lower()
        self.content.raise_()
