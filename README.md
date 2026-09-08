# Vendor Risk Assessment Automation for Government Contracts

Scores vendors bidding on a government contract using three independent,
auditable inputs — disclosed breach history, verified certification status,
and passive technical hygiene on the vendor's public domain — then rolls
them into one transparent composite score with a per-category breakdown and
a plain-language recommendation for contract conditions.

It replaces the first pass of manual procurement security review: a
reviewer currently reads a vendor's self-attested questionnaire, eyeballs
whether a claimed ISO 27001 certificate "looks right," and maybe checks
if the vendor's name shows up in the news for a breach. That's slow and
inconsistent between reviewers. This tool does the same triage in seconds,
against the same evidence every time, and shows its work — the contracting
officer still makes the final call, but starts from a comparable,
defensible baseline instead of three unstructured PDFs.

## Quickstart

```bash
pip install -r requirements.txt

# Option A: CLI demo — loads 3 sample vendors bidding on the same contract
# and runs the whole pipeline end to end, no browser needed
python cli.py demo --reset

# Option B: web UI
python app.py
# then open http://localhost:5000
```

The CLI demo prints a side-by-side comparison table, explains why the
leading vendor ranks first, and writes a one-page PDF report per vendor to
`outputs/`. Run it twice in a row (or with `--reset` to start clean) — it
does not depend on any external service and does not crash on a
re-run.

Run the tests:

```bash
python -m pytest tests/ -q
```

## Project layout

```
cli.py                     command-line entry point (demo / add-vendor / assess / reset)
app.py                     Flask web UI (intake form, comparison table, PDF download)
vendor_risk/
  models.py                vendor intake record + questionnaire schema
  breach_history.py        scoring input 1: disclosed breach history
  certifications.py        scoring input 2: certification validity vs. registry
  passive_checks.py        scoring input 3: TLS / headers / DNS / exposed services
  scoring.py                composite scoring engine, weights, risk bands
  report.py                findings -> recommended contract conditions -> PDF
  store.py                 tiny JSON-file persistence layer
data/
  breach_dataset.json       mock breach-intelligence feed
  cert_registry.json        mock certification-body registry
  vendors_store.json        created at runtime — vendor intake records
templates/, static/         Flask UI
tests/test_scoring.py       unit tests for the scoring engine
```

## Scoring methodology

Every score is 0–100, higher is better, and every score returns the raw
evidence it was computed from — nothing is a black-box number.

| Category | Weight | What it checks |
|---|---|---|
| Breach history | 30% | Disclosed incidents from a breach-intelligence feed. Penalty is severity-weighted and recency-decayed: a high-severity breach 6 months ago costs more than one 6 years ago, but old incidents are never fully forgiven (penalty floors at 35% of its original weight). |
| Certifications | 30% | Claimed certifications (ISO 27001, SOC 2, UAE IA, PCI DSS) checked against a registry lookup, not taken on faith. A claimed-but-unverifiable or claimed-but-expired certification is flagged as a **misrepresentation**, which is treated as more serious than simply lacking the certification. |
| Technical hygiene | 40% | Four passive, externally-observable sub-checks, weighted 30/25/25/20: **TLS** (protocol version, certificate validity/expiry), **security headers** (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy), **DNS hygiene** (SPF present, DMARC present and enforced — missing anti-spoofing records is a classic email-phishing pivot into a buyer's org), **exposed services** (short-timeout TCP probe for internet-facing admin/database ports that should never be public: SSH, RDP, MySQL, Postgres, Redis, Elasticsearch, Telnet, FTP). This category carries the highest weight because it's the one input a vendor cannot spin in a questionnaire — it's what's actually running today. |

Weights are configurable (`vendor_risk/scoring.py::DEFAULT_WEIGHTS`,
`TECH_SUB_WEIGHTS`) and must sum to 1.0; a bad weight configuration fails
loudly rather than silently producing a wrong score.

Composite score maps to a risk band: **LOW RISK** (≥80), **MODERATE RISK**
(≥60), **ELEVATED RISK** (≥40), **HIGH RISK** (<40).

### From score to action: recommended contract conditions

A number alone isn't a procurement decision. `vendor_risk/report.py`
maps specific findings to concrete clauses a contracting officer could
attach to an award — e.g. a shortened breach-notification window if the
vendor has prior incidents, mandatory ISO 27001 attainment within 6 months
if certification coverage is weak, or a required remediation-and-rescan
cycle if sensitive ports are internet-facing. This is what turns "62/100"
into something a procurement team can actually act on.

## Why this approach, not the one from three years ago

Three years ago this problem was usually "send the vendor a spreadsheet
questionnaire and trust it." The shift here is treating the questionnaire
as the *least* trustworthy input, not the primary one: certifications are
verified against a registry instead of taken as claimed, and the
highest-weighted category (technical hygiene) is entirely external and
non-self-reported — closer to how attack-surface-management tools
(Shodan/Censys-style passive reconnaissance, SecurityScorecard/BitSight-style
continuous vendor ratings) already operate in commercial third-party risk
programs, but scoped down to something a small procurement team can run
themselves without a paid feed.

## Ethics and legal note on the passive checks

Every check in `passive_checks.py` reads information a vendor already
exposes publicly — TLS handshake, HTTP response headers, DNS records —
except the exposed-services check, which does a short-timeout TCP connect
probe against a handful of well-known ports. That's read-only and
non-intrusive (no exploitation, no authentication bypass, equivalent to
what internet-wide scanners like Shodan already publish), but it should
only ever be pointed at a domain the assessor has a legitimate procurement
relationship with — never used for general internet scanning.

## Data sources in this prototype

`data/breach_dataset.json` and `data/cert_registry.json` are mock datasets
standing in for real feeds. Swapping them for the real thing is an
interface-level change only — `breach_history.get_breaches()` and
`certifications._load_registry()` are the two functions that would call
out to a licensed breach-intelligence API (e.g. HaveIBeenPwned's enterprise
API) and the actual issuing-body registries (IAF CertSearch for ISO 27001,
AICPA for SOC 2, UAE TDRA for UAE IA) respectively — the scoring logic
downstream is agnostic to where the records came from.

## Limitations

- Breach and certification data are mock datasets for the demo (see
  above) — the three sample vendor domains are fictional and won't
  resolve on the public internet.
- The exposed-services check only probes a fixed list of common sensitive
  ports, not a full port sweep, to stay fast and unambiguously passive.
- This is a triage layer, not a replacement for manual due diligence on
  vendors that score in the ELEVATED/HIGH bands or trigger a
  misrepresentation flag.

## Demo script (matches the "what the demo should show" requirement)

1. `python cli.py demo --reset` — loads GlobalLogix, Brightfield Solutions,
   and VantagePoint IT onto contract `GOV-2026-014` and scores all three.
2. The printed table shows VantagePoint IT ranking first (verified
   certifications, clean breach record) despite GlobalLogix and
   Brightfield having no *disclosed* incidents recently — because
   GlobalLogix's claimed ISO 27001 certificate has actually expired
   (a misrepresentation the questionnaire alone wouldn't catch).
3. Open any of the three generated PDFs in `outputs/` for the one-page
   report and recommended contract conditions, or run `python app.py` for
   the same flow with an interactive intake form and side-by-side table.

ALL WE HAVE TO DO IS BASICALLY HAVE A UX/UI AND HAVE BASIC FUNCTIONALTIY
