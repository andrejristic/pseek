#!/usr/bin/env python3
# =============================================================================
# PSEEK — LAUNCHER (output #1: PySide6 source)
# Opens a per-user workspace, wires the LLM operator + entitlements, and shows the
# GUI (sidebar + right chat panel + θ gauge). Paywall pops for a post-trial free
# user. `--selfcheck` wires everything headless and prints status.
# =============================================================================
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def _workspaces_base():
    env = os.environ.get("PSEEK_WORKSPACES")
    if env:
        base = env
    elif getattr(sys, "frozen", False):
        if sys.platform == "win32":
            root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
        else:
            root = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
        base = os.path.join(root, "pseek", "workspaces")
    else:
        base = os.path.join(ROOT, "workspaces")
    os.makedirs(base, exist_ok=True)
    return base


def wire(user=None, passphrase=None):
    from workspace import Workspace
    from llm import LLMOperator
    from billing import EntitlementManager
    base = _workspaces_base()
    user = user or os.environ.get("PSEEK_USER", "demo")
    passphrase = passphrase or os.environ.get("PSEEK_PASSPHRASE", "pseek-dev-pass")
    ws = Workspace(base, user, passphrase)
    op = LLMOperator(ws.guardian)
    ent = EntitlementManager(ws.registry)
    return ws, op, ent


def selfcheck():
    ws, op, ent = wire()
    print("PSEEK self-check")
    print("  workspace :", ws.root)
    print("  llm status:", op.status())
    print("  tier      :", ent.effective_tier())
    print("  font size :", ws.settings.font_size)


def main():
    for _s in (sys.stdout, sys.stderr):   # emoji / non-ASCII output on Windows
        try:
            _s.reconfigure(encoding="utf-8")
        except Exception:
            pass
    if "--selfcheck" in sys.argv:
        selfcheck()
        return
    import json
    from PySide6.QtWidgets import QApplication
    from gui import build_window
    from discovery import Discovery
    from pool import load_pool
    from chat.pseek_chat import PseekChat
    ws, op, ent = wire()
    config = {}
    cfg = os.path.join(ROOT, "sources_config.json")
    if os.path.exists(cfg):
        with open(cfg, encoding="utf-8") as fh:
            config = json.load(fh)
    app = QApplication.instance() or QApplication(sys.argv)
    win = build_window(workspace=ws, operator=op, entitlements=ent)
    from synthesis import recommend
    from apply import ApplyArm
    from learning import SeldonEngine
    disc = Discovery(ws, config)

    def apply_cb(rec):
        pool = load_pool(ws.docs_dir, ws.guardian)
        combo = recommend(rec.job, pool)
        if combo is None:
            return {"status": "error", "reason": "no combination (add a résumé)"}
        name = ws.registry.get_pref("name", "Candidate")
        # the click IS the user's approval (physician); dry-run until email connected
        return ApplyArm(ws.guardian, ws.tracker).apply(
            rec.job, combo, pool, candidate_name=name, approved=True)

    def refresh_tabs():
        pool = load_pool(ws.docs_dir, ws.guardian)
        win.load_documents(pool)
        win.load_applications(ws.tracker)
        prefs = sorted(disc.prefs.w.items(), key=lambda kv: -abs(kv[1]))[:6]
        win.load_strategy(SeldonEngine().analyze(ws.tracker), disc.source_stats(), prefs)

    chat = PseekChat(ws, disc, lambda: load_pool(ws.docs_dir, ws.guardian),
                     operator=op, on_results=win.load_jobs, apply_cb=apply_cb)
    win.chat.handler = chat.handle          # "nađi poslove" drives the Poslovi tab
    win.auto_interval_min = int(config.get("refresh_minutes", 30))
    win.search_cb = chat._search            # auto-search runs the same search
    win.feedback_cb = disc.record_feedback  # table feedback rewards the source
    win.apply_cb = apply_cb                 # "Apliciraj" button runs the apply-arm
    win.refresh_tabs = refresh_tabs
    refresh_tabs()                          # populate Dokumenti/Prijave/Strategija now
    win.apply_optin_state()
    win.show()
    dlg = win.maybe_show_paywall()
    if dlg is not None:
        dlg.exec()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
