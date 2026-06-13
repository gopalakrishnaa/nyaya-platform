# RTI Assistant

## Problem Statement

Right-to-Information (RTI) requests are one of the most powerful tools to
unlock stalled cases — court records, charge sheets, investigation diaries —
but drafting a legally correct RTI letter is hard for non-lawyers. The RTI
Assistant generates a ready-to-submit RTI letter tailored to the specific
missing document, the correct authority, and the applicable legal provisions.

## Architecture

```
Trigger: admin clicks "Draft RTI" on case detail page
  OR: AnomalyDetectionAgent flags a stalled case
        │
        ▼
 RTIContextBuilder
        │  reads: case status, missing events, state, district,
        │         ipc_sections, court_name, investigating_agency
        ▼
 AuthorityResolver
        │  Maps: stage → authority
        │   UNDER_INVESTIGATION → Superintendent of Police (SP)
        │   CHARGESHEET_FILED  → Public Prosecutor + Court Registrar
        │   TRIAL_IN_PROGRESS  → District & Sessions Court Registrar
        │   FAST_TRACK          → National Mission for Safety of Women helpdesk
        │
        ▼
 ClaudeDrafter (claude-3-5-sonnet — quality matters here)
        │  system: "You are an expert RTI practitioner in India..."
        │  generates: full RTI letter, postal address, fee note, deadline
        ▼
 RTIDocument
        │  Stored in rti_requests table
        │  Rendered as PDF via WeasyPrint
        ▼
 Download (PDF) + Copy (Markdown) available on case page
```

## How It Works

1. **Identify gap**: What document is missing? Derived from case stage:
   - No FIR copy in events → request FIR + GD entry from police station
   - No chargesheet after 60/90 days → request case diary from SP
   - No trial date set → request cause list from court registrar
   - No judgment after hearing → request judgment copy from court

2. **Resolve authority**: State-specific PIO (Public Information Officer)
   hierarchy. Hard-coded mapping updated quarterly. Fallback: State Home Dept.

3. **Draft with Claude**: Structured prompt includes:
   - Case facts (sanitised — no victim name, case_ref used)
   - Missing document
   - Target authority + address
   - Relevant RTI sections (Sec 6, Sec 7, Sec 19 for appeals)
   - User's name / organisation (from profile or left as `[APPLICANT NAME]`)

4. **Validate**: Claude self-checks that it has included: authority name,
   PIO address, specific document requested, 30-day deadline citation, fee
   note (₹10 IPO), and appeal provision.

5. **Output**: Markdown letter + PDF. User downloads and posts / emails.

## Tech Stack

| Component | Library / Service |
|-----------|------------------|
| LLM | `claude-3-5-sonnet-20241022` (higher quality for legal text) |
| PDF | WeasyPrint 62 |
| API | FastAPI |
| DB | PostgreSQL 15 |
| Authority data | Static JSON file (`rti_authorities.json`) |

## Configuration

```env
DATABASE_URL=postgresql://user:pass@host:5432/prajna
ANTHROPIC_API_KEY=sk-ant-...
RTI_PDF_LOGO_PATH=/assets/prajna-logo.png
RTI_DEFAULT_APPLICANT=Prajna Platform (Public Interest)
RTI_AUTHORITY_MAP_PATH=/etc/prajna/rti_authorities.json
```

## Example Output

```json
{
  "case_ref": "PRJ-LIVE-MP-2026-TWISHA",
  "document_requested": "Case diary and CBI investigation status report",
  "authority": {
    "name": "Public Information Officer",
    "designation": "Superintendent of Police, Jabalpur",
    "address": "SP Office, Civil Lines, Jabalpur, Madhya Pradesh 482001",
    "state": "Madhya Pradesh"
  },
  "letter_markdown": "**To**\nThe Public Information Officer\nSuperintendent of Police, Jabalpur\nCivil Lines, Jabalpur, Madhya Pradesh – 482001\n\n**Date:** 13 June 2026\n\n**Subject: Application under Section 6 of the Right to Information Act, 2005**\n\nSir/Madam,\n\nI, the undersigned, hereby request the following information under Section 6(1) of the RTI Act, 2005...",
  "fee_note": "Enclose ₹10 as Indian Postal Order (IPO) or court fee stamp payable to 'Accounts Officer, SP Jabalpur'.",
  "statutory_deadline": "30 days from date of receipt (Section 7(1), RTI Act 2005)",
  "appeal_note": "If no response within 30 days, file first appeal to the Appellate Authority under Section 19(1).",
  "pdf_url": "/api/v1/rti/sub-9a2f3c/download.pdf",
  "generated_at": "2026-06-13T10:00:00Z",
  "model": "claude-3-5-sonnet-20241022"
}
```

## PostgreSQL Schema

```sql
CREATE TABLE rti_requests (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id         TEXT NOT NULL REFERENCES live_cases(id),
    case_ref        TEXT NOT NULL,
    document_type   TEXT NOT NULL,
    authority_name  TEXT NOT NULL,
    authority_addr  TEXT NOT NULL,
    letter_md       TEXT NOT NULL,
    letter_pdf_path TEXT,
    status          TEXT NOT NULL DEFAULT 'DRAFTED',
    -- DRAFTED | SUBMITTED | RESPONSE_RECEIVED | APPEALED | CLOSED
    submitted_at    TIMESTAMPTZ,
    response_at     TIMESTAMPTZ,
    outcome_notes   TEXT,
    model           TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by      TEXT
);

CREATE INDEX idx_rti_requests_case ON rti_requests (case_id);
CREATE INDEX idx_rti_requests_status ON rti_requests (status);
```

## Cost Estimation

| Item | Volume | Unit cost | Monthly |
|------|--------|-----------|---------|
| Claude sonnet (draft) | ~50 RTIs/month × 3k tok avg | $0.003/1k | ~$0.45 |
| PDF generation | 50 × WeasyPrint | Compute-only | ~$0 |
| **Total** | | | **~$0.45/month** |
