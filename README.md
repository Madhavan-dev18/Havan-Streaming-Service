# 🎬 Havan Stream

**A Netflix-style, multi-profile video streaming platform** — Django REST backend, React + Vite frontend, PIN-protected user profiles, adaptive HLS playback, and per-profile watch history.

![Django](https://img.shields.io/badge/Django-6.0-092E20?style=for-the-badge&logo=django&logoColor=white)
![DRF](https://img.shields.io/badge/DRF-3.17-ff1709?style=for-the-badge&logo=django&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)
![Vite](https://img.shields.io/badge/Vite-8-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![HLS.js](https://img.shields.io/badge/HLS.js-1.6-FF6B6B?style=for-the-badge)
![License](https://img.shields.io/badge/license-MIT-green?style=for-the-badge)

---

## 📖 Table of Contents

1. [What This Is](#-what-this-is)
2. [Architecture](#-architecture)
3. [Data Model](#-data-model)
4. [API Surface](#-api-surface)
5. [Frontend Structure](#-frontend-structure)
6. [Local Setup](#-local-setup)
7. [Environment Variables](#-environment-variables)
8. [Deployment](#-deployment)
9. [Known Limitations](#-known-limitations)
10. [License](#-license)

---

## 🧭 What This Is

Havan Stream is a full-stack video streaming platform modeled on the Netflix
product experience: a single account can hold **multiple profiles**, each with
its own avatar, age setting, PIN lock, favorite genres, watchlist, and
watch-history — mirroring how real streaming services isolate viewing data
per household member.

The backend serves a JWT-authenticated REST API over a movie catalog that
supports **multi-quality HLS streams, multi-language audio tracks, WebVTT
subtitles, and intro/recap-skip metadata** — not just a flat list of video
URLs. The frontend is a Vite-powered React SPA with an HLS.js-driven player.

```
┌─────────────────────────────────────────────────────────────────┐
│                         HAVAN STREAM                             │
├───────────────────────────────┬───────────────────────────────────┤
│           FRONTEND             │              BACKEND               │
│     React 19 + Vite + Tailwind │     Django 6 + DRF + SimpleJWT      │
│                                 │                                     │
│  ┌───────────┐  ┌────────────┐ │  ┌────────────┐  ┌───────────────┐ │
│  │ Navbar     │  │ MovieCard  │ │  │ Auth        │  │ Movie Catalog │ │
│  │ FilterBar  │  │ Editorial  │ │  │ (JWT)       │  │ (Genres,      │ │
│  │ Profile    │  │ Grid       │ │  │             │  │  Qualities,   │ │
│  │ Selector/  │  │ Advanced   │ │  │ Profiles +  │  │  Subtitles,   │ │
│  │ Manager    │  │ Player     │ │  │ PIN Verify  │  │  Audio Tracks)│ │
│  └───────────┘  └────────────┘ │  └────────────┘  └───────────────┘ │
│                                 │  ┌────────────────────────────────┐│
│                                 │  │ Watchlist / Watch History       ││
│                                 │  └────────────────────────────────┘│
└───────────────────────────────┴───────────────────────────────────┘
              │                                    │
              │        HLS.js adaptive playback     │
              └───────────────►  hls_stream_url ◄────┘
```

---

## 🏗 Architecture

```
                     ┌──────────────┐
   Browser  ───────► │  React SPA   │ ── Vite dev server / static build
                     │ (havan-      │
                     │  frontend)   │
                     └──────┬───────┘
                            │ REST + JWT (Bearer token)
                            ▼
                     ┌──────────────┐
                     │  Django REST │ ── gunicorn + whitenoise (Procfile)
                     │  (core app)  │
                     └──────┬───────┘
                            │ ORM
                            ▼
                     ┌──────────────┐
                     │  PostgreSQL  │ ── via dj-database-url
                     │ (or SQLite   │
                     │  locally)    │
                     └──────────────┘
```

**Deployment shape:** a single Procfile-driven web dyno (`gunicorn
netflix_site.wsgi:application`) serves the Django API and static assets via
Whitenoise — no separate CDN or object storage layer is wired in; video/HLS
URLs are stored as plain `URLField`s pointing to wherever the media is
actually hosted.

---

## 🗄 Data Model

The catalog is intentionally richer than a basic "movie list" — it's built to
support real streaming-player features:

| Model | Purpose |
|---|---|
| `Movie` | Core catalog entry — title, description, rating, genres, trending/featured flags, and **intro/recap skip timestamps** (`intro_start`, `intro_end`, `recap_start`, `recap_end`) |
| `VideoQuality` | Multiple bitrate/resolution streams per movie (e.g. 480p / 720p / 1080p / Auto) |
| `Subtitle` | WebVTT subtitle tracks per movie, per language, with forced/default flags |
| `AudioTrack` | Multiple dubbed-language audio tracks per movie |
| `UserProfile` | Netflix-style sub-profiles under one `User` — avatar, age, 4-digit PIN, preferred language, favorite genres |
| `Watchlist` | Per-profile "my list", unique per (profile, movie) |
| `WatchHistory` | Per-profile resume-playback progress in seconds, with a `completed` flag |
| `Genre` | Simple tag/category, many-to-many with `Movie` |

```
User ──< UserProfile >── Genre (favorite_genres)
              │
              ├──< Watchlist >── Movie
              └──< WatchHistory >── Movie

Movie ──< VideoQuality
Movie ──< Subtitle
Movie ──< AudioTrack
Movie ──> Movie (next_episode, self-referential for series)
```

---

## 🔌 API Surface

All endpoints live under `core/urls.py` and (aside from `register`/`login`)
require a JWT bearer token.

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/register/` | Create a new account |
| `POST` | `/login/` | Obtain JWT access/refresh tokens |
| `POST` | `/token/refresh/` | Refresh an expired access token |
| `GET/POST` | `/profiles/` | List profiles for the account / create a new profile |
| `GET` | `/profiles/<id>/` | Fetch a single profile |
| `POST` | `/verify-pin/` | Validate a profile's 4-digit PIN before unlocking it |
| `GET` | `/movies/` | Browse the catalog |
| `GET` | `/movies/<id>/` | Movie detail (qualities, subtitles, audio tracks) |
| `GET` | `/movies/featured/` | Featured/hero movie |
| `GET` | `/movies/recommended/` | Recommended-for-you list |
| `GET` | `/genres/` | List genres |
| `GET/POST` | `/watchlist/` | View or add to a profile's watchlist |
| `GET/POST` | `/history/` | View or update watch progress |

> ⚠️ **Note:** PIN verification (`/verify-pin/`) and JWT auth are the two
> highest-value places for security testing — see [Known Limitations](#-known-limitations).

---

## 🖥 Frontend Structure

```
havan-frontend/src/
├── components/
│   ├── Navbar.jsx            top navigation
│   ├── FilterBar.jsx         genre / category filtering
│   ├── EditorialGrid.jsx     curated movie row layout
│   ├── MovieCard.jsx         individual poster card (+ test file)
│   ├── ProfileSelector.jsx   "who's watching" screen
│   ├── ProfileManager.jsx    create/edit/delete profiles
│   ├── VideoPlayer.jsx       base player
│   └── AdvancedPlayer.jsx    HLS.js-driven player (quality/subtitle/audio switching)
├── pages/
│   ├── Login.jsx
│   └── ProfilePage.jsx
├── context/
│   └── AuthContext.jsx       JWT/session state
├── AuthGateway.jsx           route guard
└── App.jsx
```

Built on **React 19 + Vite 8 + Tailwind 4**, with **HLS.js** driving adaptive
playback against the `hls_stream_url` / `VideoQuality` records from the API,
and **react-router-dom 7** for routing.

---

## ⚙️ Local Setup

### Backend

```bash
git clone https://github.com/Madhavan-dev18/havan-stream.git
cd havan-stream

python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env             # then fill in real values

python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd havan-frontend
npm install
npm run dev
```

The Vite dev server proxies to the Django API — confirm the API base URL
matches your backend's `runserver` address (default `http://127.0.0.1:8000`).

---

## 🔑 Environment Variables

| Variable | Required | Example | Notes |
|---|---|---|---|
| `SECRET_KEY` | ✅ | `django-insecure-...` | Django cryptographic signing key |
| `DEBUG` | ✅ | `False` | Never `True` in production |
| `ALLOWED_HOSTS` | ✅ | `127.0.0.1,localhost` | Comma-separated |
| `DATABASE_URL` | ✅ | `sqlite:///db.sqlite3` | Parsed via `dj-database-url`; use a real Postgres URL in production |
| `CORS_ALLOWED_ORIGINS` | ✅ | `http://localhost:5173` | Comma-separated frontend origins |
| `PORT` | ✅ (prod) | `8000` | Bound by gunicorn via `Procfile` |

See `.env.example` for the canonical template.

---

## 🚀 Deployment

Deployed via a `Procfile`-based process (Heroku/Render-style):

```
web: gunicorn netflix_site.wsgi:application --bind 0.0.0.0:$PORT
```

Static files are served through **Whitenoise** — no separate static host or
CDN is configured. Database connections are resolved dynamically from
`DATABASE_URL` via `dj-database-url`, so swapping SQLite for Postgres in
production requires no code change, only an environment variable.

---

## ⚠️ Known Limitations

Being upfront about gaps rather than silent about them:

- **No backend test suite.** `core/tests.py` exists but is not populated with
  real coverage — the PIN-verification and JWT auth flows, which are the
  highest-risk logic in this codebase, are currently untested.
- **No CI pipeline.** Nothing runs `manage.py test` or the frontend `vitest`
  suite automatically on push/PR.
- **No object storage / CDN layer.** Video and image URLs are stored as raw
  `URLField`s; there's no upload pipeline or media processing built in.
- **License file needs verification** — confirm the committed `LICENSE` file
  contains the full MIT text before treating this as properly licensed.

---

## 📄 License

MIT — see [`LICENSE`](./LICENSE).
