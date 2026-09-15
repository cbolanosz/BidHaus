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
- **Professor:** Paola Vallejo
- **University:** Universidad EAFIT — 2026-2

---

## Environment

The project is developed on more than one machine. It runs the same on all of them, because
the only requirements are Python and the three packages in `requirements.txt`.

**Machine 1 — Cristian**

- **Operating System:** Fedora Linux 44, kernel 7.1.5-200.fc44.x86_64, x64-based PC
- **Processor:** 13th Gen Intel(R) Core(TM) i5-13420H, 12 CPUs
- **Memory:** 16 GB RAM, 475 GB disk
- **Terminal:** GNU bash 5.3.9 (x86_64-redhat-linux-gnu)
- **Python:** 3.14.6

**Machine 2 — _(name)_**

- **Operating System:** _(fill in)_
- **Processor:** _(fill in)_
- **Memory:** _(fill in)_
- **Terminal:** _(fill in)_
- **Python:** _(fill in)_

**Shared across every machine:** Django 6.0 · Pillow 12.3 · python-dotenv 1.1 · SQLite (bundled with Python)

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
├─ accounts                              Accounts, roles and identity verification
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_verificationrequest.py
│  │  └─ __init__.py
│  ├─ tests
│  │  └─ …                               One module per requirement
│  ├─ __init__.py
│  ├─ admin.py                           Where an administrator resolves a request
│  ├─ apps.py
│  ├─ exceptions.py
│  ├─ forms.py
│  ├─ managers.py
│  ├─ models.py                          User and VerificationRequest
│  ├─ services.py                        Sign up, log in, submit and resolve a request
│  ├─ urls.py
│  ├─ validators.py
│  └─ views.py
├─ auctions                              Categories, auctions, photographs and bids
│  ├─ management
│  │  └─ commands
│  │     └─ close_auctions.py            Run by cron; closes and notifies (FR07-FR10)
│  ├─ migrations
│  │  ├─ 0001_initial.py
│  │  ├─ 0002_photograph.py
│  │  ├─ 0003_bid.py
│  │  ├─ 0004_auction_winning_bid.py
│  │  └─ __init__.py
│  ├─ templatetags
│  │  ├─ __init__.py
│  │  └─ auction_formats.py
│  ├─ tests
│  │  ├─ __init__.py
│  │  ├─ factories.py                    Objects a test needs
│  │  ├─ mailbox.py                      Reading the emails a use case sent
│  │  └─ …                               One module per requirement
│  ├─ __init__.py
│  ├─ admin.py
│  ├─ apps.py
│  ├─ exceptions.py                      Errors raised when a business rule is not met
│  ├─ forms.py                           Request validation
│  ├─ models.py                          Entities, fields and queries
│  ├─ notifications.py                   The emails an auction sends (FR09-FR11)
│  ├─ services.py                        Use cases: publish, upload, search, bid, close
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
│  ├─ accounts
│  │  ├─ login.html
│  │  ├─ signup.html
│  │  └─ verification_request.html
│  ├─ auctions
│  │  ├─ email                           The body of every notification
│  │  │  ├─ auction_result_seller.txt
│  │  │  ├─ auction_won.txt
│  │  │  └─ outbid.txt
│  │  ├─ auction_detail.html
│  │  ├─ auction_form.html
│  │  ├─ catalogue.html
│  │  └─ photograph_form.html
│  └─ base.html
├─ .env.example                          Every key the .env expects, with no secrets
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

`notifications.py` is a collaborator the services call, not a fifth layer: it turns a fact
the service has just recorded into an email, and it renders the body from a template like
every other piece of text a user reads.

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

- Django 6.0
- Pillow 12.3 — required by Django's `ImageField` to handle the auction photographs
- python-dotenv 1.1 — reads the `.env` where the mail credentials live

### Step 4: Create the `.env`

BidHaus sends its notifications for real, so it needs the credentials of a mailbox.
They never live in the repository: `.env` is ignored by Git, and `.env.example` lists
every key with a comment.

```bash
cp .env.example .env        # macOS and Linux
copy .env.example .env      # Windows
```

Open it and fill in the only two values that are required:

```ini
BIDHAUS_EMAIL_HOST_USER=tucorreo@gmail.com
BIDHAUS_EMAIL_HOST_PASSWORD=abcdefghijklmnop
```

With Gmail that password is **not** the one you type to log in: it is a 16-character
*app password*, and the account needs two-step verification enabled before Google will
generate one. Create it at https://myaccount.google.com/apppasswords.

A real environment variable always wins over the file, so a server can set one without
editing anything.

### Step 5: Apply the Migrations

This creates `db.sqlite3` with every table the project needs:

```bash
python manage.py migrate
```

### Step 6: Create a Superuser

The admin panel is how users and categories are created, so this step is required, not
optional:

```bash
python manage.py createsuperuser
```

