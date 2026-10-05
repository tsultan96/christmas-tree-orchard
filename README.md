# Christmas Tree Orchard: direct-order web app

A small Flask web app where customers browse Christmas trees and place a delivery order online, with no phone calls. Orders are saved to a Google Sheet, the business gets an email alert, and a password-protected admin page shows each day's deliveries with a "delivered" toggle.

Built as a two-week learning project to refresh my Python skills.

## Features

- Landing page: tree types, sizes, and prices (prices are placeholders)
- Order form: validated in the browser and on the server; keeps the customer's input after an error
- Google Sheets storage: each valid order is appended as a row via a service account
- Email alerts: the business gets every new order; customers get a confirmation if they left an email
- Admin view: deliveries for any date, mark orders delivered/undelivered, login/logout with a session

## Tech

Python 3.13 · Flask 3.1 · Jinja templates · Pico.css · gspread (Google Sheets API) · smtplib (Gmail) · python-dotenv

Server-rendered HTML.

## How it works

```
Browser form ──POST /order──▶ validate_order() ──▶ save_order() ──▶ Google Sheet
                                    │                    │
                              errors? show form     send_alert() ──▶ business inbox
                              with values kept      send_confirmation() ──▶ customer
```

## Run it locally

1. Clone and set up a virtual environment:
   ```
   git clone https://github.com/tsultan96/christmas-tree-orchard.git
   cd christmas-tree-orchard
   python -m venv .venv
   .venv\Scripts\Activate.ps1        # Windows (macOS/Linux: source .venv/bin/activate)
   pip install -r requirements.txt
   ```
2. Google Sheets: create a Google Cloud project, enable the Sheets API, create a service account,
   download its JSON key as `credentials.json`, and share your sheet with the service account's email.
3. Gmail: create an App Password for the sending account.
4. Create a `.env` file in the project root:
   ```
   SHEET_ID=
   GOOGLE_CREDENTIALS_FILE=credentials.json
   EMAIL_ADDRESS=
   EMAIL_APP_PASSWORD=
   ALERT_TO=
   SECRET_KEY=
   ADMIN_PASSWORD=
   ```
5. Run `python app.py` and open http://127.0.0.1:5000

## Security notes

- Secrets live only in `.env` and `credentials.json`, both in `.gitignore`, and never in the code or Git history.
- Every admin route checks the session, not just the admin page.
- The password check uses `secrets.compare_digest` (constant time).
- State-changing actions (`/admin/delivered`, `/logout`) are POST-only, with redirect-after-POST.
- Card payments are deliberately **not** collected; a future version would use a hosted checkout (e.g. Stripe Checkout), so card numbers never touch this app.

## What I learned

- Pico.css instead of Bootstrap: I was used to Bootstrap's utility classes, so Pico's "style plain HTML" approach was new. It also taught me that a library's CSS can silently override mine: Pico sets `background-repeat: no-repeat` on `::before`, which is why my snow animation only appeared in one corner until I found the rule in DevTools.

- Google Sheets as a lightweight database: I connected through a service account and
  learned that the sheet's header row becomes each record's dictionary keys, so a stray space in a header (`" Name "`) would quietly break lookups.
- Never trust the browser: Using `novalidate` to skip the browser's checks showed me that anyone can bypass HTML `required`/`min`/`max`, so every rule is checked again in Python.


## How I built it

I built the project in small pieces, getting each one working before starting the next: first the tree order form, then receiving each submitted order and collecting its fields into a Python dictionary, then validating it on the server. After that I connected a Google Sheet through a service account to store orders, added email alerts, and finished with a password-protected admin page and the landing page.

I tested every piece as I went, in the browser and directly in the Python shell (for example, calling `validate_order()` with bad data the browser would normally block), and committed after each working step.

I wrote most of the code myself, with Claude as a coach: it explained new concepts, reviewed each piece, and helped me debug. When I got stuck, it sometimes made a fix directly, which I then read through to understand. The Google Cloud and service-account setup would have taken me days to figure out alone; with coaching it took an afternoon.



## Next steps

- Deploy online
- Automated tests (pytest) for `validate_order`
- Online card payment via hosted checkout
- Spanish/English switch
- Split `app.py` into modules (`sheets.py`, admin Blueprint)
