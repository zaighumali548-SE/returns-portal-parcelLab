# parcelLab — Returns Portal

This repository contains a completed pass on the returns portal challenge. The work focuses on the parts of the system that most directly affect correctness, customer trust, and the end-to-end return flow.

## What was implemented

- completed upstream order mapping for `is_digital`, `is_final_sale`, and `category`
- added a configurable YAML-backed eligibility engine
- added category-specific return windows with fallback to a default window
- fixed unauthorized cross-order article access
- restored the browser return flow from article selection through confirmation and success
- added an HTMX filter to show returnable items only
- added lookup throttling after repeated failed attempts as the scoped `OPEN-001` improvement
- expanded the test suite around the new behavior and security boundaries

## Prioritized backlog items

Completed:

- `BR-001` Complete the mapper gaps
- `BR-002` Build the return eligibility engine
- `BR-003` Fix and extend the test suite
- `BR-004` Category-specific return windows
- `SEC-001` Security audit
- `FR-001` Show returnable items only
- `FR-002` Fix the return submission flow
- `OPEN-001` Lookup abuse protection through throttling

The main tradeoff was to prioritize correctness, access control, and a complete customer journey over broader backlog coverage.

## Running locally

The repository assumes Python 3.12+ and Django.

Create a local environment and install dependencies:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Set up the local database and run the app:

```bash
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Open <http://localhost:8000/returns/> and use:

- order number: `RMA-1001`
- email: `alex@example.com`
- or zip: `10115`

## Validation

The implementation was validated with:

```bash
.venv/bin/pytest
.venv/bin/ruff check portal returns_portal
.venv/bin/mypy portal returns_portal
.venv/bin/python manage.py check
```

At the time of completion:

- `42` tests passing
- Ruff clean
- Mypy clean
- Django system checks clean

## Notes for a production system

For the scope of this exercise, the return submission flow stores state in the session and lookup throttling is also session-backed. In a production system, the next step would likely be persisting return requests, moving throttling to a shared boundary, and adding audit and metrics events around lookup failures, eligibility outcomes, and return submissions.

## Supporting documents

- `DECISIONS.md` explains prioritization, design choices, and tradeoffs
- `AI_LOG.md` documents where AI assistance was used and how the resulting changes were verified

## Original challenge brief

## The situation

You're joining the returns team for a day. We run the customer-facing returns portals for a lot of brands you have heard of. Customers look up their order, see which items are eligible for return, and submit a request, you might have been in this situation yourself. The portal is live, but it's rough around the edges: the previous engineer left before finishing some critical backend work, tests are failing, and a few things are broken.

Below is the current backlog. **You don't have to do everything** — pick the tasks that best show what you can do, and explain your choices in `DECISIONS.md`.

> Please do not fork this repository. Clone it without forking work locally, and submit as as personal repo on Github, Gitlab, Codeberg, or just zip us a file.

## Getting started

**Stack:** Python 3.13+, Django, pytest, ruff, mypy. PyYAML is included if you want it for rules config.

```bash
uv sync

pytest              # you'll see some failures — that's intentional
python manage.py runserver
```

Open <http://localhost:8000/returns/> and try order `RMA-1001` with email `alex@example.com` or zip `10115`.

### Project layout

```text
portal/
  data/orders_raw.json      # raw order payloads from upstream
  data/                     # your rules config goes here (you define the format)
  services/mapper.py        # maps raw payload → domain model (incomplete)
  services/eligibility.py   # return eligibility evaluator (stubbed)
  templates/returns/*       # Django + HTMX UI
  tests/*                   # pytest suite (some tests intentionally failing)
```

## Ground rules

> **Time limit: 4 hours.** If you hit the limit, stop and submit what you have. We'd rather see clean, well-reasoned partial work than a rushed complete solution.

**AI tools** are welcome. If you use them, keep a brief log in `AI_LOG.md` — we're curious how you use them, not whether you do.

## The backlog

Pick what matters. Prioritize, skip, reorder — just tell us why in `DECISIONS.md`.

---

### BR-001 · Complete the mapper gaps

Our upstream order system sends rich payloads, but the mapper was left unfinished — item-level flags never got wired up. The eligibility engine needs these to make decisions.

Missing fields on each article:

- `is_digital`
- `is_final_sale`
- `category`

Look at the raw data in `orders_raw.json` and the test fixtures to understand the different payload shapes you need to handle.

---

### BR-002 · Build the return eligibility engine

Right now, `evaluate_eligibility()` just marks everything as returnable. We need a real rules engine — one that's configurable, not hardcoded.

Design your own rules format (JSON, YAML, whatever you prefer) and implement the evaluator. It should return a clear result per item (returnable or not, reason, matched rule) and handle at least:

- Return window (delivered date + allowed days)
- Already fully returned
- Digital items
- Final-sale items

We intentionally don't provide a rules file — we want to see how you'd structure it.

---

### BR-003 · Fix and extend the test suite

Several tests are failing. Some depend on BR-001 and BR-002 being done, others may have their own issues. Make the suite green and add tests that give you confidence in your implementation.

---

### BR-004 · Category-specific return windows

Product just told us: different categories need different return windows. Electronics should be 14 days, apparel gets 30, and so on. If your rules engine is well-designed, this should be a natural extension — add per-category window config and make the evaluator respect it. Fall back to the order-level default when a category isn't configured.

---

### SEC-001 · Security audit

A security researcher has contacted us claiming they found a vulnerability that allows unauthorized access to customer order data. They want a hefty fee to disclose it. We'd rather find it ourselves. Audit the codebase, identify the issue, write a test that demonstrates the exploit, and fix it.

---

### FR-001 · Show returnable items only

Support keeps asking: can customers filter the articles list to only see what's actually returnable? Add a "Show returnable only" toggle using HTMX — no full page reload.

---

### FR-002 · Fix the return submission flow

The "Continue" button on the articles page is dead — the rest of the flow was apparently deleted before the last push. Build the missing pieces: article selection → confirmation → success. A customer should be able to complete a return end-to-end.

---

### OPEN-001 · Surprise us

See something that bugs you? Have an idea that would make the portal better? Go for it — just keep it scoped and tell us about it in `DECISIONS.md`.

---

## What to submit

- Working, type-safe code
- Small, readable commits
- `DECISIONS.md` — what you picked, what you skipped, and why
- `AI_LOG.md` — if you used AI tools

---

© parcelLab — May your returns always be smooth.
