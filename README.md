# Vendi — Vendor Cyber Risk Intelligence

A single self-contained HTML file (`Vendi.html`) that prototypes a tool for scoring vendors bidding on a government contract by security posture, comparing them side by side, and translating each score into concrete contract conditions.

There is nothing to install and nothing to build. Open `Vendi.html` in any modern browser and the whole app runs client-side — HTML, CSS and JavaScript in one file, no server, no dependencies beyond one Google Fonts request (the app still works offline; it just falls back to system fonts).

---

## 1. What it does

Vendi walks a reviewer through three steps:

1. **Vendor intake** — add exactly three competing vendors (by name, domain, claimed certifications and optional questionnaire notes), or load a ready-made demo set.
2. **Comparison dashboard** — once three vendors are in, run the assessment and see a composite risk score per vendor, a leader call-out, a category breakdown (breach history / certifications / technical hygiene), and a plain-language "contract risk translator" for each vendor.
3. **Vendor report** — a printable, one-vendor-at-a-time report: executive summary, strengths, key risks, detailed breach/certification/technical findings, the remediation simulator (see below), and recommended contract conditions.

All three views share one left-hand navigation rail. The report view has a **Print / export** button that uses the browser's native print dialog (styled via `@media print` so the rail and tabs disappear and only the report body is printed).

## 2. The scoring model

Every vendor is scored on three categories, weighted into one composite number:

| Category | Weight | What it represents |
|---|---|---|
| Breach history | 30% | Whether the vendor has disclosed security incidents, and how severe |
| Certifications | 30% | Verification status of ISO 27001 / SOC 2 Type II / UAE IA — valid, expired, unverified, or missing |
| Technical hygiene | 40% | TLS configuration, security headers, DNS hygiene (SPF/DKIM/DMARC), and exposed services |

The composite score maps to a risk band: **Low** (≥80), **Medium** (60–79), **High** (<60). The weights live in one place in the code (`const WEIGHTS = { breach: 0.30, cert: 0.30, tech: 0.40 }`) so they're easy to re-tune.

**All findings are synthetic demo data.** There are four fictional vendors in `DEMO_LIBRARY` with hand-written breach/certification/technical-hygiene records standing in for what would, in a real deployment, come from breach-disclosure databases, certification-registry lookups, and live passive scans of the vendor's domain. Every "(Simulated check)" label in the UI is a deliberate, visible flag of this — the prototype is upfront about what's real interaction design versus placeholder data.

## 3. The contract risk translator

Scores alone don't tell a procurement officer what to *do*. The translator (`translate()`) takes a vendor's computed profile and produces:
- a plain-language summary of what the finding pattern means, and
- a list of recommended contract conditions (notification windows, audit rights, re-assessment cadence, penetration-testing requirements, etc.).

It deliberately avoids a binary accept/reject framing. A vendor with a disclosed breach but otherwise strong certifications isn't auto-rejected — it gets tightened conditions that target the specific gap the breach revealed. A vendor in the high-risk band gets the strictest available controls, but the logic is graduated across four scenarios rather than a single cutoff.

## 4. The innovation: remediation impact simulator

This is the one genuinely new piece of decision support Vendi adds beyond "score it and report it."

On each vendor's report, every certification that isn't `valid` and every technical check that isn't `pass` appears as a checkbox: *"Resolve ISO 27001 — currently expired"*, *"Fix Security headers — currently warn"*, and so on. Ticking any of them **recomputes the composite score live** and shows a before/after comparison — current score and risk band next to a projected score and risk band — with a one-line summary of the point swing.

Why this matters for the brief: static risk reports tend to force a binary decision at the moment of assessment. The simulator reframes the score as something a vendor can move, and lets a reviewer see *how far* a specific, named fix would go before deciding whether to reject outright, award with conditions, or give the vendor a remediation window. It turns the tool from a snapshot into a planning aid, without touching the underlying assessment data — breach history is deliberately excluded from the simulator, since a disclosed incident can't be un-happened; only certifications and technical hygiene, which a vendor can actually go and fix, are simulated.

