# 🏏 Cricket Availability & Conflict Dashboard  v2

A production-ready, **desktop-first** Streamlit app backed by **Supabase (PostgreSQL)**.
Built for internal cricket agency staff — data is persistent, role-protected, and shared
across every session and device automatically.

---

## ✨ What's New in v2

| Feature | Detail |
|---|---|
| **Auth gate** | Gmail OAuth + Email/Password login — no unauthenticated access |
| **Role-based access** | `admin` / `editor` / `viewer` — only editors can write |
| **Google Calendar UI** | Full month grid, rich pills (name + format + country + teams) |
| **Two calendars** | Separate Men's and Women's tabs |
| **Category system** | International / Domestic / League (replaces venue) |
| **Country field** | Replaces venue — IPL → India, PSL → Pakistan, ICC series → varies |
| **Desktop-first** | Multi-column layouts, sticky right panel, dense data tables |
| **Responsive** | Graceful fallback for tablet/mobile |
| **Caching** | `@st.cache_data` on all reads — fast on large datasets |
| **Conflict priority** | Event dates first → player → team |
| **Team search** | Search box instead of dropdown; 3 multi-input methods |
| **Search page** | Find by name/country/format + year; shows mini calendar + conflicts |
| **Admin page** | Manage staff roles from inside the app |

---

## 🗂️ Project Structure

```
cricket_dashboard_v2/
│
├── app.py                           ← Entry point: auth gate + sidebar router
├── requirements.txt
├── .gitignore
├── README.md
│
├── .streamlit/
│   └── secrets.toml.example         ← Copy → secrets.toml, fill in credentials
│
├── db/
│   ├── __init__.py
│   ├── supabase_client.py           ← Cached Supabase client singleton
│   ├── auth.py                      ← Login, logout, OAuth callback, role checks
│   ├── operations.py                ← All read/write functions (cached reads)
│   └── schema.sql                   ← Run once in Supabase SQL Editor
│
├── utils/
│   ├── __init__.py
│   ├── conflicts.py                 ← Conflict detection engine (P1→P2→P3)
│   └── analysis.py                 ← Gap analysis + workload scoring
│
├── config/
│   ├── __init__.py
│   └── styles.py                    ← All CSS: desktop-first + responsive breakpoints
│
└── pages/
    ├── __init__.py
    ├── login.py                     ← Email + Google OAuth login screen
    ├── dashboard.py                 ← 3-col: events | conflicts | workload
    ├── calendar_view.py             ← Google Calendar grid (Male + Female tabs)
    ├── search.py                    ← Search + mini calendar + conflict info
    ├── add_event.py                 ← Add event (category/country/format/gender)
    ├── add_team.py                  ← Team search + multi-input (3 methods)
    ├── add_squad.py                 ← Squad queue builder + right panel
    ├── conflicts.py                 ← Priority 1/2/3 conflict view
    ├── availability.py              ← Date-range check + dense status table
    ├── timeline.py                  ← Timeline + gap analysis + summary panel
    └── admin.py                     ← Role management for all staff
```

---

## 🚀 Setup — 5 Steps

### Step 1 — Create a Supabase project (free)

