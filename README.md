# Customer Service Request Dashboard

A general-purpose web dashboard where a customer can see the history and status of their service requests and open new ones. Categories, statuses, texts and logo are configurable, so it can be reused for different businesses.

> Demo project: the database contains fake sample data only, and login by phone number has no password.

## Features

- **Login by phone number.** The phone number is the user ID. Demo numbers are shown on the login screen.
- **My requests.** Table of all the user's requests (newest first) with category, sub-category, status and dates.
  - Counters per status, filter by status and category, search in the description.
  - Click a request to see its details and status history.
- **New request.** Category and sub-category from built-in lists (required), plus an optional free description. Requests start with status *Open* and cannot be edited after sending.
- **English / Hebrew.** Switch at the top right. Hebrew uses a right-to-left layout and translates categories and statuses too.
- **Design.** Logo at the top left, light blue background, black lines, brown and purple text.

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
tests/            Automated tests
practice.md       How we build (workflow, git rules)
concept.md        What we build (requirements)
```

## Out of scope (this version)

Real authentication, staff screens for handling requests, notifications, file attachments.
