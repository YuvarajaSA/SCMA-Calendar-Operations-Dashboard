# #!/usr/bin/env python3
# """
# scheduler.py  —  SCMA Email Notification Scheduler
# Run independently: python scheduler.py
# Or via cron:  */5 * * * * /path/to/venv/bin/python /path/to/scheduler.py

# Reads pending notifications from Supabase, sends via Resend or SendGrid,
# marks as sent/failed. Runs safely in a loop every 5 minutes.

# SETUP
# ─────
# 1. Install deps:  pip install supabase resend python-dotenv pytz
# 2. Set env vars (or create .env):
#    SUPABASE_URL=https://xxx.supabase.co
#    SUPABASE_SERVICE_KEY=your-service-role-key   ← use service key, NOT anon
#    EMAIL_PROVIDER=resend                          ← or "sendgrid"
#    EMAIL_API_KEY=re_xxxx                          ← Resend or SendGrid API key
#    EMAIL_FROM=noreply@sophieagency.com
# """

# from __future__ import annotations

# import os
# import sys
# import time
# import logging
# from datetime import datetime, timezone

# logging.basicConfig(
#     level=logging.INFO,
#     format="%(asctime)s  %(levelname)-7s  %(message)s",
#     datefmt="%Y-%m-%d %H:%M:%S",
# )
# log = logging.getLogger("scma-scheduler")

# # ── Load env ──────────────────────────────────────────────────
# try:
#     from dotenv import load_dotenv
#     load_dotenv()
# except ImportError:
#     pass

# SUPABASE_URL     = os.environ.get("SUPABASE_URL","")
# SUPABASE_KEY     = os.environ.get("SUPABASE_SERVICE_KEY","")
# EMAIL_PROVIDER   = os.environ.get("EMAIL_PROVIDER","resend").lower()
# EMAIL_API_KEY    = os.environ.get("EMAIL_API_KEY","")
# EMAIL_FROM       = os.environ.get("EMAIL_FROM","noreply@sophieagency.com")
# POLL_INTERVAL_S  = int(os.environ.get("POLL_INTERVAL_S","300"))    # 5 minutes


# # ── Supabase client (service role — bypasses RLS) ─────────────
# def _get_db():
#     from supabase import create_client
#     return create_client(SUPABASE_URL, SUPABASE_KEY)


# # ── Email sending ─────────────────────────────────────────────

# def _send_resend(to: str, subject: str, body: str) -> bool:
#     import resend
#     resend.api_key = EMAIL_API_KEY
#     try:
#         resend.Emails.send({
#             "from":    EMAIL_FROM,
#             "to":      [to],
#             "subject": subject,
#             "text":    body,
#         })
#         return True
#     except Exception as e:
#         log.error("Resend error: %s", e)
#         return False


# def _send_sendgrid(to: str, subject: str, body: str) -> bool:
#     import sendgrid
#     from sendgrid.helpers.mail import Mail
#     sg = sendgrid.SendGridAPIClient(api_key=EMAIL_API_KEY)
#     msg = Mail(
#         from_email    = EMAIL_FROM,
#         to_emails     = to,
#         subject       = subject,
#         plain_text_content = body,
#     )
#     try:
#         resp = sg.send(msg)
#         return resp.status_code in (200, 201, 202)
#     except Exception as e:
#         log.error("SendGrid error: %s", e)
#         return False


# def send_email(to: str, subject: str, body: str) -> bool:
#     if EMAIL_PROVIDER == "sendgrid":
#         return _send_sendgrid(to, subject, body)
#     return _send_resend(to, subject, body)


# # ── Notification processing ───────────────────────────────────

# def _format_message(notif: dict) -> tuple[str, str]:
#     """Return (subject, body) for a notification row."""
#     ntype   = notif.get("type","")
#     message = notif.get("message","")
#     subject_map = {
#         "event_start":  "SCMA — Event Starting Today",
#         "match_start":  "SCMA — Match Today",
#         "registration": "SCMA — Registration Window Update",
#         "auction":      "SCMA — Auction Tomorrow",
#     }
#     subject = subject_map.get(ntype, "SCMA Calendar Notification")
#     body    = f"""Hello,

# {message}

# —
# SCMA Calendar Dashboard
# Sophie Agency
# """
#     return subject, body


# def process_pending(db) -> int:
#     """Fetch due pending notifications and send them. Returns count sent."""
#     now = datetime.now(timezone.utc).isoformat()
#     try:
#         resp = (
#             db.table("notifications")
#             .select("*")
#             .eq("status","pending")
#             .lte("scheduled_at", now)
#             .order("scheduled_at")
#             .limit(50)
#             .execute()
#         )
#         notifs = resp.data or []
#     except Exception as e:
#         log.error("DB fetch error: %s", e)
#         return 0

