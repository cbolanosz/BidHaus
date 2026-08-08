# BidHaus

> **Rename this file to `CLAUDE.md` and place it in the root of the repository.**
> It is self-contained: everything needed to work on this project is here.

Online auction marketplace for second-hand, refurbished and collectible goods, built around
two guarantees: **every seller is identity-verified**, and **every payment is held in escrow
until the buyer confirms reception**.

University project — ST0251 Proyecto Integrador 1, 2026-2, Universidad EAFIT.
Team **Only code**: Cristian Bolaños (Scrum Master), Juan Bedoya, Miguel Marín.

---

## 1. Hard constraints — do not violate

- **Stack: Python, Django and SQLite only.** No PostgreSQL, no MySQL, no other language,
  no other web framework, no JavaScript framework, no CSS framework, no CDN.
  The interface is plain HTML and CSS inside Django templates. The only third-party Python
  package allowed is **Pillow**, because Django's `ImageField` requires it.
- **Architecture: MVT (Model–View–Template)**, the pattern of Django.
- **Web application only.** No native mobile app, no SPA.
- **No real payments.** This is an academic project and is not authorised to process money.
  The escrow is a *simulated* state machine in our own database. Never integrate a payment
  gateway. Never collect or store card or bank data.
- **No external identity provider.** A seller uploads a document and an **administrator**
  approves or rejects it manually.
- **Everything in English:** code, comments, docstrings, commit messages, branch names,
  issue titles. Only the strings the visitor reads are in Spanish; prices in COP.
- Excluded from scope: international shipping, native mobile application.

---

## 2. Architecture — MVT

| Layer | Files | Responsibility |
|---|---|---|
| **Model** | `models.py` | Structures and manipulates the data. Entities, fields, relationships, database logic |
| **View** | `views.py`, `forms.py` | Processes the user's request and returns the response |
| **Template** | `templates/` | Presents the information to the user |

```
Browser ──► URL map (urls.py) ──► View ──► Model ──► View ──► Template ──► Response
```

### Separation of concerns inside MVT

The course also requires **layers and separation of concerns**. That is achieved by keeping
the use cases out of the views, in a `services.py` module of each app:

```
Template   templates/*.html      presentation only, no logic beyond loops and conditionals
View       views.py, forms.py    parses the request, calls a service, renders a template
Service    services.py           use case: transactions, orchestration, business rules
Model      models.py             entities, fields, relationships, queries
```

`services.py` is **not** a fifth element of MVT — it is how the View layer is kept thin.
The pattern is still Model–View–Template.

**Rules**

- A view must not contain business logic. It parses the request, calls a service, renders.
- A template must not contain business logic. No calculations, no queries.
- Anything that changes state lives in a service, inside `transaction.atomic()`.
- Only services and models touch the ORM. Views never build querysets by hand.

### Django apps

```
bidhaus/            project settings, root urls
accounts/           User, roles, verification requests            FR21–FR23, FR30–FR33
auctions/           Category, Auction, Photograph, Bid, closing   FR01–FR13
escrow/             EscrowTransaction, StateChange, Dispute       FR14–FR20
analytics/          FraudRiskScore, fair-price range              FR25–FR27
templates/          shared base templates
static/             CSS
media/              uploaded photographs and documents (not versioned)
```

---

## 3. Domain model

```
User ──1:N──► Auction ──1:N──► Bid ◄──N:1── User
 │                │
 │                ├──1:N──► Photograph               (between 1 and 8)
 │                ├──N:1──► Category
 │                ├──1:1──► FraudRiskScore
 │                └──1:0..1──► EscrowTransaction ──1:N──► StateChange
 │                                     │
 │                                     └──1:0..1──► Dispute ──1:N──► Evidence   (up to 5)
 │
 ├──1:0..1──► VerificationRequest
 └──1:N────► Rating                                  (two per completed transaction)
```

