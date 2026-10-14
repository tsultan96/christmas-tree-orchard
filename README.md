# Christmas Tree Orchard: direct-order web app

**Live demo:** https://christmas-tree-orchard.onrender.com (free hosting, so the first load can take about a minute to wake up)

A small Flask web app where customers browse Christmas trees and place a delivery order online, with no phone calls. Orders are saved to a Google Sheet, the business gets an email alert, customers can pay by card through Stripe, and returning customers can create an account to see their orders and earn a Premium discount. A password-protected staff page lists each month's deliveries with payment status and a "delivered" toggle.

Built as a two-week learning project to refresh my Python skills.

## Features

**Customers**
- Landing page: tree types, sizes, and prices (prices are placeholders), all rendered from one `PRICES` table
- Order form with a tree picker of photo cards; validated in the browser and on the server, and keeps the customer's input after an error
- Card payments: Stripe Checkout in test mode. Try card `4242 4242 4242 4242` with any future expiry date, any CVC, and any ZIP. No real money is charged.
- Order as a guest, or sign up / log in. Logged-in customers get the order form pre-filled and a **My orders** page with delivery and payment status
- Premium loyalty: once 10 trees have been delivered to a customer (counted across all their orders), every new order is 5% off (stacks with the 10% dozen discount)

**Staff**
- Separate staff login (linked from the footer) that leads to a monthly deliveries table: date, customer, address, tree, notes, payment status (Paid / Cash / Unpaid), and a Mark delivered / undo button
- Email alert for every new order

**Behind the scenes**
- Google Sheets as the database: an orders tab and a Customers tab, accessed through a service account
- A Paid column that Stripe confirmation flips to "Yes", so abandoned card checkouts are easy to spot

## Tech

Python 3.13 · Flask 3.1 · Jinja templates · Pico.css · gspread (Google Sheets API) · Stripe Checkout · Werkzeug password hashing · smtplib (Gmail) · python-dotenv · gunicorn on Render

Server-rendered HTML, no JavaScript framework.

## Project structure

| File | Responsibility |
|---|---|
| `app.py` | Flask app setup and all routes |
| `orders.py` | Business rules: `SPECIES`, `PRICES`, discounts, `validate_order`, `order_total`, Premium status |
| `sheets.py` | Reading and writing the Google Sheet (orders and customers) |
| `payments.py` | Stripe Checkout: create a checkout, confirm a payment |
| `emails.py` | Order alert and confirmation emails |
| `templates/`, `static/` | Jinja pages, the shared `theme.css`, and images |

Imports only point toward `app.py`, so there are no circular imports.

## How it works

```
Browser form ──POST /order──▶ validate_order() ──▶ save_order() ──▶ Google Sheet
                                    │                    │
                              errors? show form     send_alert() ──▶ business inbox
                              with values kept      send_confirmation() ──▶ customer
                                                         │
                                         paying by card? create_checkout() ──▶ Stripe page
                                                         │
                                         /paid confirms with Stripe ──▶ thank-you page
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
   The spreadsheet needs two tabs with these header rows:
   - first tab (orders): `Timestamp, Name, Phone, Email, Species, Size, Quantity, Flocked, Street, Apt, City, ZIP, Delivery date, Time window, Notes, Payment, Delivered, Paid`
   - `Customers`: `Email, Name, Phone, Password hash, Created`
3. Gmail: create an App Password for the sending account.
4. Stripe: create an account, switch to the sandbox (test mode), and copy the secret key (`sk_test_...`).
5. Create a `.env` file in the project root:
   ```
   SHEET_ID=
   GOOGLE_CREDENTIALS_FILE=credentials.json
   EMAIL_ADDRESS=
   EMAIL_APP_PASSWORD=
   ALERT_TO=
   SECRET_KEY=
   ADMIN_PASSWORD=
   STRIPE_SECRET_KEY=
   ```
6. Run `python app.py` and open http://127.0.0.1:5000

Note: email alerts work locally, but Render's free tier blocks outgoing email (SMTP), so the live demo saves orders without sending emails.

## Security notes

- Secrets live only in `.env` and `credentials.json`, both in `.gitignore`, and never in the code or Git history.
- Customer passwords are stored only as salted hashes (Werkzeug `generate_password_hash`); the login page gives the same message for an unknown email and a wrong password, so it can't be used to find out who has an account.
- Staff and customer logins use separate session keys, and a staff login ends any customer login in that browser.
- Every staff route checks the session, not just the deliveries page. The staff password check uses `secrets.compare_digest` (constant time).
- State-changing actions (`/admin/delivered`, `/logout`, `/account/logout`) are POST-only, with redirect-after-POST.
- Card payments go through Stripe Checkout, so card numbers never touch this app. The price is calculated on the server from `PRICES` (never taken from the form), and `/paid` confirms the payment with Stripe before marking the order paid.
- Tree types and sizes are checked against the server's own lists, so a value edited in DevTools is rejected.
- A member's order is always filed under their account email, and Premium is only checked for a logged-in customer against the trees in their own delivered orders, so nobody can claim someone else's discount by typing their email.


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

- A real cart, so one checkout can include several kinds of trees
- Automated tests (pytest) for `validate_order`, `order_total`, and the Premium rules
- Send emails through an HTTPS email API so alerts also work on the free hosting tier
- Spanish/English switch
