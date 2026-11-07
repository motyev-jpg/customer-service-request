# Customer Service Request Dashboard

A general-purpose web dashboard where a customer can see the history and status of their service requests and open new ones. Categories, statuses, texts and logo are configurable, so it can be reused for different businesses.

> Demo project: the database contains fake sample data only, and login by phone number has no password.

## Features

- **Login by phone number.** The phone number is the user ID. Demo numbers are shown on the login screen.
- **My requests.** Centered title, with the *New request* button on the left and *Log out* on the right (in both languages). Below, a table of all the user's requests (newest first) with category, sub-category, status and dates.
  - Click a request to see its details and status history.
  - No filters or statistics in this version.
- **New request.** Category and sub-category from built-in lists (required), plus an optional free description. Requests start with status *Open* and cannot be edited after sending.
- **English / Hebrew.** Switch at the top right. Hebrew uses a right-to-left layout and translates categories and statuses too.
- **Design.** Logo at the top left, light blue background, black lines, brown and purple text.
- **Mobile friendly.** On narrow screens the requests table becomes a list of cards, and fields and buttons are sized for touch.

## Live demo

A static, browser-only version of the dashboard is published with GitHub Pages:

https://motyev-jpg.github.io/customer-service-request/

It has the same screens, languages and demo data. New requests are saved in your browser only (`localStorage`), and the *Reset demo data* button restores the initial data. Use the demo phone numbers shown on the login screen.

The demo lives in `docs/`. Its data files, CSS and logo are generated from the Flask app, so after changing `config/`, the demo data in `db.py`, or `static/css/style.css`, run:

```powershell
.\.venv\Scripts\python tools\build_static.py
```

A test fails if `docs/` is out of date. To run the demo locally: `.\.venv\Scripts\python -m http.server -d docs`.

## Tech stack

Python, Flask, SQLite, plain HTML/CSS/JavaScript.

## Setup and run

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
copy .env.example .env      # optional, set SECRET_KEY
.\.venv\Scripts\python app.py
```

Open http://127.0.0.1:5000. On first run the SQLite file `data/csrm.db` is created and filled with demo data. Demo phone numbers: `0500000001`, `0500000002`, `0500000003` (with requests) and `0500000004` (empty history).

Run the tests:

```powershell
.\.venv\Scripts\python -m pytest
```

## Configuration

| What | Where |
|---|---|
| Categories, sub-categories, statuses and their colors (English and Hebrew names) | `config/categories.json` |
| UI texts in both languages | `config/translations.json` |
| Logo | `static/assets/logo.svg` (replace with your own) |
| Colors and layout | `static/css/style.css` |
| Secret key, database path | `.env` (see `.env.example`) |

## Project structure

```
app.py            Flask app and routes
db.py             SQLite access and demo data
config/           Categories, statuses, translations
templates/        HTML templates
static/           CSS, JavaScript, logo
docs/             Static browser-only demo (GitHub Pages)
tools/            build_static.py: generates the demo data in docs/
tests/            Automated tests
practice.md       How we build (workflow, git rules)
concept.md        What we build (requirements)
```

## Out of scope (this version)

Real authentication, staff screens for handling requests, notifications, file attachments.
