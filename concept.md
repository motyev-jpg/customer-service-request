# Concept: Customer Service Request Dashboard

This file defines what we build. `practice.md` defines how we build it.

## Purpose

A general-purpose dashboard for customers to view the history of their service requests, see each request's status, and open new requests. It is generic and can be reused for different businesses by changing the category lists and the logo.

## Users and login

- The user is a customer who opens service requests.
- Identification is by **phone number**, entered on the first screen. The phone number is the user ID.
- No password in this version. This is a demo, not secure authentication.
- If the phone number has no history, the user sees an empty history and can open a new request.

## Screens

### 1. Login
- Single field: phone number. Basic format validation.
- Continue button.

### 2. Dashboard (after login)
- **My requests:** table of all requests for this phone number, newest first.
  - Columns: request number, opened date, category, sub-category, status, last update.
  - Click a row to see full details: description and status history.
  - No filters, search, or statistics section in this version.
- **New request** button, opens the new request form.

### 3. New request
- Category: required, chosen from a built-in list.
- Sub-category: required, built-in list that depends on the chosen category.
- Free description: optional text field.
- Submit creates the request with status **Open**, the current date, and the user's phone number.
- After submit, the user returns to the dashboard and sees the new request.

## Categories (demo list, configurable)

The lists are stored in a config file, not hard-coded in the UI, so they can be replaced for other uses.

| Category | Sub-categories |
|---|---|
| Billing | Invoice question, Payment issue, Refund request |
| Technical support | Cannot connect, Slow performance, Equipment fault |
| Account | Update details, Close account, Access problem |
| General | Complaint, Suggestion, Other |

Every category and sub-category has an English and a Hebrew name.

## Statuses

Open, In progress, Waiting for customer, Resolved, Closed. Every status has an English and a Hebrew name and a fixed display color.

The user can only view statuses. Changing status is not part of this version.

## Layout and design

- **Top left:** logo.
- **Top right:** language switch, English / Hebrew.
- **Language:** switching changes all UI text, category names, and status names. Hebrew uses right-to-left layout, English uses left-to-right.
- **Colors:**
  - Background: light blue.
  - Lines and borders: black.
  - Text: brown and purple. Brown for body text, purple for headings and accents.
- The logo is a placeholder image (to be replaced by the user) stored in an assets folder.
- Text must remain readable on the light blue background.

## Data

- Demo database created by Claude, with sample data only. No real customers or real phone numbers (the repo is public).
- Stores: requests (id, phone, category, sub-category, description, status, created, updated), and status history per request.
- Demo content: several fake phone numbers, each with a different number of requests, in all statuses, in both Hebrew and English descriptions.
- New requests submitted in the UI are saved to the same database.

## Airtable connection (Flask app only)

- The dashboard can store its requests in Airtable instead of the local SQLite database.
- **Admin screen:** logging in with the admin number `543210` (setting `ADMIN_PHONE`, default `543210`) opens `/admin/airtable` instead of the dashboard. There is no separate admin password in this version, and the number is visible in this public repo, so this is suitable for a demo only. Add a password before using real data.
- **Connect:** the admin enters an Airtable Personal Access Token (scopes `data.records:read`, `data.records:write`, `schema.bases:write`) and a Workspace ID. The app creates a Base `Service Requests` with a `Requests` table (`RequestID`, `Phone`, `Category`, `Subcategory`, `Description`, `Status`, `Updated`). No existing Base is needed.
- **Token storage:** on the server only, in `data/settings.json` (not in git). After saving it is shown masked and never sent back to the browser.
- **Status updates:** service staff change the `Status` column in Airtable, and customers see the change the next time they open the dashboard. Select values use the English names from `config/categories.json`.
- **Load demo data:** a button on the admin screen adds the 13 demo requests (fake phone numbers) to the Airtable table, after a confirmation. It does not add them twice. Status history is not kept, and the dates are the time of loading.
- **No status history** when using Airtable: the request page shows only the current status.
- **Disconnect** returns the dashboard to the local database.
- The static GitHub Pages demo can also connect to the same Base (see "Static demo" below). It never has a token built in, because a token in the public repo would be exposed and revoked by Airtable's secret scanning.

## Static demo (GitHub Pages)

- A second, browser-only version of the dashboard lives in `docs/` and is published with GitHub Pages from `main`, folder `/docs`, so it can be viewed without installing anything.
- It has the same screens, texts, languages, layout and demo data as the Flask app. The Flask app stays the real implementation.
- New requests are saved in the browser's `localStorage` only. A "Reset demo data" button restores the initial data. A banner says it is a static demo.
- **Optional Airtable mode.** Logging in with `543210` in the static demo opens a settings screen where the admin enters a token and the Base ID of an existing Base (created from the Flask admin screen). The values are saved in that browser's `localStorage` only, and the demo then reads and writes requests directly in Airtable (Airtable's API allows calls from the browser).
- **Link for the teacher.** From the connected settings screen the admin can create a link `.../#airtable=<token>,<baseId>`. Opening it connects the visitor's browser, and the token is removed from the address bar (the fragment is never sent to a server). Anyone with the link can read and change the data in that Base, so the token should be limited to `data.records:read` and `data.records:write` on a dedicated demo Base, and revoked afterwards.
- In Airtable mode there is no status history and no reset button. Disconnecting returns to the built-in demo data.
- `docs/data/*`, `docs/css/style.css` and `docs/assets/logo.svg` are generated from the Flask app's config, translations, demo data, CSS and logo by `tools/build_static.py`. A test fails if they are out of date.

## Out of scope for this version

- Real authentication, passwords, or SMS verification.
- Staff screens for handling requests or changing status.
- Email or SMS notifications.
- File attachments.

## Open points for the plan

- None.

## Decisions

- Technology: Python + Flask, with HTML, CSS, and JavaScript for the UI. Database: SQLite (single file, no installation).
- A request cannot be edited or cancelled by the user after it is submitted.
- The demo phone numbers are shown on the login screen to make testing easier.
