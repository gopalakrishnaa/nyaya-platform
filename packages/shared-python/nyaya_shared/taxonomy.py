"""Event type taxonomy, category mappings, benchmarks, and stage definitions for Nyaya case events."""

# ── Valid event types ────────────────────────────────────────────────────────
VALID_EVENT_TYPES: set[str] = {
    # FIR
    "FIR_REGISTERED",
    "FIR_REJECTED",
    "FIR_TRANSFERRED",
    # Medical
    "MEDICAL_EXAMINATION",
    "MEDICAL_REPORT_FILED",
    "FORENSIC_REPORT",
    # Arrest / Custody
    "ARREST_MADE",
    "ACCUSED_SURRENDERED",
    "ACCUSED_ABSCONDING",
    # Bail
    "BAIL_APPLIED",
    "BAIL_GRANTED",
    "BAIL_REJECTED",
    "BAIL_CANCELLED",
    "ANTICIPATORY_BAIL_APPLIED",
    "ANTICIPATORY_BAIL_GRANTED",
    "ANTICIPATORY_BAIL_REJECTED",
    # Remand
    "REMAND_GRANTED",
    "REMAND_EXTENDED",
    # Chargesheet
    "CHARGESHEET_FILED",
    "CHARGESHEET_INCOMPLETE",
    "SUPPLEMENTARY_CHARGESHEET",
    # Charges
    "CHARGES_FRAMED",
    "CHARGES_MODIFIED",
    "DISCHARGE_PETITION_FILED",
    "DISCHARGE_REJECTED",
    # Trial
    "TRIAL_COMMENCED",
    "WITNESS_EXAMINATION",
    "CROSS_EXAMINATION",
    "ARGUMENT_HEARD",
    "JUDGMENT_RESERVED",
    "JUDGMENT_DELIVERED",
    # Outcome
    "CONVICTION",
    "ACQUITTAL",
    "PARTIAL_CONVICTION",
    "SENTENCE_PRONOUNCED",
    "SENTENCE_ENHANCED",
    "SENTENCE_REDUCED",
    "COMPENSATION_ORDERED",
    "COMPENSATION_PAID",
    # Appeals
    "HIGH_COURT_APPEAL_FILED",
    "HIGH_COURT_APPEAL_ADMITTED",
    "HIGH_COURT_JUDGMENT",
    "SUPREME_COURT_APPEAL_FILED",
    "SUPREME_COURT_JUDGMENT",
    # Transfers
    "CASE_TRANSFERRED_FTSC",
    "CASE_TRANSFERRED_HC",
    "CASE_TRANSFERRED_SESSIONS",
    # Witness
    "VICTIM_HOSTILE",
    "KEY_WITNESS_HOSTILE",
    # Complaints / RTI
    "RTI_FILED",
    "RTI_RESPONSE",
    "NHRC_COMPLAINT",
    "NCW_COMPLAINT",
    # Administrative
    "SUSPENSION_OF_ACCUSED_OFFICER",
    "DEPARTMENTAL_ACTION",
    # Media
    "MEDIA_REPORT",
}