The simulator uses a transparent heuristic (fixing a `fail` check recovers 16 points toward the technical-hygiene score, a `warn` check recovers 8, capped at 100; a remediated certification counts as `valid`/100), clearly labelled in the UI as "simulated scoring for planning purposes only." It is not a claim of precision — it's a way to make the trade-offs the translator already reasons about visible and interactive.

## 5. Design choices

The visual language is closer to a formal audit exhibit than a consumer dashboard, on purpose — this is a document that ends up being printed and attached to a procurement file, so it borrows the conventions of one: a warm paper background, a serif typeface for headings and scores (Source Serif 4) against a plain sans-serif for body and UI text (IBM Plex Sans), hairline rules instead of card shadows, and numbered exhibit labels ("Exhibit A/B/C") on the dashboard sections it makes sense for, since those sections *are* a sequence of exhibits.

The colour system was shifted from the original navy/blue-grey to a deep teal (`#256B67`) as the single accent colour, against a softer, warmer paper background and pure-white raised cards for better contrast on badges, buttons and table rows. Risk-band colours (green / amber / red) were kept semantically standard on purpose — inventing a new colour language for "this vendor is high-risk" would work against the reader, not for them. Base type size and line-height were both nudged up slightly, borders were softened, and hover/active states were made more visible, aimed at making longer reading sessions (a reviewer working through three full vendor reports) less fatiguing.

## 6. Code structure

Everything lives in `Vendi.html`. Reading order, top to bottom:

- **`<style>`** — CSS variables (`:root`) define the whole palette in one place; component styles follow, grouped by view (rail, intake, loading, dashboard, report, simulator), with a print stylesheet and a mobile breakpoint at the bottom.
- **`WEIGHTS`, `riskLevel()`, `riskColorVar()`** — the scoring constants and small helpers used everywhere.
- **`DEMO_LIBRARY`** — the four synthetic demo vendors, each with claimed certifications, a questionnaire, breach history, certification records, and technical-hygiene checks.
- **`computeVendor(v)`** — derives a certification score and composite score for a raw vendor object.
- **`computeVendorSimulated(v, sim)`** — the remediation simulator's parallel scoring function, described above.
- **`translate(v)`** — the contract risk translator.
- **`state`** — the single mutable object holding which view is active, which vendors have been added, which vendor's report is open, and the simulator's per-vendor checkbox selections.
- **`render()`** — clears `#app` and rebuilds it from `state`. There is no virtual DOM or diffing; every state change calls `render()` and the whole app tree is rebuilt from scratch. This keeps the code simple at the scale of a three-vendor prototype.
- **`Rail()`, `IntakeView()`, `LoadingView()` / `runAssessment()`, `DashboardView()`, `ReportView()`, `RemediationSimulator()`** — one function per view/section, each returning a DOM node that `render()` attaches to `<main>`.
- **`el(tag, attrs)`** — a small `document.createElement` convenience wrapper used throughout instead of a templating library.

There's no build step, no bundler, and no external JS dependency — only the Google Fonts stylesheet link in `<head>`, which the app doesn't require to function.

## 7. Known limitations (prototype scope)

- Breach history, certification verification, and technical-hygiene checks are all hand-authored demo data, not live lookups. A production version would need integrations with a breach-disclosure feed, certification-registry APIs, and an actual passive domain scanner (TLS, headers, DNS records, exposed-port checks).
- The manual "Add a vendor" form seeds a new vendor's assessment data from a random demo profile so the flow stays fully interactive end to end — it's a stand-in for the real intake-and-assessment pipeline, not a real assessment.
- The remediation simulator's point values are an illustrative heuristic, not a validated scoring model — flagged as such in the UI.
- State lives only in memory; refreshing the page resets everything to the empty intake screen.

## 8. Running it

Just open `Vendi.html` in a browser. No server, no `npm install`, no build. To print or export a report, open that vendor's report and use the **Print / export** button (or your browser's own print shortcut) — the print stylesheet hides the navigation and tabs automatically.