#     sent = 0
#     for n in notifs:
#         to      = n.get("user_email","")
#         subject, body = _format_message(n)

#         if not to:
#             log.warning("Notification %s has no recipient — skipping.", n["id"])
#             _mark(db, n["id"], "failed")
#             continue

#         log.info("Sending [%s] to %s  id=%s", n.get("type"), to, n["id"])
#         ok = send_email(to, subject, body)

#         if ok:
#             _mark(db, n["id"], "sent")
#             sent += 1
#         else:
#             _mark(db, n["id"], "failed")

#     return sent


# def _mark(db, notif_id: int, status: str) -> None:
#     update = {"status": status}
#     if status == "sent":
#         update["sent_at"] = datetime.now(timezone.utc).isoformat()
#     try:
#         db.table("notifications").update(update).eq("id", notif_id).execute()
#     except Exception as e:
#         log.error("Could not mark notification %s as %s: %s", notif_id, status, e)


# # ── Scheduling helpers — called when creating entities ────────

# def schedule_event(db, event_row: dict, recipients: list[str]) -> None:
#     """Queue same-day morning notification for an event."""
#     import pytz
#     start = event_row.get("start_date")
#     if not start:
#         return
#     if isinstance(start, str):
#         from datetime import date as dt_date
#         import pandas as pd
#         start = pd.to_datetime(start).date()
#     from datetime import time as dt_time
#     send_at = datetime(start.year, start.month, start.day, 7, 0, 0, tzinfo=timezone.utc)
#     for email in recipients:
#         try:
#             db.table("notifications").insert({
#                 "user_email":   email,
#                 "type":         "event_start",
#                 "entity_id":    event_row["id"],
#                 "entity_type":  "event",
#                 "message":      f"Event starting today: {event_row.get('event_name','')}",
#                 "status":       "pending",
#                 "scheduled_at": send_at.isoformat(),
#             }).execute()
#         except Exception:
#             pass   # likely duplicate — UNIQUE constraint prevents double send


# def schedule_match(db, match_row: dict, recipients: list[str]) -> None:
#     import pandas as pd
#     m_date = match_row.get("match_date")
#     if not m_date:
#         return
#     if isinstance(m_date, str):
#         m_date = pd.to_datetime(m_date).date()
#     from datetime import time as dt_time
#     send_at = datetime(m_date.year, m_date.month, m_date.day, 7, 0, 0, tzinfo=timezone.utc)
#     for email in recipients:
#         try:
#             db.table("notifications").insert({
#                 "user_email":   email,
#                 "type":         "match_start",
#                 "entity_id":    match_row["id"],
#                 "entity_type":  "match",
#                 "message":      f"Match today: {match_row.get('match_name','Match')}",
#                 "status":       "pending",
#                 "scheduled_at": send_at.isoformat(),
#             }).execute()
#         except Exception:
#             pass


# def schedule_registration(db, reg_row: dict, recipients: list[str]) -> None:
#     """2 days before start and 2 days before deadline."""
#     import pandas as pd
#     from datetime import timedelta
#     for field, label in [("start_date","Registration window opens"), ("deadline","Registration deadline")]:
#         raw = reg_row.get(field)
#         if not raw:
#             continue
#         if isinstance(raw, str):
#             raw = pd.to_datetime(raw).date()
#         send_at = datetime(raw.year, raw.month, raw.day, 7, 0, 0, tzinfo=timezone.utc)
#         send_at -= timedelta(days=2)
#         for email in recipients:
#             try:
#                 db.table("notifications").insert({
#                     "user_email":   email,
#                     "type":         "registration",
#                     "entity_id":    reg_row["id"],
#                     "entity_type":  "registration",
#                     "message":      f"{label} in 2 days (event id {reg_row.get('event_id','')})",
#                     "status":       "pending",
#                     "scheduled_at": send_at.isoformat(),
#                 }).execute()
#             except Exception:
#                 pass


