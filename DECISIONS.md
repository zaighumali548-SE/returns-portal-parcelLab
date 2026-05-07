# Decisions

Decision:
Prioritized the work in this order: mapper completeness, configurable eligibility, category-specific windows, API authorization hardening, then the customer-facing returns flow.

Rationale:
The portal’s primary responsibility is to make correct return decisions against real order data. That required getting the domain model right before adding behavior on top of it. The mapper gaps and the stubbed eligibility engine were upstream blockers for both the UI and the API. The authorization issue on article access was also high priority because it affected customer data exposure, so it was addressed before treating the flow as complete.

Alternatives considered:
Starting with the visible UI issues first, especially the missing continuation flow. That would have improved the demo earlier, but it would have left incorrect decisioning and a security gap underneath it.


Decision:
Implemented return eligibility as a configuration-driven service backed by YAML, rather than hardcoding policy directly in application code.

Rationale:
The business rules in scope are policy decisions, not framework behavior. Representing them in configuration keeps the evaluator small and makes future changes easier to reason about. It also made the category-specific window requirement a natural extension instead of a refactor. The resulting shape is intentionally simple: evaluate a small ordered set of non-returnable conditions, record the matched rule, and otherwise mark the item returnable.

Alternatives considered:
Hardcoded conditionals only, or a more generic rule engine abstraction. Hardcoding would have been faster initially but less adaptable. A larger rule framework would have added ceremony that the challenge does not need.


Decision:
Used explicit item-level eligibility results with `returnable`, `reason`, and `matched_rule` instead of returning only a boolean.

Rationale:
In a returns portal, “why not?” matters almost as much as “yes or no.” Support teams, future API consumers, and template code all benefit from deterministic explanations. Returning structured reasons also creates a stable seam for future analytics, localization, or customer messaging improvements.

Alternatives considered:
Returning only `True`/`False`, or embedding explanation text directly inside templates. A boolean alone would be too weak for product and support needs. Template-only explanations would push business logic out of the service layer.


Decision:
Applied category-specific return windows in the rules configuration, with fallback to a default order-level window.

Rationale:
This matched the stated product need while keeping policy centralized. The implementation keeps category overrides explicit and unsurprising, and it avoids scattering category logic across views or templates. The fallback preserves sane behavior for uncategorized or newly introduced categories.

Alternatives considered:
Encoding category windows directly in Python, or requiring every category to be declared. Hardcoding increases maintenance cost. Making every category mandatory would be brittle for incomplete upstream data.


Decision:
Completed the mapper by normalizing category and deriving `is_digital` and `is_final_sale` across multiple upstream payload shapes.

Rationale:
The sample data and fixtures already showed that upstream payloads are not perfectly uniform. The mapper therefore needed to be defensive and derive the same internal flags from multiple raw representations. Doing that work in the mapper keeps the eligibility engine clean and ensures downstream code consumes a stable domain model.

Alternatives considered:
Teaching the eligibility layer to inspect raw payload quirks directly. That would have mixed mapping concerns with business policy and made testing harder.


Decision:
Fixed article access authorization by binding the articles endpoint to the specific order authenticated in session.

Rationale:
The existing behavior allowed a user who had authenticated one order to request another order’s articles by changing the URL. That is the highest-risk defect in the codebase because it can expose customer order data. The fix is intentionally narrow: the session must match the requested order number before article data is returned.

Alternatives considered:
Relying on the lookup step alone, or treating order numbers as effectively unguessable. Neither is a sound security assumption for a customer-facing system.


Decision:
Implemented the “show returnable only” behavior as an HTMX-driven partial update instead of a larger client-side state rewrite.

Rationale:
The repository is already server-rendered and already includes HTMX. Using a partial render kept the feature aligned with the current stack, preserved server-side truth for eligibility, and avoided introducing unnecessary front-end complexity. The filter also preserves in-progress selection state, which keeps it practical rather than purely cosmetic.

Alternatives considered:
Adding a richer client-side selection model or building the filter exclusively in JavaScript. That would have widened the implementation surface for limited benefit.


Decision:
Restored the return submission flow as a simple multi-step server-side interaction: article selection, confirmation, and success.

Rationale:
For the current scope, the goal was to make the customer journey complete and reliable without over-designing persistence that the app does not yet have. Session-backed pending return state is sufficient for the exercise and keeps the implementation cohesive with the existing browser flow. The confirmation step also creates a clean place to validate selected quantities server-side before final submission.

Alternatives considered:
Compressing everything into a single page submit, or introducing a database-backed return request model immediately. A single-step flow removes a useful validation checkpoint. A persistence model may be appropriate later, but it is broader than the current challenge requires.


Decision:
Used the open-ended scope for lookup throttling after repeated failures across both the browser and API entry points.

Rationale:
Once article authorization was fixed, the next most obvious production concern was abuse on the public lookup surface. A small throttle on repeated failed lookups improves resilience against brute-force attempts without changing the normal customer path. It also strengthens both entry points consistently, which is the right boundary for this kind of control.

Alternatives considered:
Additional UI polish, more filtering options, or duplicate-submit protection on the return submission step. Those are all defensible ideas, but the lookup surface was the more meaningful operational improvement for the time available.


Decision:
Expanded the test suite around behavior boundaries rather than only fixing the existing failing assertions.

Rationale:
The initial failures were useful signals, but they did not fully protect the new behavior. Additional coverage was added for item flag mapping, non-returnable rule cases, category windows, the authorization exploit path, the HTMX filter path, the restored return flow, and lookup throttling. That gives the implementation a more trustworthy safety net than simply making the original tests pass.

Alternatives considered:
Fixing only the broken tests already present. That would have left the most important newly added behavior under-tested.


Decision:
Did not attempt to complete every backlog item.

Rationale:
The stronger submission was the one that established correct core behavior, closed the obvious security gap, restored the main customer journey, and used the remaining room for a scoped operational improvement. That produces a better signal on prioritization and engineering judgment than a broader but thinner pass across the backlog.

Alternatives considered:
Pursuing maximum feature count. That would likely have traded away depth, test quality, and decision clarity.
