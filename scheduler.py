#!/usr/bin/env python3
"""
scheduler.py  —  SCMA Email Notification Scheduler
Run independently: python scheduler.py
Or via cron:  */5 * * * * /path/to/venv/bin/python /path/to/scheduler.py

Reads pending notifications from Supabase, sends via Resend or SendGrid,
marks as sent/failed. Runs safely in a loop every 5 minutes.

SETUP
─────
1. Install deps:  pip install supabase resend python-dotenv pytz
2. Set env vars (or create .env):
   SUPABASE_URL=https://xxx.supabase.co
   SUPABASE_SERVICE_KEY=your-service-role-key   ← use service key, NOT anon
   EMAIL_PROVIDER=resend                          ← or "sendgrid"
   EMAIL_API_KEY=re_xxxx                          ← Resend or SendGrid API key
   EMAIL_FROM=noreply@sophieagency.com
"""

from __future__ import annotations

import os
import sys
import time
import logging
from datetime import datetime, timezone

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("scma-scheduler")

# ── Load env ──────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPABASE_URL     = os.environ.get("SUPABASE_URL","")
SUPABASE_KEY     = os.environ.get("SUPABASE_SERVICE_KEY","")
EMAIL_PROVIDER   = os.environ.get("EMAIL_PROVIDER","resend").lower()
EMAIL_API_KEY    = os.environ.get("EMAIL_API_KEY","")
EMAIL_FROM       = os.environ.get("EMAIL_FROM","noreply@sophieagency.com")
POLL_INTERVAL_S  = int(os.environ.get("POLL_INTERVAL_S","300"))    # 5 minutes


# ── Supabase client (service role — bypasses RLS) ─────────────
def _get_db():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Email sending ─────────────────────────────────────────────

def _send_resend(to: str, subject: str, body: str) -> bool:
    import resend
    resend.api_key = EMAIL_API_KEY
    try:
        resend.Emails.send({
            "from":    EMAIL_FROM,
            "to":      [to],
            "subject": subject,
            "text":    body,
        })
        return True
    except Exception as e:
        log.error("Resend error: %s", e)
        return False


def _send_sendgrid(to: str, subject: str, body: str) -> bool:
    import sendgrid
    from sendgrid.helpers.mail import Mail
    sg = sendgrid.SendGridAPIClient(api_key=EMAIL_API_KEY)
    msg = Mail(
        from_email    = EMAIL_FROM,
        to_emails     = to,
        subject       = subject,
        plain_text_content = body,
    )
    try:
        resp = sg.send(msg)
        return resp.status_code in (200, 201, 202)
    except Exception as e:
        log.error("SendGrid error: %s", e)
        return False


def send_email(to: str, subject: str, body: str) -> bool:
    if EMAIL_PROVIDER == "sendgrid":
        return _send_sendgrid(to, subject, body)
    return _send_resend(to, subject, body)


# ── Notification processing ───────────────────────────────────

def _format_message(notif: dict) -> tuple[str, str]:
    """Return (subject, body) for a notification row."""
    ntype   = notif.get("type","")
    message = notif.get("message","")
    subject_map = {
        "event_start":  "SCMA — Event Starting Today",
        "match_start":  "SCMA — Match Today",
        "registration": "SCMA — Registration Window Update",
        "auction":      "SCMA — Auction Tomorrow",
    }
    subject = subject_map.get(ntype, "SCMA Calendar Notification")
    body    = f"""Hello,

{message}

—
SCMA Calendar Dashboard
Sophie Agency
"""
    return subject, body


def process_pending(db) -> int:
    """Fetch due pending notifications and send them. Returns count sent."""
    now = datetime.now(timezone.utc).isoformat()
    try:
        resp = (
            db.table("notifications")
            .select("*")
            .eq("status","pending")
            .lte("scheduled_at", now)
            .order("scheduled_at")
            .limit(50)
            .execute()
        )
        notifs = resp.data or []
    except Exception as e:
        log.error("DB fetch error: %s", e)
        return 0

    sent = 0
    for n in notifs:
        to      = n.get("user_email","")
        subject, body = _format_message(n)

        if not to:
            log.warning("Notification %s has no recipient — skipping.", n["id"])
            _mark(db, n["id"], "failed")
            continue

        log.info("Sending [%s] to %s  id=%s", n.get("type"), to, n["id"])
        ok = send_email(to, subject, body)

        if ok:
            _mark(db, n["id"], "sent")
            sent += 1
        else:
            _mark(db, n["id"], "failed")

    return sent