You'll be asked for:
- Email address (BidHaus identifies an account by email, not by username)
- Full name
- Password (you type it but it won't show on screen)

### Step 7: Seed the Categories

Anyone can now create their own account from `/accounts/signup/`, so only the categories
still have to be seeded by hand. Start the server, open http://127.0.0.1:8000/admin/ and
create **at least one Category** (for example *Fotografía*, *Audio*, *Relojes*). Without
one, the publication form has an empty dropdown.

A new account starts with the role *Comprador*, which is enough to bid. Publishing needs
the role *Vendedor*, and that is what an approved identity verification grants (FR21, FR23):

1. Log in and send an identity document from **«Verifica tu identidad»**.
2. Open the admin as an administrator, go to **Solicitudes de verificación**, select the
   request and run the action **Aprobar**.

The account that approves must itself have the role *Administrador*. Give your superuser
that role from **Usuarios** in the admin the first time.

### Step 8: Run the Development Server

```bash
python manage.py runserver
```

You'll see a message similar to:

```
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.
```

### Step 9: Open the Application

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
| `/accounts/signup/` | Creates an account from an email, a name and a password | FR30 |
| `/accounts/login/` | Starts a session | FR31 |
| `/accounts/logout/` | Ends the session. POST only | FR32 |
| `/accounts/verification/` | Sends an identity document and lists what was answered | FR21 |
| `/accounts/verification/<id>/document/` | Serves a document to an administrator only | DBR08 |
| `/admin/` | Django admin: categories, roles, and the verification decisions | FR23 |

---

The tests use a **file-based** SQLite database (`test_db.sqlite3`) instead of the in-memory
default, because WAL mode and the lock timeout that the bidding service relies on only exist
on a real file.

To run a single module:

```bash
python manage.py test auctions.tests.test_place_bid
```

---

## Configuration

Every value that changes between machines is read from an environment variable, and
`settings.py` loads a `.env` from the project root before reading them. Only the two mail
credentials have no usable default; everything else runs as it is:

| Variable | Default | Purpose |
|---|---|---|
| `BIDHAUS_SECRET_KEY` | insecure development key | Django secret key. **Must be set in production** |
| `BIDHAUS_DEBUG` | `true` | Debug mode. Set to `false` in production |
| `BIDHAUS_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated list of allowed hosts |
| `BIDHAUS_DATABASE_PATH` | `db.sqlite3` in the project root | Location of the SQLite file |
| `BIDHAUS_TIME_ZONE` | `America/Bogota` | Time zone used for closing dates |
| `BIDHAUS_CURRENCY` | `COP` | Currency every stored amount is expressed in |
| `BIDHAUS_IDENTITY_DOCUMENT_ROOT` | `private-media/` | Where identity documents are kept, outside `MEDIA_ROOT` |
| `BIDHAUS_SITE_URL` | `http://127.0.0.1:8000` | Address the links inside an email point at |
| `BIDHAUS_EMAIL_HOST_USER` | empty | **Required.** The mailbox the notifications are sent from |
| `BIDHAUS_EMAIL_HOST_PASSWORD` | empty | **Required.** Its app password, never the login password |
| `BIDHAUS_EMAIL_BACKEND` | SMTP backend | Set it to the console backend to develop without sending |
| `BIDHAUS_DEFAULT_FROM_EMAIL` | the value of `BIDHAUS_EMAIL_HOST_USER` | Address in the `From:` header |
| `BIDHAUS_EMAIL_HOST` | `smtp.gmail.com` | SMTP server |
| `BIDHAUS_EMAIL_PORT` | `587` | Port of the SMTP server |
| `BIDHAUS_EMAIL_USE_TLS` | `true` | Whether to open the SMTP connection with TLS |
| `BIDHAUS_EMAIL_TIMEOUT` | `10` | Seconds to wait for the SMTP server before giving up |

---

## Closing Auctions and Notifications

Django has no scheduler of its own, so nothing happens on a clock unless something runs the
`close_auctions` command. Closing an auction is what marks its winning bid and what sends
the two result notifications, so the same command covers FR07 to FR10:

```bash
python manage.py close_auctions
```

Running it twice in a row is harmless: the second run finds nothing to close and sends
nothing. In production it is run by cron. Running it **every 30 seconds** keeps both
deadlines with room to spare — the 30 seconds FR07 allows for the closing, and the 2 minutes
FR09 and FR10 allow for the result reaching the winner and the seller:

```cron
* * * * * cd /srv/bidhaus && .venv/bin/python manage.py close_auctions
* * * * * sleep 30; cd /srv/bidhaus && .venv/bin/python manage.py close_auctions
```

Between two runs of the command, an auction that is already past its closing date is also
closed the moment somebody opens its page, so a visitor never sees a countdown on an auction
that is over. That path sends the notifications too.

The outbid notification of FR11 needs no scheduler at all: it goes out as part of
registering the bid that displaced the previous one.

### Where the emails go

They are sent, for real, over SMTP. The notifications are part of the product, so the
default is a working mailbox and not a console transcript. Fill in the two credentials of
Step 4 and the three messages reach their recipient.

Every message is queued with `transaction.on_commit`, so nothing is ever announced that the
database rolled back a moment later, and a mail server that cannot be reached is written to
the log instead of undoing the bid or the closing that caused the message. That failure is
printed by the `auctions.notifications` logger, so a wrong password shows up in the terminal
rather than disappearing.

`BIDHAUS_SITE_URL` matters as much as the credentials: an email is read outside the browser
that opened the site, so the link it carries has to be absolute.

To check the configuration without going through a whole auction:

```bash
python manage.py shell
```
```python
from django.core.mail import send_mail
send_mail("Prueba", "¿Llegó?", None, ["tucorreo@gmail.com"])   # devuelve 1 si salió
```

While developing, sending a real message on every bid gets in the way. Comment the backend
back to the console in your own `.env` and the messages are printed in the terminal instead:

```ini
BIDHAUS_EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

The tests never send anything: Django swaps the backend for an in-memory one on its own, and
`auctions/tests/mailbox.py` is what reads that mailbox.

| Email | Sent when | To |
|---|---|---|
| *Ganaste la subasta «…»* | The auction closes with a winning bid | The winning bidder (FR09) |
| *Cerró tu subasta «…»* | The auction closes, with or without bids | The seller (FR10) |
| *Superaron tu puja en «…»* | A bid displaces the highest one | The bidder who held it (FR11) |

A bidder who raises their own highest bid outbids nobody but themselves, so no message is
sent. Only the bidder who actually held the lead is written to: everybody else further down
the history was already told when it was their turn to be passed.

---

## Current Scope — Sprint 2

Sprint 1 delivered the catalogue and the bidding; sprint 2 closes an auction on its own,
tells the people it concerns, and puts a verified identity behind every seller.

| ID | Requirement | Sprint | State |
|---|---|---|---|
| FR01 | A registered seller publishes an auction with title, description, condition, category, starting price and closing date | 1 | Done |
| FR02 | The seller uploads between 1 and 8 photographs of at most 5 MB each | 1 | Done |
| FR03 | A user searches auctions by category, price range and condition | 1 | Done |
| FR04 | The auction detail displays the complete bid history, highest first | 1 | Done |
| FR05 | A registered bidder places a bid higher than the current price | 1 | Done |
| FR06 | The current price of the auction is updated after a bid is registered | 1 | Done |
| FR07 | An auction closes as soon as its closing date is reached | 2 | Done |
| FR08 | The highest bid is marked as the winning bid after an auction closes | 2 | Done |
| FR09 | The winning bidder is notified of the result after an auction closes | 2 | Done |
| FR10 | The seller is notified of the result after an auction closes | 2 | Done |
| FR11 | A bidder is notified when their bid is outbid | 2 | Done |
| FR21 | A user submits identity documents to be verified as a seller | 2 | Done |
| FR22 | The verified-seller badge is displayed next to the seller | 2 | Done |
| FR23 | An administrator approves or rejects an identity-verification request | 2 | Done |
| FR30 | A visitor signs up for an account | 2 | Done |
| FR31 | A registered user logs in | 2 | Done |
| FR32 | A logged-in user logs out | 2 | Done |

Known limitations of this sprint:

- Notifications are sent synchronously, in the same process that closed the auction or
  registered the bid, which means a bid that outbids somebody waits for the SMTP server
  before the page answers — normally a second or two. That is what a project of this size
  needs; a real deployment would hand them to a queue.
- The seller-rating filter of FR03 is not implemented, because ratings depend on completed
  escrow transactions, which belong to a later sprint (FR24).
- Escrow itself is not implemented yet, so the result email tells the winner that the seller
  will contact them, and no payment is held anywhere.
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

### Close the Auctions Whose Date Has Passed
```bash
python manage.py close_auctions
```
This also marks the winning bid and sends the result notifications. See
*Closing Auctions and Notifications* above.

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

### "Para publicar necesitas verificar tu identidad antes"
- **Cause:** The account has not been verified, and only a verified seller may publish.
- **Solution:** Send an identity document from **«Verifica tu identidad»** and approve the
  request from the admin, as described in Step 6.

### An auction is past its closing date but still says "Abierta" in the catalogue
- **Cause:** Nothing has run `close_auctions` since the date passed. The catalogue reads the
  stored state; it does not close anything by itself.
- **Solution:** Run `python manage.py close_auctions`, or open the auction's own page, which
  closes it on the spot. In production, let cron run the command.

### No notification arrives
- **Cause:** Almost always the credentials. Look at the terminal: the
  `auctions.notifications` logger prints what went wrong.
- **`SMTPAuthenticationError`:** the password is not an app password, or two-step
  verification is off on that Google account.
- **Nothing at all in the log:** there was nothing to send. The first bid on an auction
  outbids nobody, and a bidder who raises their own leading bid outbids nobody either.
- **`ModuleNotFoundError: No module named 'dotenv'`:** run `pip install -r requirements.txt`
  again; the `.env` is read by a package that was added in Sprint 2.

### The link inside a notification points at 127.0.0.1
- **Cause:** `BIDHAUS_SITE_URL` still holds its development default.
- **Solution:** Set it to the address the site actually answers at.

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

**Last updated:** September 2026
