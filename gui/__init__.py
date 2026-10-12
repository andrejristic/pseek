"""PSEEK PySide6 GUI: sidebar shell + right chat panel + θ gauge."""
from .shell import MainWindow, build_window, PaywallDialog
from .theta_gauge import ThetaGauge
from .chat_panel import ChatPanel

__all__ = ["MainWindow", "build_window", "PaywallDialog", "ThetaGauge", "ChatPanel"]