| Entity | Fields | Key rules |
|---|---|---|
| `User` | email (unique), password_hash, full_name, role, is_verified | Extends Django's user. Roles: bidder, seller, administrator |
| `Category` | name | |
| `Auction` | seller FK, category FK, title, description, condition, starting_price, current_price, closing_date, state, winning_bid FK | States: `open`, `closed`, `cancelled`. closing_date later than publication date |
| `Photograph` | auction FK, image, display_order | 1 to 8 per auction, max 5 MB each |
| `Bid` | auction FK, bidder FK, amount, timestamp | **Immutable once created.** Amount higher than current_price. Seller cannot bid on own auction |
| `EscrowTransaction` | auction FK, buyer FK, seller FK, amount, commission, state, created_at | One per closed auction. States: `held`, `released`, `refunded`, `in_dispute` |
| `StateChange` | transaction FK, previous_state, new_state, actor, timestamp | **Append-only. Never updated or deleted** |
| `Dispute` | transaction FK, opened_by FK, description, state, resolution | At most one per transaction |
| `Evidence` | dispute FK, file | Up to 5 per dispute |
| `Rating` | transaction FK, rater FK, rated FK, score, timestamp | Score 1–5. Nobody rates themselves. One per participant per transaction |
| `VerificationRequest` | seller FK, identity_document, state, resolved_by FK, resolved_at | One pending per seller. **Delete the document file once resolved** (Habeas Data) |
| `FraudRiskScore` | auction FK, score, factors, calculated_at | Integer 0–100 |

**Access rules.** Identity documents: administrator only. Escrow transactions and disputes:
their buyer, their seller and the administrator. Everything else in the catalogue is public.

---

## 4. Three things that are easy to get wrong

### 4.1 Concurrent bids on SQLite

`select_for_update()` is a **no-op on SQLite** — Django silently ignores it. SQLite serialises
writes with a database-level lock, which gives correctness but throws
`OperationalError: database is locked` under contention.

In the bidding service:

- Wrap the bid in `transaction.atomic()`.
- **Re-read the auction and re-validate the amount inside the transaction.** Never trust the
  price that was rendered in the form.
- Catch `OperationalError`, retry with a short backoff, and only then fail.
- Set `OPTIONS: {"timeout": 20}` in `DATABASES` and enable WAL mode on connection.

```python
# auctions/services.py
@transaction.atomic
def place_bid(auction_id, bidder, amount):
    """Register a bid on an open auction and update its current price."""
    auction = Auction.objects.select_for_update().get(pk=auction_id)  # no-op on SQLite, kept for portability
    if auction.state != Auction.State.OPEN:
        raise AuctionClosed
    if auction.closing_date <= timezone.now():
        raise AuctionClosed
    if auction.seller_id == bidder.id:
        raise SellerCannotBid
    if amount <= auction.current_price:
        raise BidTooLow(current_price=auction.current_price)

    bid = Bid.objects.create(auction=auction, bidder=bidder, amount=amount)
    auction.current_price = amount
    auction.save(update_fields=["current_price"])
    return bid
```

### 4.2 Closing auctions

Django has no built-in scheduler. Use a **management command** plus a lazy check:

- `python manage.py close_auctions` closes every auction whose `closing_date` has passed,
  marks the winning bid and creates the `EscrowTransaction`.
- The command must be **idempotent**: running it twice must not create two transactions.
- Also check on access: if an auction detail is requested after its closing date and it is
  still `open`, close it before rendering.
- In production it would be run by cron. Do not add Celery.

### 4.3 Escrow is append-only

Never update a status field in place and lose the history. Every transition writes a
`StateChange` row. A dispute is resolved from that history, so it is the evidence.

---

## 5. Sprint plan

Must → sprints 1–3 · Should → sprints 2–4 · Could → sprint 4 if time allows.

| Sprint | Requirements | Delivers |
|---|---|---|
| **1** | FR01–FR08 | The auction cycle: publish with photos, browse, bid, automatic close. Users seeded through the Django admin |
| **2** | FR09, FR10, FR11, FR21, FR22, FR30, FR31, FR32 | Real accounts, identity verification, verified badge, notifications |
| **3** | FR12, FR14, FR15, FR16, FR20, FR23, FR25, FR26 | Escrow money flow, fraud-risk score, commission |
| **4** | FR13, FR17, FR18, FR19, FR24, FR33, PR01, SR01 | Disputes, reputation, account recovery, performance, hashing |
| **4 (if time)** | FR27, FR28, FR29 | Contingency |

### Sprint 1 — current scope

**There is no sign-up or login UI yet.** Users are created from the Django admin.

| Route | Purpose |
|---|---|
| `/` | Catalogue with search and filters (FR03) |
| `/auctions/new/` | Publication form with photo upload (FR01, FR02) |
| `/auctions/<id>/` | Detail: photographs, current price, countdown, bid history, bid form (FR04, FR05) |
| `/admin/` | Django admin, to seed users and categories |

---

## 6. Requirements

