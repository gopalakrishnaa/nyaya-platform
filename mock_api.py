"""Lightweight mock API — serves realistic seed data without any DB/Kafka/Redis."""
from __future__ import annotations

import random
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Nyaya Mock API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

STATES = ["Maharashtra", "Uttar Pradesh", "Rajasthan", "Delhi", "West Bengal",
          "Karnataka", "Tamil Nadu", "Madhya Pradesh", "Bihar", "Andhra Pradesh"]

DISTRICTS = {
    "Maharashtra": ["Mumbai", "Pune", "Nagpur", "Thane", "Nashik"],
    "Uttar Pradesh": ["Lucknow", "Kanpur", "Agra", "Varanasi", "Prayagraj"],
    "Rajasthan": ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer"],
    "Delhi": ["New Delhi", "East Delhi", "North Delhi", "South Delhi", "West Delhi"],
    "West Bengal": ["Kolkata", "Howrah", "Durgapur", "Asansol", "Siliguri"],
    "Karnataka": ["Bengaluru", "Mysuru", "Mangaluru", "Hubli", "Belagavi"],
    "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem"],
    "Madhya Pradesh": ["Bhopal", "Indore", "Gwalior", "Jabalpur", "Ujjain"],
    "Bihar": ["Patna", "Gaya", "Muzaffarpur", "Bhagalpur", "Darbhanga"],
    "Andhra Pradesh": ["Visakhapatnam", "Vijayawada", "Guntur", "Nellore", "Kurnool"],
}

CATEGORIES = ["RAPE", "SEXUAL_ASSAULT", "DOMESTIC_VIOLENCE", "POCSO_VIOLATION",
               "ACID_ATTACK", "DOWRY_DEATH", "STALKING", "TRAFFICKING", "GANG_RAPE"]

STATUSES = ["REPORTED", "UNDER_INVESTIGATION", "CHARGESHEET_FILED",
            "TRIAL_IN_PROGRESS", "JUDGMENT_DELIVERED", "CLOSED_CONVICTED", "CLOSED_ACQUITTED"]

EVENT_TYPES = ["FIR_REGISTERED", "ARREST_MADE", "CHARGESHEET_FILED", "BAIL_DENIED",
               "TRIAL_COMMENCED", "WITNESS_EXAMINED", "JUDGMENT_DELIVERED", "CONVICTION",
               "MEDICAL_EXAMINATION", "FAST_TRACK_COURT_ASSIGNED"]


def make_case(idx: int) -> dict:
    random.seed(idx)
    state = random.choice(STATES)
    district = random.choice(DISTRICTS[state])
    category = random.choice(CATEGORIES)
    status = random.choice(STATUSES)
    year = random.randint(2021, 2026)
    max_month = 5 if year == 2026 else 12
    month = random.randint(1, max_month)
    max_day = 10 if year == 2026 and month == 5 else 28
    day = random.randint(1, max_day)
    state_code = state[:2].upper()
    pocso = category == "POCSO_VIOLATION" or random.random() < 0.15
    fast_track = random.random() < 0.3
    convicted = status == "CLOSED_CONVICTED"

    return {
        "id": f"case-{idx:06d}",
        "case_ref": f"NYA-{year}-{state_code}-{idx:06d}",
        "victim_pseudonym": f"VICTIM-{idx:06x}",
        "crime_category": category,
        "status": status,
        "incident_date": f"{year}-{month:02d}-{day:02d}",
        "incident_date_approx": random.random() < 0.2,
        "state": state,
        "district": district,
        "ipc_sections": random.sample([375, 376, 354, 498, 302, 304, 307], k=random.randint(1, 3)),
        "pocso_applicable": pocso,
        "fast_track_court": fast_track,
        "num_victims": random.randint(1, 3),
        "event_count": random.randint(2, 12),
        "last_event_at": (datetime(year, month, day) + timedelta(days=random.randint(30, 900))).isoformat(),
        "overall_confidence": round(random.uniform(0.72, 0.99), 2),
        "conviction_achieved": convicted,
        "created_at": f"{year}-{month:02d}-{day:02d}T00:00:00",
        "updated_at": f"{year}-{month:02d}-{day:02d}T00:00:00",
    }