def _mark(db, notif_id: int, status: str) -> None:
    update = {"status": status}
    if status == "sent":
        update["sent_at"] = datetime.now(timezone.utc).isoformat()
    try:
        db.table("notifications").update(update).eq("id", notif_id).execute()
    except Exception as e:
        log.error("Could not mark notification %s as %s: %s", notif_id, status, e)


# ── Scheduling helpers — called when creating entities ────────

def schedule_event(db, event_row: dict, recipients: list[str]) -> None:
    """Queue same-day morning notification for an event."""
    import pytz
    start = event_row.get("start_date")
    if not start:
        return
    if isinstance(start, str):
        from datetime import date as dt_date
        import pandas as pd
        start = pd.to_datetime(start).date()
    from datetime import time as dt_time
    send_at = datetime(start.year, start.month, start.day, 7, 0, 0, tzinfo=timezone.utc)
    for email in recipients:
        try:
            db.table("notifications").insert({
                "user_email":   email,
                "type":         "event_start",
                "entity_id":    event_row["id"],
                "entity_type":  "event",
                "message":      f"Event starting today: {event_row.get('event_name','')}",
                "status":       "pending",
                "scheduled_at": send_at.isoformat(),
            }).execute()
        except Exception:
            pass   # likely duplicate — UNIQUE constraint prevents double send


def schedule_match(db, match_row: dict, recipients: list[str]) -> None:
    import pandas as pd
    m_date = match_row.get("match_date")
    if not m_date:
        return
    if isinstance(m_date, str):
        m_date = pd.to_datetime(m_date).date()
    from datetime import time as dt_time
    send_at = datetime(m_date.year, m_date.month, m_date.day, 7, 0, 0, tzinfo=timezone.utc)
    for email in recipients:
        try:
            db.table("notifications").insert({
                "user_email":   email,
                "type":         "match_start",
                "entity_id":    match_row["id"],
                "entity_type":  "match",
                "message":      f"Match today: {match_row.get('match_name','Match')}",
                "status":       "pending",
                "scheduled_at": send_at.isoformat(),
            }).execute()
        except Exception:
            pass


def schedule_registration(db, reg_row: dict, recipients: list[str]) -> None:
    """2 days before start and 2 days before deadline."""
    import pandas as pd
    from datetime import timedelta
    for field, label in [("start_date","Registration window opens"), ("deadline","Registration deadline")]:
        raw = reg_row.get(field)
        if not raw:
            continue
        if isinstance(raw, str):
            raw = pd.to_datetime(raw).date()
        send_at = datetime(raw.year, raw.month, raw.day, 7, 0, 0, tzinfo=timezone.utc)
        send_at -= timedelta(days=2)
        for email in recipients:
            try:
                db.table("notifications").insert({
                    "user_email":   email,
                    "type":         "registration",
                    "entity_id":    reg_row["id"],
                    "entity_type":  "registration",
                    "message":      f"{label} in 2 days (event id {reg_row.get('event_id','')})",
                    "status":       "pending",
                    "scheduled_at": send_at.isoformat(),
                }).execute()
            except Exception:
                pass


def schedule_auction(db, auction_row: dict, recipients: list[str]) -> None:
    """1 day before auction date."""
    import pandas as pd
    from datetime import timedelta
    raw = auction_row.get("auction_date")
    if not raw:
        return
    if isinstance(raw, str):
        raw = pd.to_datetime(raw).date()
    send_at = datetime(raw.year, raw.month, raw.day, 7, 0, 0, tzinfo=timezone.utc)
    send_at -= timedelta(days=1)
    for email in recipients:
        try:
            db.table("notifications").insert({
                "user_email":   email,
                "type":         "auction",
                "entity_id":    auction_row["id"],
                "entity_type":  "auction",
                "message":      f"Auction tomorrow: {auction_row.get('franchise_name','')}",
                "status":       "pending",
                "scheduled_at": send_at.isoformat(),
            }).execute()
        except Exception:
            pass


# ── Main loop ─────────────────────────────────────────────────

def main() -> None:
    if not SUPABASE_URL or not SUPABASE_KEY:
        log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
        sys.exit(1)

    if not EMAIL_API_KEY:
        log.error("EMAIL_API_KEY must be set.")
        sys.exit(1)

    log.info("SCMA Scheduler starting. Provider=%s  Poll=%ds", EMAIL_PROVIDER, POLL_INTERVAL_S)

    db = _get_db()

    while True:
        try:
            count = process_pending(db)
            if count:
                log.info("Sent %d notification(s).", count)
            else:
                log.debug("No pending notifications due.")
        except Exception as e:
            log.error("Unexpected error in process loop: %s", e)

        time.sleep(POLL_INTERVAL_S)


if __name__ == "__main__":
    main()
