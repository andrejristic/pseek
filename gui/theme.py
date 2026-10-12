# =============================================================================
# PSEEK GUI — THEME (QSS) for light and dark
# =============================================================================

def qss(theme="dark"):
    if theme == "light":
        return """
        QMainWindow, QWidget { background:#f4f6f9; color:#1b2430; }
        QListWidget#nav { background:#e9edf3; border:0; }
        QListWidget#nav::item { padding:12px 16px; }
        QListWidget#nav::item:selected { background:#d5deea; color:#0b2f6b; }
        QTextEdit, QLineEdit { background:#ffffff; border:1px solid #ccd3de; }
        QLabel { color:#1b2430; }
        QPushButton { background:#e1e7f0; border:1px solid #ccd3de; padding:6px 12px; border-radius:6px; }
        """
    return """
    QMainWindow, QWidget { background:#0b0e12; color:#c7d0dc; }
    QListWidget#nav { background:#10141a; border:0; }
    QListWidget#nav::item { padding:12px 16px; color:#9aa7b8; }
    QListWidget#nav::item:selected { background:#1f2a3a; color:#e6edf5; }
    QTextEdit, QLineEdit { background:#10141a; border:1px solid #222a35; color:#c7d0dc; }
    QLabel { color:#c7d0dc; }
    QPushButton { background:#161b23; border:1px solid #222a35; padding:6px 12px; border-radius:6px; color:#c7d0dc; }
    QPushButton:hover { background:#222a35; }
    """
