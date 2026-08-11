# BidHaus

Online auction marketplace for second-hand, refurbished and collectible goods, built around
two guarantees: every seller is identity-verified, and every payment is held in escrow until
the buyer confirms reception.

Built with Python, Django and SQLite, following the Model–View–Template pattern. The interface
is plain HTML and CSS inside Django templates — no CSS framework, no JavaScript framework and
no CDN. The only third-party dependencies are Django and Pillow.

---

## Student Information

- **Full Name:** Cristian David Bolaños Giraldo, Juan Bedoya and Miguel Marín
- **Team:** Only code
- **Class:** ST0251
- **Course:** Proyecto Integrador 1
- **Professor:** _(fill in)_
- **University:** Universidad EAFIT — 2026-2

---

## Environment

- **Operating System:** Fedora Linux 44, kernel 7.1.5-200.fc44.x86_64, x64-based PC
- **Processor:** 13th Gen Intel(R) Core(TM) i5-13420H, 12 CPUs
- **Memory:** 16 GB RAM, 475 GB disk
- **Terminal:** GNU bash 5.3.9 (x86_64-redhat-linux-gnu)
- **Python:** 3.14.6
- **Django:** 6.0.7 · **Pillow:** 12.3.0

---

## Prerequisites

Before starting, make sure you have the following installed on your computer:

1. **Python 3.12 or higher** — Django 6.0 does not run on older versions.
   - Check installation: `python --version` or `python3 --version`
   - Download from: https://www.python.org/downloads/

2. **pip** (usually comes with Python)
   - Check installation: `pip --version` or `pip3 --version`