# def schedule_auction(db, auction_row: dict, recipients: list[str]) -> None:
#     """1 day before auction date."""
#     import pandas as pd
#     from datetime import timedelta
#     raw = auction_row.get("auction_date")
#     if not raw:
#         return
#     if isinstance(raw, str):
#         raw = pd.to_datetime(raw).date()
#     send_at = datetime(raw.year, raw.month, raw.day, 7, 0, 0, tzinfo=timezone.utc)
#     send_at -= timedelta(days=1)
#     for email in recipients:
#         try:
#             db.table("notifications").insert({
#                 "user_email":   email,
#                 "type":         "auction",
#                 "entity_id":    auction_row["id"],
#                 "entity_type":  "auction",
#                 "message":      f"Auction tomorrow: {auction_row.get('franchise_name','')}",
#                 "status":       "pending",
#                 "scheduled_at": send_at.isoformat(),
#             }).execute()
#         except Exception:
#             pass


# # ── Main loop ─────────────────────────────────────────────────

# def main() -> None:
#     if not SUPABASE_URL or not SUPABASE_KEY:
#         log.error("SUPABASE_URL and SUPABASE_SERVICE_KEY must be set.")
#         sys.exit(1)

#     if not EMAIL_API_KEY:
#         log.error("EMAIL_API_KEY must be set.")
#         sys.exit(1)

#     log.info("SCMA Scheduler starting. Provider=%s  Poll=%ds", EMAIL_PROVIDER, POLL_INTERVAL_S)

#     db = _get_db()

#     while True:
#         try:
#             count = process_pending(db)
#             if count:
#                 log.info("Sent %d notification(s).", count)
#             else:
#                 log.debug("No pending notifications due.")
#         except Exception as e:
#             log.error("Unexpected error in process loop: %s", e)

#         time.sleep(POLL_INTERVAL_S)


# if __name__ == "__main__":
#     main()

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
from datetime import datetime, timezone, timedelta

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
EMAIL_FROM       = os.environ.get("EMAIL_FROM","noreply@sophieclairem.com")
POLL_INTERVAL_S  = int(os.environ.get("POLL_INTERVAL_S","300"))    # 5 minutes


# ── Supabase client (service role — bypasses RLS) ─────────────
def _get_db():
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Email sending ─────────────────────────────────────────────

def _send_resend(to: str, subject: str, body: str, html: str = "") -> bool:
    import resend
    resend.api_key = EMAIL_API_KEY
    payload: dict = {
        "from":    EMAIL_FROM,
        "to":      [to],
        "subject": subject,
        "text":    body,
    }
    if html:
        payload["html"] = html
    try:
        resend.Emails.send(payload)
        return True
    except Exception as e:
        log.error("Resend error: %s", e)
        return False


def _send_sendgrid(to: str, subject: str, body: str, html: str = "") -> bool:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Content
    sg = sendgrid.SendGridAPIClient(api_key=EMAIL_API_KEY)
    msg = Mail(
        from_email         = EMAIL_FROM,
        to_emails          = to,
        subject            = subject,
        plain_text_content = body,
    )
    if html:
        try:
            msg.add_content(Content("text/html", html))
        except Exception:
            pass   # HTML attachment failure must not block plain-text send
    try:
        resp = sg.send(msg)
        return resp.status_code in (200, 201, 202)
    except Exception as e:
        log.error("SendGrid error: %s", e)
        return False


def send_email(to: str, subject: str, body: str, html: str = "") -> bool:
    if EMAIL_PROVIDER == "sendgrid":
        return _send_sendgrid(to, subject, body, html=html)
    return _send_resend(to, subject, body, html=html)


# ── HTML email template ───────────────────────────────────────

def build_email_html(title: str, message: str, footer: str) -> str:
    """
    Return a minimal, inline-styled HTML email string.
    Plain text is always sent alongside this as the fallback.
    """
    def _esc(s: str) -> str:
        return (
            s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;")
             .replace('"', "&quot;")
        )

    # Preserve newlines in the message body.
    message_html = _esc(message).replace("\n", "<br>")

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_esc(title)}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f4f4;
             font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background-color:#f4f4f4;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="max-width:600px;width:100%;background-color:#ffffff;
                      border-radius:8px;overflow:hidden;
                      box-shadow:0 2px 8px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background-color:#1a1a2e;padding:24px 32px;">
              <p style="margin:0;font-size:13px;color:#a0a8c0;
                        letter-spacing:1px;text-transform:uppercase;">
                SCMA Calendar Dashboard
              </p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <h2 style="margin:0 0 16px 0;font-size:20px;color:#1a1a2e;">
                {_esc(title)}
              </h2>
              <p style="margin:0 0 24px 0;font-size:15px;color:#333333;
                        line-height:1.6;">
                {message_html}
              </p>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background-color:#f9f9f9;padding:16px 32px;
                       border-top:1px solid #eeeeee;">
              <p style="margin:0;font-size:12px;color:#888888;">
                {_esc(footer)}
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