# ── Category groupings ────────────────────────────────────────────────────────
EVENT_CATEGORY_MAP: dict[str, str] = {
    # FIR
    "FIR_REGISTERED": "FIR",
    "FIR_REJECTED": "FIR",
    "FIR_TRANSFERRED": "FIR",
    # Medical
    "MEDICAL_EXAMINATION": "MEDICAL",
    "MEDICAL_REPORT_FILED": "MEDICAL",
    "FORENSIC_REPORT": "MEDICAL",
    # Arrest
    "ARREST_MADE": "ARREST",
    "ACCUSED_SURRENDERED": "ARREST",
    "ACCUSED_ABSCONDING": "ARREST",
    # Bail
    "BAIL_APPLIED": "BAIL",
    "BAIL_GRANTED": "BAIL",
    "BAIL_REJECTED": "BAIL",
    "BAIL_CANCELLED": "BAIL",
    "ANTICIPATORY_BAIL_APPLIED": "BAIL",
    "ANTICIPATORY_BAIL_GRANTED": "BAIL",
    "ANTICIPATORY_BAIL_REJECTED": "BAIL",
    # Remand
    "REMAND_GRANTED": "REMAND",
    "REMAND_EXTENDED": "REMAND",
    # Chargesheet
    "CHARGESHEET_FILED": "CHARGESHEET",
    "CHARGESHEET_INCOMPLETE": "CHARGESHEET",
    "SUPPLEMENTARY_CHARGESHEET": "CHARGESHEET",
    # Charges
    "CHARGES_FRAMED": "CHARGES",
    "CHARGES_MODIFIED": "CHARGES",
    "DISCHARGE_PETITION_FILED": "CHARGES",
    "DISCHARGE_REJECTED": "CHARGES",
    # Trial
    "TRIAL_COMMENCED": "TRIAL",
    "WITNESS_EXAMINATION": "TRIAL",
    "CROSS_EXAMINATION": "TRIAL",
    "ARGUMENT_HEARD": "TRIAL",
    "JUDGMENT_RESERVED": "TRIAL",
    "JUDGMENT_DELIVERED": "TRIAL",
    # Outcome
    "CONVICTION": "OUTCOME",
    "ACQUITTAL": "OUTCOME",
    "PARTIAL_CONVICTION": "OUTCOME",
    "SENTENCE_PRONOUNCED": "OUTCOME",
    "SENTENCE_ENHANCED": "OUTCOME",
    "SENTENCE_REDUCED": "OUTCOME",
    "COMPENSATION_ORDERED": "OUTCOME",
    "COMPENSATION_PAID": "OUTCOME",
    # Appeals
    "HIGH_COURT_APPEAL_FILED": "APPEAL",
    "HIGH_COURT_APPEAL_ADMITTED": "APPEAL",
    "HIGH_COURT_JUDGMENT": "APPEAL",
    "SUPREME_COURT_APPEAL_FILED": "APPEAL",
    "SUPREME_COURT_JUDGMENT": "APPEAL",
    # Transfers
    "CASE_TRANSFERRED_FTSC": "TRANSFER",
    "CASE_TRANSFERRED_HC": "TRANSFER",
    "CASE_TRANSFERRED_SESSIONS": "TRANSFER",
    # Witness
    "VICTIM_HOSTILE": "WITNESS",
    "KEY_WITNESS_HOSTILE": "WITNESS",
    # Complaints
    "RTI_FILED": "COMPLAINT",
    "RTI_RESPONSE": "COMPLAINT",
    "NHRC_COMPLAINT": "COMPLAINT",
    "NCW_COMPLAINT": "COMPLAINT",
    # Administrative
    "SUSPENSION_OF_ACCUSED_OFFICER": "ADMINISTRATIVE",
    "DEPARTMENTAL_ACTION": "ADMINISTRATIVE",
    # Media
    "MEDIA_REPORT": "MEDIA",
}