Priority: **M** Must · **S** Should · **C** Could · **W** Won't have this time.
Every requirement is written with the specification template of the course:
`[condition] the <system> shall|should|could <activity> <object> <validation criteria>`.

### 6.1 Functional requirements

| ID | P | Sprint | Requirement |
|---|---|---|---|
| FR01 | M | 1 | The BidHaus system shall provide a registered seller with the ability to publish an auction with title, description, condition, category, starting price and closing date within 5 seconds. |
| FR02 | M | 1 | After the seller creates an auction, the BidHaus system shall provide the seller with the ability to upload between 1 and 8 photographs of at most 5 MB each within 10 seconds. |
| FR03 | M | 1 | The BidHaus system shall provide a user with the ability to search auctions by category, price range, condition and seller rating within 3 seconds. |
| FR04 | M | 1 | While a user is on the auction detail page, the BidHaus system shall display the complete bid history ordered from highest to lowest within 3 seconds. |
| FR05 | M | 1 | If a bidder submits an amount higher than the current highest bid, then the BidHaus system shall register the bid within 2 seconds. |
| FR06 | M | 1 | After a bid is registered, the BidHaus system shall update the current price of the auction within 2 seconds. |
| FR07 | M | 1 | As soon as the closing date of an auction is reached, the BidHaus system shall close the auction within 30 seconds. |
| FR08 | M | 1 | After an auction closes, the BidHaus system shall mark the highest bid as the winning bid within 30 seconds. |
| FR09 | S | 2 | After an auction closes, the BidHaus system should be able to send a result notification towards the email service of the winning bidder within 2 minutes. |
| FR10 | S | 2 | After an auction closes, the BidHaus system should be able to send a result notification towards the email service of the seller within 2 minutes. |
| FR11 | S | 2 | If a bid surpasses the bid of another bidder, then the BidHaus system should be able to send an outbid notification towards the email service of that bidder within 1 minute. |
| FR12 | S | 3 | After the user has published an auction, the BidHaus system should provide the user with the ability to consult all the auctions they have published within 3 seconds. |
| FR13 | S | 4 | After the user has placed a bid, the BidHaus system should provide the user with the ability to consult all the bids they have placed within 3 seconds. |
| FR14 | M | 3 | After an auction closes, the BidHaus system shall retain the payment of the winning bidder in an escrow account within 10 seconds. |
| FR15 | M | 3 | After the seller ships an item, the BidHaus system shall provide the buyer with the ability to confirm its reception within 3 seconds. |
| FR16 | M | 3 | After the buyer confirms the reception of an item, the BidHaus system shall release the retained funds towards the account of the seller within 24 hours. |
| FR17 | S | 4 | If the buyer does not receive the item as described, then the BidHaus system should provide the buyer with the ability to open a dispute within 10 seconds. |
| FR18 | S | 4 | After the buyer opens a dispute, the BidHaus system should provide the buyer with the ability to attach up to 5 evidence files within 10 seconds. |
| FR19 | S | 4 | After a dispute is opened, the BidHaus system should provide an administrator with the ability to resolve it within 24 hours. |
| FR20 | S | 3 | As soon as the funds of an auction are released, the BidHaus system should deduct the platform commission from the payment of the seller within 10 seconds. |
| FR21 | M | 2 | Before the seller publishes their first auction, the BidHaus system shall provide the seller with the ability to submit an identity document for verification within 5 seconds. |
| FR22 | M | 2 | While a user is viewing an auction of a verified seller, the BidHaus system shall display the verified-seller badge within 2 seconds. |
| FR23 | S | 3 | After a seller submits an identity document, the BidHaus system should provide an administrator with the ability to approve or reject the request within 5 seconds. |
| FR24 | S | 4 | After a transaction is completed, the BidHaus system should provide each participant with the ability to rate the counterpart from 1 to 5 stars within 3 seconds. |
| FR25 | M | 3 | After an auction is published, the BidHaus system shall calculate a fraud-risk score between 0 and 100 for that auction within 1 minute. |
| FR26 | M | 3 | While a user is on the auction detail page, the BidHaus system shall display the fraud-risk score of the auction within 3 seconds. |
| FR27 | C | 4 | While a user is on the auction detail page, the BidHaus system could display the fair-price range of the item, calculated from the closing prices of the last 6 months in the same category and condition, within 3 seconds. |
| FR28 | C | 4 | After the seller completes their first sale, the BidHaus system could provide the seller with the ability to consult a dashboard with sales, average rating, disputes and completion rate within 5 seconds. |
| FR29 | C | 4 | While an auction is open, the BidHaus system could provide a bidder with the ability to define a maximum amount for automatic proxy bidding within 2 seconds. |
| FR30 | S | 2 | Before the visitor places a bid, the BidHaus system should provide the visitor with the ability to create an account with email, password and full name within 5 seconds. |
| FR31 | S | 2 | Before the user accesses their account, the BidHaus system should provide the user with the ability to log in with email and password within 3 seconds. |
| FR32 | S | 2 | After the user logs in, the BidHaus system should provide the user with the ability to log out within 2 seconds. |
| FR33 | S | 4 | If the user forgets their password, then the BidHaus system should provide the user with the ability to reset it through a recovery link sent to their email within 2 minutes. |
| FR34 | W | — | The BidHaus system won't provide a seller with the ability to offer international shipping. |
| FR35 | W | — | The BidHaus system won't provide a user with the ability to operate through a native mobile application. |