# ── Timezone & entity helpers (send-time only) ────────────────

def _get_user_timezone(db, email: str) -> str:
    """
    Look up the user's preferred timezone from the profiles table.
    Returns "UTC" if the record is missing, the field is blank, or any
    DB error occurs.  Never raises.
    """
    try:
        resp = (
            db.table("profiles")
            .select("timezone")
            .eq("email", email)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if rows:
            tz = (rows[0].get("timezone") or "").strip()
            if tz:
                return tz
    except Exception as e:
        log.warning("Could not fetch timezone for %s: %s", email, e)
    return "UTC"


def _get_entity_datetime(db, entity_type: str, entity_id: int) -> datetime | None:
    """
    Fetch the canonical UTC datetime for a match or auction.
    Returns None for other entity types or on any error.

    Table / field mapping
    ─────────────────────
    match   → matches.match_datetime
    auction → auctions.auction_datetime
    """
    _MAP = {
        "match":   ("matches",  "match_datetime"),
        "auction": ("auctions", "auction_datetime"),
    }
    if entity_type not in _MAP:
        return None
    table, field = _MAP[entity_type]
    try:
        resp = (
            db.table(table)
            .select(field)
            .eq("id", entity_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if rows:
            return _parse_utc_datetime(rows[0].get(field))
    except Exception as e:
        log.warning(
            "Could not fetch %s for %s id=%s: %s", field, entity_type, entity_id, e
        )
    return None


def _format_dual_time(dt_utc: datetime, user_tz: str) -> str:
    """
    Format a UTC datetime showing both UTC and the user's local time.

    Output format
    ─────────────
    UTC only:   "14:30 UTC on 15 Apr 2025"
    With local: "14:30 UTC on 15 Apr 2025 (20:00 IST)"

    Timezone conversion is done here with pytz directly — datetime_utils
    is intentionally not imported into the scheduler.
    """
    import pytz

    date_str = dt_utc.strftime("%d %b %Y")
    utc_str  = f"{dt_utc.strftime('%H:%M')} UTC on {date_str}"

    if not user_tz or user_tz == "UTC":
        return utc_str

    try:
        tz        = pytz.timezone(user_tz)
        local_dt  = dt_utc.astimezone(tz)
        tz_abbr   = local_dt.strftime("%Z")
        local_str = local_dt.strftime("%H:%M")
        return f"{utc_str} ({local_str} {tz_abbr})"
    except Exception:
        return utc_str


def _enrich_message(db, notif: dict, user_tz: str) -> str:
    """
    Build a timezone-aware plain-text message body for send time.

    For match / auction notifications the entity datetime is fetched live
    so the local-time suffix reflects the actual recipient's timezone.
    For event_start and registration the stored message is returned as-is.
    """
    ntype     = notif.get("type", "")
    stored    = notif.get("message", "")
    entity_id = notif.get("entity_id")

    if ntype == "match_start" and entity_id:
        dt_utc = _get_entity_datetime(db, "match", entity_id)
        if dt_utc:
            time_str = _format_dual_time(dt_utc, user_tz)
            # Preserve the name already embedded in the stored message.
            name = stored.split(" starts at ")[0] if " starts at " in stored else "Match"
            return f"{name} starts at {time_str}"

    if ntype == "auction" and entity_id:
        dt_utc = _get_entity_datetime(db, "auction", entity_id)
        if dt_utc:
            time_str = _format_dual_time(dt_utc, user_tz)
            name = (
                stored.split(" auction starts at ")[0]
                if " auction starts at " in stored
                else "Auction"
            )
            return f"{name} auction starts at {time_str}"

    return stored


# ── Notification processing ───────────────────────────────────

def _format_message(notif: dict) -> tuple[str, str]:
    """Return (subject, plain_body) for a notification row."""
    ntype   = notif.get("type", "")
    message = notif.get("message", "")
    subject_map = {
        "event_start": "SCMA — Event Notification",
        "match_start":  "SCMA — Match Notification",
        "registration": "SCMA — Registration Window Update",
        "auction":      "SCMA — Auction Notification",
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
            .eq("status", "pending")
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
        to = n.get("user_email", "")

        if not to:
            log.warning("Notification %s has no recipient — skipping.", n["id"])
            _mark(db, n["id"], "failed")
            continue

        # Subject from static map; plain fallback uses the stored message.
        subject, _ = _format_message(n)

        # Fetch the user's preferred timezone (defaults to "UTC").
        user_tz = _get_user_timezone(db, to)

        # Build a timezone-enriched plain-text message body.
        rich_message = _enrich_message(db, n, user_tz)

        plain_body = f"""Hello,

{rich_message}

—
SCMA Calendar Dashboard
Sophie Agency
"""

        # Build the HTML version with the same content.
        html_body = build_email_html(subject, rich_message, "Sophie Agency")

        log.info(
            "Sending [%s] to %s  tz=%s  id=%s",
            n.get("type"), to, user_tz, n["id"],
        )
        ok = send_email(to, subject, plain_body, html=html_body)

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


# ── Internal UTC helpers ──────────────────────────────────────

def _parse_utc_datetime(raw) -> datetime | None:
    """
    Coerce a DB value (ISO string, aware datetime, or naive datetime) to a
    UTC-aware datetime.  Returns None if the value is absent or unparseable.
    All operations in this file stay in UTC — no timezone conversion is done here.
    """
    if raw is None:
        return None
    if isinstance(raw, datetime):
        if raw.tzinfo is None:
            return raw.replace(tzinfo=timezone.utc)
        return raw.astimezone(timezone.utc)
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw:
            return None
        try:
            # Python 3.11+ handles 'Z'; earlier versions need the replace.
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except ValueError:
            return None
    return None


def _date_to_utc_midnight(raw) -> datetime | None:
    """
    Coerce a date / date-string to midnight UTC datetime.
    Returns None if the value is absent or unparseable.
    """
    if raw is None:
        return None
    try:
        import pandas as pd
        d = pd.to_datetime(raw).date()
        return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
    except Exception:
        return None


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
    """
    Queue a notification 2 hours before the match.

    Priority:
      1. match_datetime (UTC) — subtract 2 hours → send_at
      2. Fallback: match_date at 07:00 UTC (legacy rows without match_datetime)
    All arithmetic stays in UTC; no timezone conversion is performed here.
    """
    # ── Primary: use match_datetime ───────────────────────────
    match_dt = _parse_utc_datetime(match_row.get("match_datetime"))

    if match_dt is not None:
        now = datetime.now(timezone.utc)
        send_at = max(match_dt - timedelta(hours=2), now)
    else:
        # ── Fallback: match_date at 07:00 UTC ─────────────────
        midnight = _date_to_utc_midnight(match_row.get("match_date"))
        if midnight is None:
            log.warning(
                "schedule_match: match id=%s has no match_datetime or match_date — skipped.",
                match_row.get("id"),
            )
            return
        log.warning(
            "schedule_match: match id=%s missing match_datetime — "
            "falling back to match_date at 07:00 UTC.",
            match_row.get("id"),
        )
        send_at = midnight.replace(hour=7)

    match_name = match_row.get("match_name") or "Match"
    if match_dt is not None:
        time_label = match_dt.strftime("%H:%M UTC on %d %b %Y")
    else:
        # Fallback path — match_datetime unavailable, use date only
        time_label = match_row.get("match_date", "date unknown")
    message = f"{match_name} starts at {time_label}"

    for email in recipients:
        try:
            db.table("notifications").insert({
                "user_email":   email,
                "type":         "match_start",
                "entity_id":    match_row["id"],
                "entity_type":  "match",
                "message":      message,
                "status":       "pending",
                "scheduled_at": send_at.isoformat(),
            }).execute()
        except Exception:
            pass


def schedule_registration(db, reg_row: dict, recipients: list[str]) -> None:
    """2 days before start and 2 days before deadline."""
    import pandas as pd
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
    """
    Queue a notification 24 hours before the auction.

    Uses auction_datetime (UTC) as the source of truth.
    auction_date is no longer used; if auction_datetime is absent the row is
    skipped with a warning rather than silently inserting a wrong time.
    All arithmetic stays in UTC; no timezone conversion is performed here.
    """
    auction_dt = _parse_utc_datetime(auction_row.get("auction_datetime"))

    if auction_dt is None:
        log.warning(
            "schedule_auction: auction id=%s has no auction_datetime — skipped.",
            auction_row.get("id"),
        )
        return

    now = datetime.now(timezone.utc)
    send_at = max(auction_dt - timedelta(hours=24), now)

    auction_name = auction_row.get("auction_name") or "Auction"
    time_label = auction_dt.strftime("%H:%M UTC on %d %b %Y")
    message = f"{auction_name} starts at {time_label}"

    for email in recipients:
        try:
            db.table("notifications").insert({
                "user_email":   email,
                "type":         "auction",
                "entity_id":    auction_row["id"],
                "entity_type":  "auction",
                "message":      message,
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