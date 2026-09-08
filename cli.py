#!/usr/bin/env python3
"""Command-line interface for the Vendor Risk Assessment tool.

Usage:
    python cli.py add-vendor --contract GOV-2026-014 --name "GlobalLogix" --domain globallogix.com --certs "ISO 27001"
    python cli.py assess --contract GOV-2026-014
    python cli.py demo   # loads three sample vendors and runs the full flow
"""
import argparse
import json
import os
import sys
from vendor_risk.models import VendorIntake
from vendor_risk import store
from vendor_risk.scoring import assess_vendor
from vendor_risk.report import build_vendor_report_pdf, recommended_contract_conditions

SAMPLE_VENDORS = [
    {
        "company_name": "GlobalLogix",
        "domain": "globallogix.com",
        "claimed_certifications": ["ISO 27001", "SOC 2 Type II"],
        "questionnaire": {
            "has_incident_response_plan": True,
            "subprocessor_disclosure": False,
            "data_residency": "US-East",
            "encryption_at_rest": True,
            "breach_notification_hours": 72,
            "employee_security_training": True,
        },
    },
    {
        "company_name": "Brightfield Solutions",
        "domain": "brightfield-solutions.net",
        "claimed_certifications": ["SOC 2 Type II"],
        "questionnaire": {
            "has_incident_response_plan": True,
            "subprocessor_disclosure": True,
            "data_residency": "UAE",
            "encryption_at_rest": True,
            "breach_notification_hours": 48,
            "employee_security_training": True,
        },
    },
    {
        "company_name": "VantagePoint IT",
        "domain": "vantagepoint-it.com",
        "claimed_certifications": ["ISO 27001", "UAE IA", "SOC 2 Type II"],
        "questionnaire": {
            "has_incident_response_plan": True,
            "subprocessor_disclosure": True,
            "data_residency": "UAE",
            "encryption_at_rest": True,
            "breach_notification_hours": 24,
            "employee_security_training": True,
        },
    },
]

DEMO_CONTRACT_ID = "GOV-2026-014"


def cmd_add_vendor(args):
    vendor = VendorIntake(
        company_name=args.name,
        domain=args.domain,
        contract_id=args.contract,
        claimed_certifications=[c.strip() for c in args.certs.split(",")] if args.certs else [],
    )
    store.add_vendor(vendor)
    print(f"Added vendor {vendor.company_name} ({vendor.vendor_id}) to contract {vendor.contract_id}")


def cmd_assess(args):
    vendors = store.get_vendors_for_contract(args.contract)
    if not vendors:
        print(f"No vendors found for contract {args.contract}", file=sys.stderr)
        sys.exit(1)
    results = _assess_and_report(vendors, args.contract)
    _print_comparison(results)


def _assess_and_report(vendors, contract_id):
    results = []
    for v in vendors:
        print(f"Assessing {v.company_name} ({v.domain}) ...")
        assessment = assess_vendor(v.company_name, v.domain, v.claimed_certifications)
        out_path = f"outputs/{contract_id}_{v.vendor_id}_{assessment['company_name'].replace(' ', '_')}.pdf"
        build_vendor_report_pdf(assessment, contract_id, out_path)
        results.append((v, assessment, out_path))
    return results


def _print_comparison(results):
    results.sort(key=lambda r: r[1]["composite_score"], reverse=True)
    print("\n=== Side-by-side comparison ===")
    print(f"{'Rank':<5}{'Vendor':<24}{'Composite':<11}{'Band':<16}{'Breach':<8}{'Certs':<8}{'Tech':<8}")
    for i, (v, a, _) in enumerate(results, 1):
        cats = a["categories"]
        print(f"{i:<5}{a['company_name']:<24}{a['composite_score']:<11}{a['risk_band']:<16}"
              f"{cats['breach_history']['score']:<8}{cats['certifications']['score']:<8}"
              f"{cats['technical_hygiene']['score']:<8}")

    leader = results[0][1]
    print(f"\n{leader['company_name']} ranks first with a composite score of {leader['composite_score']}/100.")
    print("Why:")
    for c in recommended_contract_conditions(leader)[:3]:
        print(f"  - {c}")
    print("\nPDF reports written to outputs/:")
    for _, _, path in results:
        print(f"  - {path}")


def cmd_reset(args):
    if os.path.exists(store.STORE_PATH):
        os.remove(store.STORE_PATH)
    print("Vendor store cleared.")


def cmd_demo(args):
    if args.reset:
        cmd_reset(args)
    print(f"Loading {len(SAMPLE_VENDORS)} sample vendors into contract {DEMO_CONTRACT_ID} ...\n")
    for sv in SAMPLE_VENDORS:
        vendor = VendorIntake(
            company_name=sv["company_name"], domain=sv["domain"], contract_id=DEMO_CONTRACT_ID,
            claimed_certifications=sv["claimed_certifications"], questionnaire=sv["questionnaire"],
        )
        store.add_vendor(vendor)

    vendors = store.get_vendors_for_contract(DEMO_CONTRACT_ID)
    results = _assess_and_report(vendors, DEMO_CONTRACT_ID)
    _print_comparison(results)


def main():
    parser = argparse.ArgumentParser(description="Vendor Risk Assessment Automation CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add-vendor", help="Add a vendor intake record")
    p_add.add_argument("--contract", required=True)
    p_add.add_argument("--name", required=True)
    p_add.add_argument("--domain", required=True)
    p_add.add_argument("--certs", default="", help="Comma-separated claimed certifications")
    p_add.set_defaults(func=cmd_add_vendor)

    p_assess = sub.add_parser("assess", help="Assess and compare all vendors for a contract")
    p_assess.add_argument("--contract", required=True)
    p_assess.set_defaults(func=cmd_assess)

    p_demo = sub.add_parser("demo", help="Load 3 sample vendors and run the full flow end to end")
    p_demo.add_argument("--reset", action="store_true", help="Clear the vendor store first for a clean run")
    p_demo.set_defaults(func=cmd_demo)

    p_reset = sub.add_parser("reset", help="Clear all stored vendor records")
    p_reset.set_defaults(func=cmd_reset)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