### 6.2 Usability requirements

| ID | Requirement | Metric |
|---|---|---|
| UR01 | After first accessing the platform, a seller shall be able to complete the publication of an auction without external assistance. | No more than 5 screens or form sections from start to confirmation |
| UR02 | While a user is on the auction detail page, the BidHaus system shall provide the bidder with the ability to place a bid in at most 2 clicks. | Clicks from detail page to bid confirmation ≤ 2 |
| UR03 | While a transaction is in progress, the BidHaus system shall display its escrow state within 3 seconds. | The four states are visible on the transaction page |
| UR04 | If a user submits a form with an invalid value, then the BidHaus system shall display an error message in Spanish indicating the field that caused it within 2 seconds. | 100 % of validation messages identify the field and the correction |
| UR05 | The BidHaus system shall display each page correctly in viewports between 360 and 1920 pixels wide. | No horizontal scrolling and no overlap at 360, 768, 1024 and 1920 px |
| UR06 | The BidHaus system shall display all the text content with a contrast ratio of at least 4.5:1 according to WCAG 2.1 level AA. | Contrast ≥ 4.5:1 in 100 % of text elements |
| UR07 | The BidHaus system should provide a user with the ability to reach an auction of a given category from the home page in at most 3 interactions. | Interactions from home to auction detail ≤ 3 |
| UR08 | While an auction is open, the BidHaus system should display its current price, its remaining time and its bid history on a single page. | The three elements are visible without navigating away |

### 6.3 Logical database requirements

One requirement per entity. Each one carries its own integrity constraint, access rule and
retention rule.

| ID | Requirement | Integrity · Access · Retention |
|---|---|---|
| DBR01 | The BidHaus system shall store for each user: unique email address, hashed password, full name, role, verification state and account creation date. | Email unique · The hashed password is readable by no role · Stored until account deletion |
| DBR02 | The BidHaus system shall store for each auction: seller, category, title, description, condition, starting price, current price, closing date, state and winning bid. | Closing date later than publication date · Readable by anyone, writable only by its seller while open · Stored 5 years after closing |
| DBR03 | The BidHaus system shall store for each auction between 1 and 8 photographs, each one with its auction reference, its file reference and its display order. | 1 to 8 per auction, none over 5 MB · Readable by anyone, writable only by the seller · Stored while its auction is stored |
| DBR04 | The BidHaus system shall store for each bid: auction, bidder, amount and timestamp. | **Amount higher than the current price at the moment of registration; the bidder is not the seller; concurrent registrations are serialised** · Readable by anyone, **not modifiable nor deletable by any role** · Stored 5 years with its auction |
| DBR05 | The BidHaus system shall store for each closed auction one escrow transaction with: auction, buyer, seller, amount, commission, current state and creation timestamp. | At most one per auction; state in held, released, refunded, in_dispute · Restricted to its buyer, its seller and the administrator · Stored 5 years after closing |
| DBR06 | The BidHaus system shall store for each change of state of an escrow transaction: the transaction, the previous state, the new state, the actor and the timestamp. | **Never modified nor deleted once created** · Readable by the participants and the administrator · Stored 5 years with its transaction |
| DBR07 | The BidHaus system shall store for each dispute: the escrow transaction, the buyer who opened it, its description, its state, its resolution and up to 5 evidence files. | At most one dispute per transaction, at most 5 evidence files · Restricted to its buyer, its seller and the administrator · Stored 5 years after resolution |
| DBR08 | The BidHaus system shall store for each verification request: the seller, the identity document, its state, the administrator who resolved it and the resolution timestamp. | One pending request per seller · **Identity document readable only by the administrator** · **The document is deleted once the request is resolved**; only the result is retained |
| DBR09 | The BidHaus system shall store for each completed transaction up to two ratings, each one with rater, rated user, score and timestamp. | Score 1–5; nobody rates themselves; one rating per participant per transaction · Readable by anyone, writable only by the participants · Kept while the rated account exists |
| DBR10 | The BidHaus system shall store for each published auction its fraud-risk score, the date of its calculation and the factors that produced it. | Score is an integer 0–100 · Readable by anyone · Stored while its auction is stored |