# ── Stage definitions — event types that belong to each pipeline stage ────────
STAGE_DEFINITIONS: dict[str, set[str]] = {
    "FIR": {
        "FIR_REGISTERED",
        "FIR_REJECTED",
        "FIR_TRANSFERRED",
    },
    "INVESTIGATION": {
        "MEDICAL_EXAMINATION",
        "MEDICAL_REPORT_FILED",
        "FORENSIC_REPORT",
        "ARREST_MADE",
        "ACCUSED_SURRENDERED",
        "ACCUSED_ABSCONDING",
        "REMAND_GRANTED",
        "REMAND_EXTENDED",
        "BAIL_APPLIED",
        "BAIL_GRANTED",
        "BAIL_REJECTED",
        "BAIL_CANCELLED",
        "ANTICIPATORY_BAIL_APPLIED",
        "ANTICIPATORY_BAIL_GRANTED",
        "ANTICIPATORY_BAIL_REJECTED",
    },
    "CHARGESHEET": {
        "CHARGESHEET_FILED",
        "CHARGESHEET_INCOMPLETE",
        "SUPPLEMENTARY_CHARGESHEET",
    },
    "TRIAL": {
        "CHARGES_FRAMED",
        "CHARGES_MODIFIED",
        "DISCHARGE_PETITION_FILED",
        "DISCHARGE_REJECTED",
        "TRIAL_COMMENCED",
        "WITNESS_EXAMINATION",
        "CROSS_EXAMINATION",
        "ARGUMENT_HEARD",
        "JUDGMENT_RESERVED",
        "CASE_TRANSFERRED_FTSC",
        "CASE_TRANSFERRED_SESSIONS",
        "VICTIM_HOSTILE",
        "KEY_WITNESS_HOSTILE",
    },
    "JUDGMENT": {
        "JUDGMENT_DELIVERED",
        "CONVICTION",
        "ACQUITTAL",
        "PARTIAL_CONVICTION",
        "SENTENCE_PRONOUNCED",
        "SENTENCE_ENHANCED",
        "SENTENCE_REDUCED",
        "COMPENSATION_ORDERED",
        "COMPENSATION_PAID",
    },
    "APPEAL": {
        "HIGH_COURT_APPEAL_FILED",
        "HIGH_COURT_APPEAL_ADMITTED",
        "HIGH_COURT_JUDGMENT",
        "CASE_TRANSFERRED_HC",
        "SUPREME_COURT_APPEAL_FILED",
        "SUPREME_COURT_JUDGMENT",
    },
    "CLOSURE": {
        "RTI_FILED",
        "RTI_RESPONSE",
        "NHRC_COMPLAINT",
        "NCW_COMPLAINT",
        "SUSPENSION_OF_ACCUSED_OFFICER",
        "DEPARTMENTAL_ACTION",
        "MEDIA_REPORT",
    },
}

# ── Benchmarks — legal/policy time limits in days ─────────────────────────────
# legal_ref: statute or government order establishing the benchmark
BENCHMARKS: dict[str, dict] = {
    # CrPC Sec 167 — 60 days for POCSO offences (Sec 36A POCSO Act)
    "FIR_TO_CHARGESHEET_POCSO": {
        "days": 60,
        "legal_ref": "POCSO Act Sec 35 / CrPC Sec 167",
    },
    # Standard chargesheet deadline (non-POCSO) — 90 days for offences > 3 years
    "FIR_TO_CHARGESHEET_OTHER": {
        "days": 90,
        "legal_ref": "CrPC Sec 167(2)(a)(i)",
    },
    # Medical examination within 24 hours of FIR — MHA advisory 2014
    "FIR_TO_MEDICAL": {
        "days": 1,
        "legal_ref": "MHA Advisory 09.06.2014",
    },
    # Arrest should follow FIR — no hard limit; 7-day benchmark used here
    "FIR_TO_ARREST": {
        "days": 7,
        "legal_ref": "CrPC Sec 41",
    },
    # Charges framed within 60 days of chargesheet — CrPC Sec 228
    "CHARGESHEET_TO_CHARGES_FRAMED": {
        "days": 60,
        "legal_ref": "CrPC Sec 228",
    },
    # Trial to commence within 30 days of charges framed — Nirbhaya guidelines
    "CHARGES_FRAMED_TO_TRIAL": {
        "days": 30,
        "legal_ref": "MHA SOP 2019 / SC guidelines",
    },
    # FTSC must complete trial within 1 year — FTSC scheme guidelines
    "TRIAL_TO_JUDGMENT_FTSC": {
        "days": 365,
        "legal_ref": "Fast Track Special Courts Scheme 2019",
    },
    # HC appeal judgment within 6 months — Sec 374 CrPC / POCSO Sec 36B
    "CONVICTION_TO_APPEAL": {
        "days": 180,
        "legal_ref": "POCSO Act Sec 36B / CrPC Sec 374",
    },
}