def make_events(case: dict) -> list[dict]:
    events = []
    base = datetime.fromisoformat(case["incident_date"])
    for i, etype in enumerate(random.sample(EVENT_TYPES, k=min(6, len(EVENT_TYPES)))):
        d = base + timedelta(days=i * random.randint(10, 60))
        events.append({
            "id": f"evt-{case['id']}-{i}",
            "event_type": etype,
            "event_category": "LEGAL",
            "event_date": d.date().isoformat(),
            "event_date_approx": False,
            "summary": f"{etype.replace('_', ' ').title()} recorded in {case['district']}, {case['state']}.",
            "court_name": f"{case['district']} Sessions Court" if "TRIAL" in etype or "JUDGMENT" in etype else None,
            "source_attribution": [{"source_code": "ANI", "source_name": "Asian News International",
                                     "published_at": d.isoformat(), "source_url": ""}],
            "source_quote": f"The {etype.lower().replace('_', ' ')} was confirmed by officials in {case['district']}.",
            "confidence_score": round(random.uniform(0.75, 0.98), 2),
            "moderation_status": "APPROVED",
            "is_milestone": etype in {"FIR_REGISTERED", "CONVICTION", "JUDGMENT_DELIVERED", "ARREST_MADE"},
        })
    return events


CASES = [make_case(i) for i in range(1, 201)]


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/v1/cases")
def list_cases(
    page: int = 1,
    page_size: int = 20,
    state: str | None = None,
    crime_category: str | None = None,
    status: str | None = None,
    pocso: bool | None = None,
    fast_track: bool | None = None,
    conviction: bool | None = None,
    year: int | None = None,
    q: str | None = None,
    sort: str | None = None,
):
    items = list(CASES)
    if state:
        items = [c for c in items if c["state"].lower() == state.lower()]
    if crime_category:
        items = [c for c in items if c["crime_category"] == crime_category]
    if status:
        items = [c for c in items if c["status"] == status]
    if pocso is True:
        items = [c for c in items if c["pocso_applicable"]]
    if fast_track is True:
        items = [c for c in items if c["fast_track_court"]]
    if conviction is True:
        items = [c for c in items if c["conviction_achieved"]]
    if year:
        items = [c for c in items if c["incident_date"].startswith(str(year))]
    if q:
        q_lower = q.lower()
        items = [c for c in items if q_lower in c["state"].lower()
                 or q_lower in c["district"].lower()
                 or q_lower in c["crime_category"].lower()]
    total = len(items)
    start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "total": total, "page": page, "page_size": page_size}


@app.get("/v1/cases/{case_id}")
def get_case(case_id: str):
    case = next((c for c in CASES if c["id"] == case_id), None)
    if not case:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Case not found")
    return {**case, "events": make_events(case)}


@app.get("/v1/stats/summary")
def stats_summary():
    convicted = sum(1 for c in CASES if c["conviction_achieved"])
    states = len(set(c["state"] for c in CASES))
    pocso = sum(1 for c in CASES if c["pocso_applicable"])
    fast_track = sum(1 for c in CASES if c["fast_track_court"])
    return {
        "total_cases": len(CASES),
        "total_convictions": convicted,
        "states_covered": states,
        "avg_conviction_rate": round(convicted / len(CASES), 3),
        "total_pocso": pocso,
        "total_fast_track": fast_track,
    }


@app.get("/v1/stats/geo")
def stats_geo():
    from collections import Counter
    state_cases: dict[str, list] = {}
    for c in CASES:
        state_cases.setdefault(c["state"], []).append(c)
    result = []
    for state, cases in state_cases.items():
        convicted = sum(1 for c in cases if c["conviction_achieved"])
        result.append({
            "state": state,
            "state_code": state[:2].upper(),
            "total_cases": len(cases),
            "conviction_rate": round(convicted / len(cases), 3),
            "avg_delay_days": round(random.uniform(120, 600), 1),
        })
    return sorted(result, key=lambda x: -x["total_cases"])


@app.get("/v1/search")
def search(q: str = "", page: int = 1, page_size: int = 20):
    return list_cases(page=page, page_size=page_size, q=q)