### 6.4 Performance and security requirements

| ID | P | Requirement |
|---|---|---|
| PR01 | S | While at least 20 users are placing bids concurrently, the BidHaus system should register each bid within 2 seconds. |
| SR01 | S | The BidHaus system should store all the user passwords hashed according to the OWASP password storage standard. |
| SR02 | M | The BidHaus system shall transmit all the traffic between the browser and the server according to the HTTPS protocol. |

---

## 7. Code quality

This is graded work. Readability matters more than cleverness. A teammate — or a professor —
must understand any function on the first read.

### Clean code

- **Names say what things are.** `current_price`, `place_bid`, `close_expired_auctions`.
  Never `data`, `info`, `temp`, `x`, `aux`, `helper`, `manager2`, `do_stuff`.
- **A function does one thing** and its name says which. If you need "and" to describe it,
  split it.
- **Short functions.** If one exceeds ~20 lines, it is doing too much.
- **No magic numbers or strings.** Use module constants or `TextChoices`:
  `Auction.State.OPEN`, not `"open"`; `MAX_PHOTOGRAPHS = 8`, not `8`.
- **Guard clauses, not nesting.** Validate and raise early; keep the happy path unindented.
  Never nest more than two levels.
- **Comments explain *why*, never *what*.** If a comment is needed to explain what the code
  does, rename things instead. Docstring on every service function.
- **Delete dead code.** No commented-out blocks, no unused imports, no "just in case"
  functions, no parameters nobody passes.
- **Do not repeat yourself**, but do not abstract on the first repetition either. Two similar
  lines are fine; three copies of the same rule are a bug waiting to happen.

### SOLID, applied to this project

- **Single responsibility.** A model holds data and its own invariants. A service holds one
  use case. A view translates HTTP. Nothing does two of those.
- **Open/closed.** New auction states or new fraud-risk factors are added by extending a
  registry or a choices class, not by growing an `if/elif` chain inside a service.
- **Liskov.** Any subclass must be usable wherever the parent is, without the caller checking
  its type.
- **Interface segregation.** Small, focused functions and forms. No service function with a
  dozen optional parameters that behaves differently for each combination.
- **Dependency inversion.** Services depend on abstractions, not on details. Sending an email
  goes through `notifications.py`; a service never imports `django.core.mail` directly.

### Never

- Spaghetti code: no logic scattered between a view, a template and a model for the same rule.
- Speculative code: implement only what the current requirement asks for.
- Business logic in templates, or querysets built inside a view.
- A `try/except` that swallows an error silently.
- Code, comments, docstrings, commit messages or identifiers in Spanish.

---

## 8. Conventions

- Commits reference the requirement: `FR05: register a bid inside an atomic transaction`.
- One branch per requirement: `fr05-place-bid`.
- Every service function has a test. Priority: the bidding rules and the closing command.
- Use `DecimalField` for money, never `FloatField`.
- Timezone `America/Bogota`, `USE_TZ = True`. Always compare with `timezone.now()`.
- Configuration from environment variables: database path, SMTP credentials, commission
  percentage, currency, timezone.
- Media files: `MEDIA_ROOT` / `MEDIA_URL`, Pillow installed. Photographs are served as media,
  never loaded into memory.

## 9. Commands

```bash
python manage.py runserver
python manage.py makemigrations && python manage.py migrate
python manage.py createsuperuser
python manage.py close_auctions        # closes expired auctions and creates escrow rows
python manage.py test
```

## 10. Do not

- Do not add a payment gateway or a KYC provider.
- Do not switch the database engine.
- Do not add any dependency beyond Django and Pillow — no Bootstrap, no Tailwind, no jQuery,
  no HTMX, no REST framework, no Celery.
- Do not put business logic in views or templates.
- Do not modify or delete a `Bid` or a `StateChange` once created.
- Do not implement anything outside the current sprint without being asked.