3. **Git** (optional, if you're going to clone the repository)
   - Check installation: `git --version`
   - Download from: https://git-scm.com/downloads

No database server is needed: SQLite ships with Python and the database file is created
by the migrations.

---

## Project Structure

```
BidHaus
├─ accounts                              User model, roles and the admin that seeds them
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  └─ __init__.py
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ managers.py
│  └─ models.py
├─ auctions                              Categories, auctions, photographs and bids
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_photograph.py
│  │  ├─ 0003_bid.py
│  │  └─ __init__.py
│  ├─ templatetags
│  │  ├─ __init__.py
│  │  └─ auction_formats.py
│  ├─ tests
│  │  ├─ __init__.py
│  │  ├─ factories.py
│  │  ├─ test_add_photographs.py
│  │  ├─ test_auction_bid_view.py
│  │  ├─ test_auction_catalogue_view.py
│  │  ├─ test_auction_create_view.py
│  │  ├─ test_auction_detail_view.py
│  │  ├─ test_auction_photographs_view.py
│  │  ├─ test_bid_history.py
│  │  ├─ test_place_bid.py
│  │  ├─ test_publish_auction.py
│  │  └─ test_search_auctions.py
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ exceptions.py                      Errors raised when a business rule is not met
│  ├─ forms.py                           Request validation
│  ├─ models.py                          Entities, fields and queries
│  ├─ services.py                        Use cases: publish, upload, search, bid
│  ├─ urls.py
│  ├─ validators.py
│  └─ views.py                           Parses the request, calls a service, renders
├─ bidhaus                               Project settings and root URL map
│  ├─ __init__.py
│  ├─ asgi.py
│  ├─ settings.py
│  ├─ urls.py
│  └─ wsgi.py
├─ static
│  ├─ css
│  │  └─ style.css
│  └─ img
│     ├─ favicon.svg
│     ├─ isotype.svg
│     ├─ logo-horizontal-inverse.svg
│     ├─ logo-horizontal-mono.svg
│     └─ logo-horizontal.svg
├─ templates
│  ├─ auctions
│  │  ├─ auction_detail.html
│  │  ├─ auction_form.html
│  │  ├─ catalogue.html
│  │  └─ photograph_form.html
│  └─ base.html
├─ .gitignore
├─ manage.py
└─ requirements.txt
```

### How the layers are separated

```
Template   templates/*.html      presentation only, no logic beyond loops and conditionals
View       views.py, forms.py    parses the request, calls a service, renders a template
Service    services.py           use case: transactions, orchestration, business rules
Model      models.py             entities, fields, relationships, queries
```

`services.py` is not a fifth element of MVT — it is how the View layer is kept thin.
A view never contains business logic and never builds a queryset by hand.

---

## Installation and Setup

### Step 1: Get the Code

```bash
git clone https://github.com/cbolanosz/BidHaus.git
cd BidHaus
```

### Step 2: Create a Virtual Environment

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

When the virtual environment is activated, you'll see `(venv)` at the beginning of your
command line.

### Step 3: Install Dependencies

With the virtual environment activated:

```bash
pip install -r requirements.txt
```

This will install:

- Django 6.0.7
- Pillow 12.3.0 — required by Django's `ImageField` to handle the auction photographs

### Step 4: Apply the Migrations

This creates `db.sqlite3` with every table the project needs:

```bash
python manage.py migrate
```

### Step 5: Create a Superuser

The admin panel is how users and categories are created, so this step is required, not
optional:

```bash
python manage.py createsuperuser
```

You'll be asked for:
- Email address (BidHaus identifies an account by email, not by username)
- Full name
- Password (you type it but it won't show on screen)

### Step 6: Seed the Data the Catalogue Needs

**There is no sign-up screen yet** — accounts are created from the Django admin during this
sprint. Start the server, open http://127.0.0.1:8000/admin/ and create:

1. **At least one Category** (for example *Fotografía*, *Audio*, *Relojes*).
2. **At least one user with the role Vendedor** — only a seller may publish an auction.
3. **At least one user with the role Comprador** — only a bidder may place a bid.

Without these, the publication form and the bid form will have empty dropdowns.

### Step 7: Run the Development Server

```bash
python manage.py runserver
```

You'll see a message similar to:

```
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

### Step 8: Open the Application

- **Main application:** http://127.0.0.1:8000/ or http://localhost:8000/
- **Admin panel:** http://127.0.0.1:8000/admin/ (use the superuser credentials)

---

## Routes

| Route | What it does | Requirement |
|---|---|---|
| `/` | Catalogue of open auctions, with search by text, category, condition and price range | FR03 |
| `/auctions/new/` | Publish an auction with its first photographs | FR01, FR02 |
| `/auctions/<id>/` | Auction detail: photographs, current price, countdown, bid form and full bid history | FR04 |
| `/auctions/<id>/bid/` | Registers a bid submitted from the detail page | FR05, FR06 |
| `/auctions/<id>/photographs/` | Adds photographs to an auction, up to 8 | FR02 |
| `/admin/` | Django admin, used to seed users and categories | — |

---

## Running the Tests

```bash
python manage.py test
```

The suite covers every service function: publishing, photograph limits, catalogue search,
the bid history and its immutability, and the bidding rules — including a case with 20
concurrent bidders.

```
Ran 83 tests
OK
```

The tests use a **file-based** SQLite database (`test_db.sqlite3`) instead of the in-memory
default, because WAL mode and the lock timeout that the bidding service relies on only exist
on a real file.

To run a single module:

```bash
python manage.py test auctions.tests.test_place_bid
```

---

## Configuration

The project runs with sensible defaults, so no `.env` file is required. Every value that
changes between machines can still be overridden with an environment variable:

| Variable | Default | Purpose |
|---|---|---|
| `BIDHAUS_SECRET_KEY` | insecure development key | Django secret key. **Must be set in production** |
| `BIDHAUS_DEBUG` | `true` | Debug mode. Set to `false` in production |
| `BIDHAUS_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed hosts |
| `BIDHAUS_DATABASE_PATH` | `db.sqlite3` in the project root | Location of the SQLite file |
| `BIDHAUS_TIME_ZONE` | `America/Bogota` | Time zone used for closing dates |
| `BIDHAUS_CURRENCY` | `COP` | Currency every stored amount is expressed in |

---

## Current Scope — Sprint 1

| ID | Requirement | State |
|---|---|---|
| FR01 | A registered seller publishes an auction with title, description, condition, category, starting price and closing date | Done |
| FR02 | The seller uploads between 1 and 8 photographs of at most 5 MB each | Done |
| FR03 | A user searches auctions by category, price range and condition | Done |
| FR04 | The auction detail displays the complete bid history, highest first | Done |
| FR05 | A registered bidder places a bid higher than the current price | Done |
| FR06 | The current price of the auction is updated after a bid is registered | Done |
| FR07 | An auction closes as soon as its closing date is reached | In progress |
| FR08 | The highest bid is marked as the winning bid after an auction closes | In progress |

Known limitations of this sprint:

- There is no sign-up or login yet, so the seller and the bidder are chosen from a dropdown
  in the form. Those fields disappear once authentication is implemented (FR30, FR31).
- The seller-rating filter of FR03 is not implemented, because ratings depend on completed
  escrow transactions, which belong to a later sprint (FR24).
- Payments are simulated. This is an academic project and never integrates a payment gateway
  nor stores card or bank data.

---

## Useful Commands

### Stop the Server
Press `Ctrl + C` in the terminal where the server is running.

### Deactivate the Virtual Environment
```bash
deactivate
```

### Create New Migrations (after modifying models)
```bash
python manage.py makemigrations
python manage.py migrate
```

### Check the Project for Problems
```bash
python manage.py check
```

### Run the Django Shell (for testing)
```bash
python manage.py shell
```

---

## Common Troubleshooting

### Error: "python is not recognized as a command"
- **Solution:** Make sure Python is installed and added to your system's PATH.
- Try using `python3` instead of `python`.

### Error: "No module named 'django'"
- **Solution:** Make sure the virtual environment is activated and that you ran
  `pip install -r requirements.txt`.

### Error: "Port is already in use"
- **Solution:** Port 8000 is already being used. You can:
  - Close the other process using the port
  - Use another port: `python manage.py runserver 8001`

### The publication form has an empty "Vendedor" dropdown
- **Cause:** No user has the role *Vendedor*. Only a registered seller may publish.
- **Solution:** Create one at http://127.0.0.1:8000/admin/ under **Usuarios**, or change the
  role of an existing user.

### The bid form has an empty "Pujador" dropdown
- **Cause:** No user has the role *Comprador*. Only a registered bidder may bid.
- **Solution:** Create one from the admin panel.

### Error uploading photographs
- **Solution:** Make sure Pillow is installed correctly: `pip install Pillow`.
  Each file must be a real image of at most 5 MB, and an auction accepts at most 8.

### Uploaded photographs are not displayed
- **Cause:** Media files are only served by the development server while `DEBUG` is `true`.
- **Solution:** Check that `BIDHAUS_DEBUG` is not set to `false` in your environment.

### Error: "database is locked"
- **Cause:** SQLite serialises writes, and another process is holding the database.
- **Solution:** Close any other `runserver` or `shell` session using the same file. The
  bidding service already retries this error before giving up.

### Migration issues
- **Solution:** Since the database holds no real data during development, the fastest fix is
  to delete `db.sqlite3` and run `python manage.py migrate` again, then recreate the
  superuser.

---

**Last updated:** August 2026