1. Go to [supabase.com](https://supabase.com) → **New project**
2. Choose a name, strong password, and the nearest region
3. Wait ~2 minutes for provisioning

---

### Step 2 — Run the database schema

1. Supabase dashboard → **SQL Editor** → **New query**
2. Paste the **entire contents** of `db/schema.sql`
3. Click **Run**

This creates:
- `events` table — with `category` (International/Domestic/League) and `country` fields
- `teams` table — linked to events
- `squad` table — one row per player per event
- `user_roles` table — maps Supabase auth users to app roles
- Row-Level Security policies — viewers read-only, editors write, admins delete

---

### Step 3 — Configure credentials

Get these from **Supabase → Project Settings → API**:

```toml
# .streamlit/secrets.toml
[supabase]
url          = "https://YOUR_PROJECT_ID.supabase.co"
anon_key     = "YOUR_ANON_PUBLIC_KEY"
redirect_url = "http://localhost:8501"     # your app URL (local or deployed)
```

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# then edit secrets.toml with your real values
```

> ⚠️ **`secrets.toml` is in `.gitignore` — never commit it.**

---

### Step 4 — (Optional) Enable Google Login

1. Supabase dashboard → **Authentication → Providers → Google**
2. Toggle **Enable** → paste your Google OAuth **Client ID** and **Client Secret**
3. Add your app URL to **Authorized redirect URIs** in Google Console:
   `https://YOUR_PROJECT_ID.supabase.co/auth/v1/callback`
4. Set `redirect_url` in `secrets.toml` to your deployed app URL

> Email/password login works immediately without Google setup.

---

### Step 5 — Create your first admin user

**Option A — Invite via Supabase dashboard:**
1. Supabase → **Authentication → Users → Invite user** → enter your email
2. Check email, click the link, set a password
3. Then in **SQL Editor**, run:
   ```sql
   INSERT INTO user_roles (user_id, email, role)
   SELECT id, email, 'admin'
   FROM auth.users
   WHERE email = 'your@email.com';
   ```

**Option B — Sign up via the app then promote:**
1. Run the app, use the login screen to sign up
2. In Supabase SQL Editor, run the INSERT above

---

### Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

---

## ☁️ Deploy to Streamlit Community Cloud

1. Push project to a **private GitHub repo**
   (`.gitignore` keeps `secrets.toml` out automatically)

2. Go to [share.streamlit.io](https://share.streamlit.io) → **New app**

3. Set **Main file path** → `app.py`

4. **Advanced settings → Secrets** → paste:
   ```toml
   [supabase]
   url          = "https://YOUR_PROJECT_ID.supabase.co"
   anon_key     = "YOUR_ANON_PUBLIC_KEY"
   redirect_url = "https://YOUR_APP_NAME.streamlit.app"
   ```

5. Click **Deploy** ✅

Data persists in Supabase permanently — redeploying never loses data.

---

## 🔐 Role System

| Role | Calendar | Search | Add/Edit | Delete | Manage Users |
|---|---|---|---|---|---|
| **viewer** | ✅ | ✅ | ❌ | ❌ | ❌ |
| **editor** | ✅ | ✅ | ✅ | ❌ | ❌ |
| **admin**  | ✅ | ✅ | ✅ | ✅ | ✅ |

Roles are enforced both in the app UI (buttons hidden) and at the database level
via Supabase Row-Level Security policies — so even direct API calls respect roles.

---

## 📅 Calendar Colour Guide

| Colour | Meaning |
|---|---|
| 🔵 Blue pill | International event |
| 🟢 Green pill | Domestic event |
| 🟣 Purple pill | League (IPL, CPL, PSL…) |
| Pink left-border | Women's event |
| 🔴 Red outline | Conflict with another event |
| Red cell border | Day contains a conflicting event |

---

## 🗄️ Database Schema (summary)

### `events`
| Column | Type | Notes |
|---|---|---|
| event_name | TEXT | UNIQUE |
| event_type | TEXT | match / series / tournament |
| category   | TEXT | International / Domestic / League |
| format     | TEXT | T20 / ODI / Test / … |
| start_date | DATE | |
| end_date   | DATE | ≥ start_date (CHECK) |
| country    | TEXT | host nation / region |
| gender     | TEXT | Male / Female / Mixed |
| notes      | TEXT | optional |

### `user_roles`
| Column | Type | Notes |
|---|---|---|
| user_id | UUID | FK → auth.users |
| email   | TEXT | |
| role    | TEXT | admin / editor / viewer |

---

## ⚙️ Conflict Priority

```
1. Event date overlaps  →  do the scheduling dates clash?
2. Player conflicts     →  is a player double-booked?
3. Team conflicts       →  is a team in two events at once?
```

Check in this order — resolving (1) automatically prevents many (2) and (3) cases.

---

## 🖥️ Desktop-First Design

- **1280px+** — Full calendar grid, 3-column dashboard, sticky right panels
- **768–1279px** — 2-column layout, pill meta hidden
- **< 768px** — Stacked layout, simplified calendar cells, agenda-style fallback

---

## 📦 Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit |
| Database | Supabase (PostgreSQL) |
| Auth | Supabase Auth (Email + Google OAuth) |
| Client | `supabase-py` |
| Data | Pandas |
| Caching | `@st.cache_data` / `@st.cache_resource` |
