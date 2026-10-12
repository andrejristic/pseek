# =============================================================================
# PSEEK GUI — MAIN WINDOW SHELL
# Left sidebar navigation · center stacked pages · right always-open chat panel
# (~⅓). A θ gauge on the dashboard, a paywall dialog, an in-app font-size control
# (default 20, persisted), and screen-fit so the window never overflows the
# display. Dark/light theme via QSS.
# =============================================================================
import os
import tempfile

from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                               QListWidget, QStackedWidget, QLabel, QPushButton,
                               QToolBar, QDialog, QGridLayout, QTableWidget,
                               QTableWidgetItem, QHeaderView, QAbstractItemView,
                               QCheckBox)
from PySide6.QtGui import QFont, QGuiApplication, QAction
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QTimer

from settings import AppSettings
from .theme import qss
from .theta_gauge import ThetaGauge
from .chat_panel import ChatPanel

NAV = ["Dashboard", "Poslovi", "Dokumenti", "Prijave", "Strategija", "Settings"]


def _page(title):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.addWidget(QLabel(f"<h2>{title}</h2>"))
    return w, lay


class PaywallDialog(QDialog):
    def __init__(self, paywall, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PSEEK — pretplata")
        self.choice = None
        g = QGridLayout(self)
        g.addWidget(QLabel("<b>Izaberi plan</b> (prvih 24h sve je uključeno)"), 0, 0, 1, 3)
        for i, opt in enumerate(paywall["options"]):
            price = "besplatno" if opt["price"] == 0 else f"${opt['price']:.2f}/mj"
            b = QPushButton(f"{opt['tier'].upper()} — {price}\n{opt['blurb']}")
            b.clicked.connect(lambda _=False, t=opt["tier"]: self._pick(t))
            g.addWidget(b, 1, i)

    def _pick(self, tier):
        self.choice = tier
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self, workspace=None, operator=None, entitlements=None,
                 chat_handler=None):
        super().__init__()
        self.setWindowTitle("PSEEK")
        self.workspace = workspace
        self.entitlements = entitlements
        self.settings = (workspace.settings if workspace
                         else AppSettings(os.path.join(tempfile.mkdtemp(), "settings.json")))

        # opt-in feature wiring (both OFF until the user turns them on)
        self.search_cb = None            # set by the app: run a multi-source search
        self.feedback_cb = None          # set by the app: reward source / learn
        self.apply_cb = None             # set by the app: run the apply-arm for a job
        self.refresh_tabs = None         # set by the app: refresh docs/apps/strategy
        self._jobs_records = []
        self.auto_interval_min = int(self.settings.get("auto_search_minutes", 30))
        self.auto_timer = QTimer(self)
        self.auto_timer.timeout.connect(self._auto_tick)

        central = QWidget()
        row = QHBoxLayout(central)
        row.setContentsMargins(0, 0, 0, 0)

        # ---- left sidebar ----
        self.nav = QListWidget(); self.nav.setObjectName("nav")
        self.nav.setFixedWidth(190)
        self.nav.addItems(NAV)
        self.nav.currentRowChanged.connect(lambda i: self.stack.setCurrentIndex(i))
        row.addWidget(self.nav)

        # ---- center stacked pages ----
        self.stack = QStackedWidget()
        self._build_pages()
        row.addWidget(self.stack, 2)          # center gets 2/3 of the flexible space

        # ---- right chat panel (~⅓) ----
        self.chat = ChatPanel(handler=chat_handler, operator=operator)
        row.addWidget(self.chat, 1)           # chat gets ~1/3

        self.setCentralWidget(central)
        self.nav.setCurrentRow(0)

        self._build_toolbar()
        self.setStyleSheet(qss(self.settings.get("theme", "dark")))
        self.apply_font()
        self.resize(self.settings.get("window_w", 1280), self.settings.get("window_h", 800))

    # ---- pages -------------------------------------------------------------
    def _build_pages(self):
        # Dashboard
        w, lay = _page("Dashboard")
        self.gauge = ThetaGauge()
        lay.addWidget(self.gauge)
        self.dash_info = QLabel("Dobrodošao u PSEEK.")
        self.dash_info.setWordWrap(True)
        lay.addWidget(self.dash_info)
        lay.addStretch(1)
        self.stack.addWidget(w)
        # Poslovi (Jobs) — a real table populated by Discovery
        jp, jl = _page("Poslovi")
        self.jobs_hint = QLabel("Reci u chatu: <b>nađi poslove</b>")
        jl.addWidget(self.jobs_hint)

        # opt-in options (OFF by default; only active when the user turns them on)
        opts = QHBoxLayout()
        self.cb_auto = QCheckBox("Auto-pretraga (periodično sam traži)")
        self.cb_learn = QCheckBox("Uči iz mojih ocjena (nagradi izvor)")
        self.cb_auto.setChecked(bool(self.settings.get("auto_search", False)))
        self.cb_learn.setChecked(bool(self.settings.get("feedback_learning", False)))
        self.cb_auto.toggled.connect(self._toggle_auto)
        self.cb_learn.toggled.connect(self._toggle_learn)
        opts.addWidget(self.cb_auto); opts.addWidget(self.cb_learn); opts.addStretch(1)
        jl.addLayout(opts)

        self.jobs_table = QTableWidget(0, 5)
        self.jobs_table.setHorizontalHeaderLabels(
            ["Verdikt", "Posao", "Firma", "Lokacija", "Fit"])
        self.jobs_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.jobs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.jobs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        jl.addWidget(self.jobs_table)

        # feedback buttons (act on the selected row; reward only when learning is on)
        fb = QHBoxLayout()
        b_ap = QPushButton("✅ Odobri"); b_rj = QPushButton("✕ Odbij")
        b_send = QPushButton("✉ Apliciraj")
        b_ap.clicked.connect(lambda: self._feedback("approve"))
        b_rj.clicked.connect(lambda: self._feedback("reject"))
        b_send.clicked.connect(self._apply)
        for b in (b_ap, b_rj, b_send):
            fb.addWidget(b)
        fb.addStretch(1)
        jl.addLayout(fb)
        self.jobs_status = QLabel(""); jl.addWidget(self.jobs_status)
        self.stack.addWidget(jp)

        # Dokumenti — the user's document pool (résumés + covers)
        dp, dl = _page("Dokumenti")
        self.docs_hint = QLabel("Dodaj fajlove u docs/ ili u chatu reci: "
                                "<b>generiši rezime …</b>")
        dl.addWidget(self.docs_hint)
        self.docs_list = QListWidget()
        dl.addWidget(self.docs_list)
        self.stack.addWidget(dp)

        # Prijave — the application tracker
        pp, pl = _page("Prijave")
        self.apps_table = QTableWidget(0, 4)
        self.apps_table.setHorizontalHeaderLabels(["Posao", "Firma", "Profil", "Status"])
        self.apps_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.apps_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        pl.addWidget(self.apps_table)
        self.stack.addWidget(pp)

        # Strategija — what the system has learned (Seldon + sources + prefs)
        sp, sl = _page("Strategija")
        self.strategy_label = QLabel("Nema još podataka — traži i ocjenjuj poslove "
                                     "pa se strategija uči.")
        self.strategy_label.setWordWrap(True)
        self.strategy_label.setTextFormat(Qt.RichText)
        sl.addWidget(self.strategy_label); sl.addStretch(1)
        self.stack.addWidget(sp)

        # Settings — what the user plugs in (keys/email) + look & feel
        setp, setl = _page("Settings")
        self.settings_label = QLabel(
            "<b>Da uključiš punu snagu, ubaci svoje:</b><br>"
            "• LLM ključ (Groq/Mistral/Claude) — bogatiji chat/generisanje<br>"
            "• Email nalog — da se prijave stварno šalju (Connect email)<br>"
            "• Job-API ključ (Adzuna/LinkedIn/Indeed) — više izvora<br>"
            "• Square (prodavac) — naplata<br><br>"
            "Font: <b>A− / A+</b> u toolbaru (default 20) · Tema: <b>◐</b>.")
        self.settings_label.setWordWrap(True)
        setl.addWidget(self.settings_label); setl.addStretch(1)
        self.stack.addWidget(setp)

    def _build_toolbar(self):
        tb = QToolBar(); self.addToolBar(tb)
        a_minus = QAction("A−", self); a_minus.triggered.connect(lambda: self.change_font(-1))
        a_plus = QAction("A+", self); a_plus.triggered.connect(lambda: self.change_font(+1))
        a_theme = QAction("◐ tema", self); a_theme.triggered.connect(self.toggle_theme)
        for a in (a_minus, a_plus, a_theme):
            tb.addAction(a)

    # ---- font (in-app, persisted, default 20) ------------------------------
    def apply_font(self):
        app = QApplication.instance()
        if app is not None:
            f = QFont(); f.setPointSize(self.settings.font_size)
            app.setFont(f)

    def change_font(self, delta):
        self.settings.bump_font(delta)
        self.apply_font()

    def toggle_theme(self):
        new = "light" if self.settings.get("theme", "dark") == "dark" else "dark"
        self.settings.set("theme", new)
        self.setStyleSheet(qss(new))

    # ---- screen-fit (never overflow the display) ---------------------------
    def fit_to_screen(self, avail_w, avail_h):
        w = min(int(self.settings.get("window_w", 1280)), int(avail_w * 0.95))
        h = min(int(self.settings.get("window_h", 800)), int(avail_h * 0.95))
        self.resize(w, h)
        return w, h

    def showEvent(self, ev):
        scr = QGuiApplication.primaryScreen()
        if scr is not None:
            geo = scr.availableGeometry()
            self.fit_to_screen(geo.width(), geo.height())
        super().showEvent(ev)

    # ---- app hooks ---------------------------------------------------------
    def set_theta(self, t):
        self.gauge.set_theta(t)

    def _apply(self):
        """Apliciraj: run the apply-arm for the selected job (consent is this click)."""
        rec = self._selected_record()
        if rec is None:
            self.jobs_status.setText("Izaberi posao u tabeli.")
            return
        if self.apply_cb is None:
            self.jobs_status.setText("Apply nije povezan.")
            return
        res = self.apply_cb(rec)
        status = res.get("status") if isinstance(res, dict) else res
        msg = {"sent": "poslato ✉", "dry_run": "draft spreman (poveži email da se pošalje)",
               "escalate": "čeka tvoje odobrenje", "error": "greška"}.get(status, str(status))
        self.jobs_status.setText(f"Apliciraj → {msg}: {rec.title} @ {rec.company}")
        if self.refresh_tabs is not None:
            self.refresh_tabs()

    def load_documents(self, pool):
        self.docs_list.clear()
        for r in pool.resumes:
            self.docs_list.addItem(f"📄 [rezime] {r.name} — {len(r.lines)} linija")
        for c in pool.covers:
            self.docs_list.addItem(f"✉ [cover] {c.name} — {len(c.paragraphs)} pasusa")
        self.docs_hint.setText(f"<b>{len(pool.resumes)}</b> rezimea · "
                               f"<b>{len(pool.covers)}</b> covera "
                               f"(dodaj u docs/ ili generiši u chatu)")

    def load_applications(self, tracker):
        try:
            from tracking import STATES
        except Exception:
            STATES = []
        apps = tracker.all()
        if STATES:
            apps.sort(key=lambda a: STATES.index(a["state"]) if a["state"] in STATES else 99)
        self.apps_table.setRowCount(len(apps))
        for i, a in enumerate(apps):
            cells = [a.get("title", ""), a.get("company", ""), a.get("profile", ""),
                     a.get("state", "")]
            for j, c in enumerate(cells):
                self.apps_table.setItem(i, j, QTableWidgetItem(str(c)))

    def load_strategy(self, analysis=None, source_stats=None, prefs_top=None):
        parts = []
        if analysis:
            o = analysis.get("overall", {})
            parts.append(f"<b>Ishodi:</b> poslato {o.get('sent',0)}, "
                         f"response {int(o.get('response_rate',0)*100)}%, "
                         f"offer {int(o.get('offer_rate',0)*100)}%.")
            if analysis.get("recommend_profile"):
                parts.append(f"Preporuka profila: <b>{analysis['recommend_profile']}</b>.")
        if source_stats:
            best = sorted(source_stats, key=lambda s: source_stats[s]["mean"], reverse=True)[:4]
            parts.append("<b>Najbolji izvori (uči se):</b> "
                         + ", ".join(f"{s} ({source_stats[s]['mean']:.2f})" for s in best))
        if prefs_top:
            parts.append("<b>Tvoje preference:</b> "
                         + ", ".join(f"{k} {v:+.1f}" for k, v in prefs_top))
        self.strategy_label.setText("<br>".join(parts) if parts
                                    else "Nema još podataka — traži i ocjenjuj poslove.")

    # ---- opt-in: feedback from the table + auto-search --------------------
    def _selected_record(self):
        rows = self.jobs_table.selectionModel().selectedRows()
        if not rows or not self._jobs_records:
            return None
        idx = rows[0].row()
        return self._jobs_records[idx] if 0 <= idx < len(self._jobs_records) else None

    def _feedback(self, action):
        rec = self._selected_record()
        if rec is None:
            self.jobs_status.setText("Izaberi posao u tabeli.")
            return
        if action in ("approve", "reject") and not self.cb_learn.isChecked():
            self.jobs_status.setText("Uključi 'Uči iz mojih ocjena' da ocjene "
                                     "nagrađuju izvor.")
            return
        if self.feedback_cb is not None:
            self.feedback_cb(rec, action)
        self.jobs_status.setText(f"Zabilježeno: {action} — {rec.title} @ {rec.company}")

    def _toggle_learn(self, checked):
        self.settings.set("feedback_learning", bool(checked))

    def _toggle_auto(self, checked):
        self.settings.set("auto_search", bool(checked))
        if checked and self.search_cb is not None:
            self.auto_timer.start(max(60000, self.auto_interval_min * 60 * 1000))
            self.jobs_status.setText(
                f"Auto-pretraga UKLJUČENA (svakih {self.auto_interval_min} min).")
        else:
            self.auto_timer.stop()
            if not checked:
                self.jobs_status.setText("Auto-pretraga isključena.")

    def _auto_tick(self):
        if self.search_cb is not None:
            try:
                self.search_cb()
            except Exception:
                pass

    def apply_optin_state(self):
        """Call after search_cb is set, to honour a persisted auto-search=on."""
        if self.cb_auto.isChecked():
            self._toggle_auto(True)

    def load_jobs(self, records):
        """Populate the Poslovi tab from Discovery results."""
        from PySide6.QtGui import QColor
        self._jobs_records = list(records)
        self.jobs_hint.setText(f"<b>{len(records)}</b> poslova (pretraženo više izvora)")
        self.jobs_table.setRowCount(len(records))
        for i, r in enumerate(records):
            fit = max(r.fit_by_profile.values()) if r.fit_by_profile else 0.0
            cells = [r.verdict_code, r.title, r.company,
                     r.how_to_apply.get("location", ""), f"{fit:.2f}"]
            for j, c in enumerate(cells):
                item = QTableWidgetItem(str(c))
                if j == 0:
                    item.setForeground(QColor("#2ec4b6") if r.verdict_code == "APPLY"
                                       else QColor("#e71d36"))
                self.jobs_table.setItem(i, j, item)

    def maybe_show_paywall(self):
        if self.entitlements is None:
            return None
        if self.entitlements.effective_tier() == "free":
            dlg = PaywallDialog(self.entitlements.paywall(), self)
            return dlg
        return None


def build_window(workspace=None, operator=None, entitlements=None, chat_handler=None):
    return MainWindow(workspace, operator, entitlements, chat_handler)
