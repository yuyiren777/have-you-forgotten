"""Consistent, high-visibility checkbox used across the application."""

from PyQt5.QtCore import QPointF, QSize, Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPen
from PyQt5.QtWidgets import QApplication, QCheckBox


class ModernCheckBox(QCheckBox):
    """Draw a stable checkbox instead of relying on the host OS theme."""

    INDICATOR_SIZE = 22
    TEXT_GAP = 10

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumHeight(32)
        self.setMinimumWidth(self.INDICATOR_SIZE + 6)

    def sizeHint(self) -> QSize:
        text_width = self.fontMetrics().horizontalAdvance(self.text())
        width = self.INDICATOR_SIZE + (self.TEXT_GAP + text_width if self.text() else 0) + 4
        return QSize(width, max(32, self.fontMetrics().height() + 10))

    def hitButton(self, position) -> bool:
        """Treat the whole painted control as clickable.

        QCheckBox otherwise delegates hit testing to the platform style, whose
        native indicator can be much smaller than our 22 px painted indicator.
        """
        return self.rect().contains(position)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        dark = self._uses_dark_theme()
        enabled = self.isEnabled()
        checked = self.isChecked()
        hovered = self.underMouse() and enabled

        top = (self.height() - self.INDICATOR_SIZE) / 2
        indicator = self.rect().adjusted(2, int(top), 0, 0)
        indicator.setWidth(self.INDICATOR_SIZE)
        indicator.setHeight(self.INDICATOR_SIZE)

        if checked:
            fill = QColor("#2F9089" if dark else "#2B7A78")
            border = QColor("#5EC3BA" if hovered else fill.name())
        else:
            fill = QColor("#243033" if dark else "#FFFFFF")
            if hovered:
                fill = QColor("#29413F" if dark else "#E8F4F2")
            border = QColor("#88A09F" if dark else "#718891")

        if not enabled:
            fill.setAlpha(115)
            border.setAlpha(115)

        painter.setPen(QPen(border, 2.0))
        painter.setBrush(fill)
        painter.drawRoundedRect(indicator, 5, 5)

        if checked:
            check = QPainterPath(QPointF(indicator.left() + 5.0, indicator.center().y()))
            check.lineTo(QPointF(indicator.left() + 9.0, indicator.bottom() - 5.5))
            check.lineTo(QPointF(indicator.right() - 4.5, indicator.top() + 5.0))
            painter.setPen(QPen(QColor("#FFFFFF"), 2.6, Qt.PenStyle.SolidLine,
                                Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPath(check)

        if self.hasFocus():
            focus = indicator.adjusted(-2, -2, 2, 2)
            painter.setPen(QPen(QColor("#63BDB6"), 1.2, Qt.PenStyle.DotLine))
            painter.drawRoundedRect(focus, 6, 6)

        if self.text():
            text_rect = self.rect().adjusted(
                self.INDICATOR_SIZE + self.TEXT_GAP + 2, 0, -2, 0
            )
            text_color = QColor("#E4ECEA" if dark else "#26343F")
            if not enabled:
                text_color.setAlpha(120)
            painter.setPen(text_color)
            painter.drawText(
                text_rect,
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self.text(),
            )

    def _uses_dark_theme(self) -> bool:
        """Detect the active QSS theme; Qt does not always update child palettes."""
        app = QApplication.instance()
        if app and self._is_dark_stylesheet(app.styleSheet()):
            return True
        widget = self
        while widget is not None:
            if self._is_dark_stylesheet(widget.styleSheet()):
                return True
            widget = widget.parentWidget()
        return False

    @staticmethod
    def _is_dark_stylesheet(stylesheet: str) -> bool:
        return "night theme" in stylesheet or "background: #171D1F" in stylesheet
