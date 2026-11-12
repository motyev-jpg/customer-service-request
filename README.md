# Customer Service Request Dashboard

A general-purpose web dashboard where a customer can see the history and status of their service requests and open new ones. Categories, statuses, texts and logo are configurable, so it can be reused for different businesses.

> Demo project: the database contains fake sample data only, and login by phone number has no password.

## Features

- **Login by phone number.** The phone number is the user ID. Demo numbers are shown on the login screen.
- **My requests.** Centered title, with the *New request* button on the left and *Log out* on the right (in both languages). Below, a table of all the user's requests (newest first) with category, sub-category, status and dates.
  - Click a request to see its details and status history (the history is kept only in the local database, not in Airtable).
  - No filters or statistics in this version.
- **New request.** Category and sub-category from built-in lists (required), plus an optional free description. Requests start with status *Open* and cannot be edited after sending.
- **English / Hebrew.** Switch at the top right. Hebrew uses a right-to-left layout and translates categories and statuses too.
- **Design.** Logo at the top left, light blue background, black lines, brown and purple text.
- **Mobile friendly.** On narrow screens the requests table becomes a list of cards, and fields and buttons are sized for touch.
- **Optional Airtable data source.** An admin screen connects the dashboard to Airtable (see below). Service staff can then update request statuses in Airtable. The live GitHub Pages demo can connect to the same Base from the browser, and can create a link that connects a teacher's browser.

## Connect to Airtable (optional)

By default requests are stored in a local SQLite database. To store them in Airtable instead:

1. In Airtable, create a Personal Access Token with the scopes `data.records:read`, `data.records:write` and `schema.bases:write`, and copy your Workspace ID from the workspace URL (`airtable.com/workspaces/wspXXXX`).
2. In the dashboard login screen, enter the admin number `543210`. This opens the Airtable settings screen.
3. Paste the token and Workspace ID and press **Connect and create Base**. A Base named `Service Requests` with a `Requests` table is created and becomes the data source.
4. The new Base is empty. To try the dashboard, press **Load demo data into Airtable** on the same screen. It adds the demo requests for the fake phone numbers (`0500000001` to `0500000003`) once.
5. Service staff update the `Status` column in Airtable. Customers see the new status the next time they open the dashboard. With Airtable there is no status history, only the current status.

The token is stored on the server in `data/settings.json` (not in git) and is never shown again after saving. **Disconnect** on the same screen returns to the local database. The admin number can be changed with `ADMIN_PHONE` in `.env`. It has no password, so use it for demos only.

If connecting fails with `0 NETWORK`, check that this computer can reach `api.airtable.com`. On networks or antivirus that inspect HTTPS, Python 3.13+ may reject the inspection certificate in its strict mode. The app already relaxes only that strict check, and it still verifies the certificate chain and host name.

The GitHub Pages demo can connect to the same Base (see **Live demo** below).

## Live demo

A static, browser-only version of the dashboard is published with GitHub Pages:

https://motyev-jpg.github.io/customer-service-request/

It has the same screens, languages and demo data. New requests are saved in your browser only (`localStorage`), and the *Reset demo data* button restores the initial data. Use the demo phone numbers shown on the login screen.

**Optional: connect the live demo to Airtable.** Create the Base from the Flask admin screen first (see above). Then on the demo login screen enter `543210`, and paste an Airtable token and the Base ID. They are saved in your browser only, never in this repository, and the demo then reads and writes requests in Airtable. The same screen creates a link for a teacher (`.../#airtable=<token>,<baseId>`); opening it connects the visitor's browser and removes the token from the address bar. Anyone with the link can read and change that Base, so use a token limited to `data.records:read` and `data.records:write` on a dedicated demo Base, and revoke it afterwards. In this mode there is no status history.

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
store.py          Data sources: local SQLite or Airtable
airtable.py       Airtable REST client and table schema
settings.py       Server-side settings file (Airtable token)
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
