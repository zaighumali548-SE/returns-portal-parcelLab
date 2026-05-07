# AI Log

Tool:
Codex / GPT-based coding assistant in the local repository.

Prompt summary:
Used to quickly inspect the repository, summarize failing tests, and surface the highest-risk gaps before implementation started. The main focus was narrowing the work to the returns decision path, the article access issue, and the missing continuation flow.

How you verified the output:
Reviewed the suggested scope against the backlog and the existing codebase before making changes. The final selection was based on the repository structure, failing tests, and the impact of each issue on correctness and customer data exposure.


Tool:
Codex / GPT-based coding assistant in the local repository.

Prompt summary:
Used for first-pass scaffolding in the mapper and eligibility services, especially around repetitive transformation logic and rule coverage. The prompts focused on normalizing upstream item fields, wiring them into the internal domain model, and exercising the main non-returnable cases.

How you verified the output:
Checked the resulting logic directly against `portal/data/orders_raw.json` and the existing fixtures, then tightened the implementation where needed. Verified behavior with targeted tests for item flags, category handling, return-window evaluation, and already-returned quantities.


Tool:
Codex / GPT-based coding assistant in the local repository.

Prompt summary:
Used to draft a first pass of the browser flow changes for article filtering and the missing return continuation path, keeping the work aligned with the existing Django + HTMX approach rather than introducing a new frontend pattern.

How you verified the output:
Reviewed the generated view and template changes before keeping them, then validated the result with view tests and a manual browser pass through lookup, articles, confirmation, and success states.


Tool:
Codex / GPT-based coding assistant in the local repository.

Prompt summary:
Used to enumerate likely abuse paths on the public lookup surface and sketch a minimal hardening option. That led to the session-backed throttle on repeated failed lookups across both the browser and API entry points.

How you verified the output:
Confirmed the final implementation with dedicated browser and API tests, checked the lockout and reset behavior, and reran the full validation set (`pytest`, `ruff`, `mypy`, and `manage.py check`) after the hardening work landed.
