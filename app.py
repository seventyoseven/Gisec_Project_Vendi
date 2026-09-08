#!/usr/bin/env python3
"""Flask web UI for the Vendor Risk Assessment tool.

Run: python app.py
Then open http://localhost:5000
"""
import os
from flask import Flask, render_template, request, redirect, url_for, send_file, flash

from vendor_risk.models import VendorIntake, QUESTIONNAIRE_FIELDS
from vendor_risk import store
from vendor_risk.scoring import assess_vendor
from vendor_risk.report import build_vendor_report_pdf, recommended_contract_conditions

app = Flask(__name__)
app.secret_key = "dev-only-hackathon-secret"  # fine for a local demo; replace for real deployment

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "outputs")


@app.route("/")
def home():
    contracts = store.list_contracts()
    return render_template("index.html", contracts=contracts, questionnaire_fields=QUESTIONNAIRE_FIELDS)


@app.route("/vendor/add", methods=["POST"])
def add_vendor():
    contract_id = request.form.get("contract_id", "").strip() or "default"
    company_name = request.form.get("company_name", "").strip()
    domain = request.form.get("domain", "").strip()
    certs_raw = request.form.get("certifications", "")
    certs = [c.strip() for c in certs_raw.split(",") if c.strip()]

    if not company_name or not domain:
        flash("Company name and domain are required.", "error")
        return redirect(url_for("home"))

    questionnaire = {}
    for field_id, _, ftype in QUESTIONNAIRE_FIELDS:
        val = request.form.get(f"q_{field_id}")
        if ftype == "bool":
            questionnaire[field_id] = (val == "yes")
        elif ftype == "number":
            try:
                questionnaire[field_id] = float(val) if val else None
            except ValueError:
                questionnaire[field_id] = None
        else:
            questionnaire[field_id] = val or ""

    vendor = VendorIntake(
        company_name=company_name, domain=domain, contract_id=contract_id,
        claimed_certifications=certs, questionnaire=questionnaire,
    )
    store.add_vendor(vendor)
    flash(f"Added {company_name} to contract {contract_id}.", "success")
    return redirect(url_for("compare", contract_id=contract_id))


@app.route("/compare/<contract_id>")
def compare(contract_id):
    vendors = store.get_vendors_for_contract(contract_id)
    results = []
    for v in vendors:
        assessment = assess_vendor(v.company_name, v.domain, v.claimed_certifications)
        conditions = recommended_contract_conditions(assessment)
        results.append({"vendor": v, "assessment": assessment, "conditions": conditions})

    results.sort(key=lambda r: r["assessment"]["composite_score"], reverse=True)
    leader = results[0] if results else None
    return render_template("compare.html", contract_id=contract_id, results=results, leader=leader)


@app.route("/report/<contract_id>/<vendor_id>")
def download_report(contract_id, vendor_id):
    vendor = store.get_vendor(vendor_id)
    assessment = assess_vendor(vendor.company_name, vendor.domain, vendor.claimed_certifications)
    filename = f"{contract_id}_{vendor_id}_{vendor.company_name.replace(' ', '_')}.pdf"
    out_path = os.path.join(OUTPUT_DIR, filename)
    build_vendor_report_pdf(assessment, contract_id, out_path)
    return send_file(out_path, as_attachment=True, download_name=filename)


if __name__ == "__main__":
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=5000)
