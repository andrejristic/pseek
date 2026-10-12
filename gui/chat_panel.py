# =============================================================================
# PSEEK GUI — RIGHT-HAND CHAT PANEL (~⅓ of the screen, always open)
# The control surface: the user runs the whole app by talking here. A handler
# turns text into an answer/action (deterministic command router first, then the
# LLM operator). Governed: whatever the chat proposes still passes θ / the floors
# / the physician downstream.
# =============================================================================
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTextEdit, QLineEdit, QLabel)


class ChatPanel(QWidget):
    def __init__(self, handler=None, operator=None, parent=None):
        super().__init__(parent)
        self.handler = handler
        self.operator = operator
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel("<b>Chat</b> — vodi aplikaciju razgovorom"))
        self.view = QTextEdit(); self.view.setReadOnly(True)
        lay.addWidget(self.view, 1)
        self.input = QLineEdit()
        self.input.setPlaceholderText("npr. nađi poslove · zašto #3 · pripremi #2 · poveži email")
        self.input.returnPressed.connect(self.send)
        lay.addWidget(self.input)

    def _answer(self, text):
        if self.handler is not None:
            return self.handler(text)
        if self.operator is not None:
            return self.operator.complete([{"role": "user", "content": text}])["text"]
        return "…"

    def send(self, text=None):
        t = (text if text is not None else self.input.text()).strip()
        if not t:
            return
        resp = self._answer(t)
        self.view.append(f"<b>ti:</b> {t}")
        self.view.append("<b>pse:</b> " + str(resp).replace("\n", "<br>"))
        self.input.clear()
        return resp
