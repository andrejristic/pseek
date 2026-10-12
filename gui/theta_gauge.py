# =============================================================================
# PSEEK GUI — θ GAUGE
# A semicircular gauge for θ (0–100) with the healthy band [25,35] marked and a
# needle at the current value. Green in-band, amber/red out of band — the
# self/other balance at a glance.
# =============================================================================
from math import cos, sin, radians
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QFont
from PySide6.QtCore import Qt, QPointF

from theta import THETA_MIN, THETA_MAX, in_band, band_label


class ThetaGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._theta = 30.0
        self.setMinimumSize(220, 140)

    def set_theta(self, t):
        self._theta = max(0.0, min(100.0, float(t)))
        self.update()

    def _pt(self, cx, cy, r, frac):
        ang = radians(180 - 180 * frac)         # 0→left(180°), 100→right(0°)
        return QPointF(cx + r * cos(ang), cy - r * sin(ang))

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), QColor("#10141a"))
        w, h = self.width(), self.height()
        cx, cy, r = w / 2, h - 18, min(w / 2 - 12, h - 30)

        # base arc
        p.setPen(QPen(QColor("#3a4453"), 8))
        p.drawArc(int(cx - r), int(cy - r), int(2 * r), int(2 * r), 0, 180 * 16)
        # healthy band [25,35]
        p.setPen(QPen(QColor("#2ec4b6"), 8))
        start = 180 - 180 * (THETA_MAX / 100.0)
        span = 180 * ((THETA_MAX - THETA_MIN) / 100.0)
        p.drawArc(int(cx - r), int(cy - r), int(2 * r), int(2 * r),
                  int(start * 16), int(span * 16))

        # needle
        col = QColor("#2ec4b6") if in_band(self._theta) else QColor("#e71d36")
        p.setPen(QPen(col, 3))
        p.drawLine(QPointF(cx, cy), self._pt(cx, cy, r - 6, self._theta / 100.0))

        # labels
        p.setPen(QColor("#c7d0dc"))
        f = QFont(); f.setPointSize(11); f.setBold(True); p.setFont(f)
        p.drawText(self.rect().adjusted(0, 6, 0, 0), Qt.AlignHCenter | Qt.AlignTop,
                   f"θ {self._theta:.0f}")
        f2 = QFont(); f2.setPointSize(8); p.setFont(f2)
        p.setPen(QColor("#9aa7b8"))
        p.drawText(self.rect().adjusted(0, 0, 0, -2), Qt.AlignHCenter | Qt.AlignBottom,
                   band_label(self._theta))
        p.end()
