#!/usr/bin/env python3
"""Refine cases_raw.json (from fetch-real-cases.py, run in same directory)
into live-cases-ingested.json (CaseDetail[] shape consumed by lib/real-cases.ts).

Usage: python3 scripts/build-cases-dataset.py src/lib/live-cases-ingested.json"""
import json, re, sys
from collections import Counter, defaultdict

cases = json.load(open('cases_raw.json'))

# ── 1. exclusions ────────────────────────────────────────────────────────────
STATIC_KEYWORDS = [
    'nirbhaya','bilkis','kathua','unnao','sengar','hathras','twisha','sister abhaya',
    'kamduni','soumya','jisha','aruna shanbaug','shakti mills','priyadarshini','jessica',
    'suryanelli','bhanwari','pallavi purkayastha','park street','kopardi','gudiya',
    'vismaya','shraddha','swathi','kunan','shahbano','shah bano','shayara','manorama',
    'soni sori','mathura case','roop kanwar','chhawla','imrana','guwahati molestation',
]
EXPLAINER = re.compile(r'^(why|how|what|when|explained|opinion|watch|video)\b', re.I)
FALSE_CASE = re.compile(r'false (rape|case|charge|complaint)|falsely accus', re.I)

# ── 2. status regrade ────────────────────────────────────────────────────────
def regrade(title):
    tl = title.lower()
    if re.search(r'acquit', tl): return ('CLOSED_ACQUITTED', False)
    if re.search(r'challenges conviction|appeal against|moves (hc|high court|sc|supreme court) against|suspends (life )?sentence|appeal (filed|admitted)', tl):
        return ('APPEALED', True)
    if re.search(r'convict\w*|sentenc\w*|death penalty|capital punishment|life (term|imprisonment)|'
                 r'\bgets? \d+[- ]?(year|yr)|(\d+[- ]?(year|yr)s?|life)[- ]?(ri|rigorous|jail|imprisonment|term)|'
                 r'awards? death|jail term|jailed for|\bri for\b', tl):
        return ('CLOSED_CONVICTED', True)
    if re.search(r'chargesheet|charge sheet', tl): return ('CHARGESHEET_FILED', False)
    if re.search(r'charges framed|frames charges', tl): return ('CHARGES_FRAMED', False)
    if re.search(r'trial|hearing|witness|verdict|court reserves', tl): return ('TRIAL_IN_PROGRESS', False)
    if re.search(r'arrest\w*|\bheld\b|nabbed|detained|custody|booked|surrender|hunt on|absconding|rescued', tl):
        return ('UNDER_INVESTIGATION', False)
    return ('REPORTED', False)

# ── 3. dedupe by distinctive tokens ──────────────────────────────────────────
STOP = set('''the a an of in for to and on with at by from over after under against as is was were
man men woman women girl boy minor teen teenager year old years yr yrs case cases court courts high supreme
sessions district police fir accused victim survivor rape raped rapes gangrape gang rapist molestation
molesting molested sexual sexually assault assaulted assaulting harassment abuse abused pocso act dowry
death penalty life term imprisonment jail jailed sentence sentenced sentences convicted convict conviction
acquitted acquittal arrest arrested arrests chargesheet trial hearing judge justice bench order orders
bail plea petition appeal news india indian city student school hospital doctor teacher officer daughter
wife husband father mother brother son family delhi mumbai kolkata chennai bengaluru hyderabad pune noida
lucknow jaipur two three four five six seven eight nine ten first second another more also says said till
gets given grants denied filed files registered probe investigation crime branch crackdown update updates
uttar pradesh madhya maharashtra bengal karnataka kerala tamil nadu rajasthan gujarat bihar haryana punjab
odisha assam telangana andhra himachal jharkhand chhattisgarh uttarakhand goa tripura manipur days months
alleged allegedly incident report reported reporting horror shocker shocking near where his her their who
that this then them into out off amid despite before during between within without woman's girl's man's
day week month time top new old big major minor'''.split())

def tokens(title):
    t = re.sub(r'\s*[-|–]\s*[A-Za-z0-9 .&\']+$', '', title)  # strip outlet
    words = re.findall(r"[a-z']+", t.lower())
    return set(w for w in words if len(w) >= 4 and w not in STOP)

RANK = {'CLOSED_CONVICTED':6,'CLOSED_ACQUITTED':5,'APPEALED':5,'CHARGES_FRAMED':4,
        'CHARGESHEET_FILED':4,'TRIAL_IN_PROGRESS':3,'UNDER_INVESTIGATION':2,'REPORTED':1}

kept, kept_toks = [], []
pool = []
for c in cases:
    t = c['title']
    tl = t.lower()
    if any(k in tl for k in STATIC_KEYWORDS): continue
    if EXPLAINER.search(t): continue
    if FALSE_CASE.search(t): continue
    if not c.get('pub_date'): continue
    # pre-2021 'Delhi gang-rape' shorthand = Nirbhaya coverage
    if re.search(r'delhi gang.?rape', tl) and c['pub_date'][:4] <= '2020': continue
    c['status'], c['conviction_achieved'] = regrade(t)
    pool.append(c)

# explicit same-case clusters: (state, regex, keep_one) — keep_one False = drop all (static overlap)
CLUSTERS = [
    ('Rajasthan', re.compile(r'asaram'), True),
    ('Gujarat', re.compile(r'asaram'), True),
    ('Madhya Pradesh', re.compile(r'asaram|narayan sai'), False),
    ('Rajasthan', re.compile(r'ajmer.*(1992|blackmail|sex (scandal|abuse))|1992.*ajmer'), False),
    ('West Bengal', re.compile(r'durgapur'), True),
    ('West Bengal', re.compile(r'law college|kasba|kolkata college'), True),
    ('West Bengal', re.compile(r'rg kar|sanjay roy|sanjoy roy|kolkata doctor'), True),
]

pool.sort(key=lambda c: -RANK.get(c['status'], 0))
cluster_seen = set()
filtered = []
for c in pool:
    tl = c['title'].lower()
    drop = False
    for i, (state, rx, keep_one) in enumerate(CLUSTERS):
        if c['state'] == state and rx.search(tl):
            if not keep_one or i in cluster_seen:
                drop = True
            cluster_seen.add(i)
            break
    if not drop: filtered.append(c)
pool = filtered
tok_freq = Counter()
for c in pool:
    tok_freq.update(tokens(c['title']))
for c in pool:
    tk = tokens(c['title'])
    rare = set(w for w in tk if tok_freq[w] <= 4)  # likely proper names
    dup = False
    for pt, pstate, prare in kept_toks:
        if pstate != c['state_code']: continue
        if len(tk & pt) >= 2 or (rare & prare):
            dup = True; break
    if dup: continue
    kept.append(c)
    kept_toks.append((tk, c['state_code'], rare))

print('after dedupe/filter:', len(kept), file=sys.stderr)
print(Counter(c['status'] for c in kept), file=sys.stderr)

# ── 4. select with state diversity (cap per state), max 280 ─────────────────
MAX_TOTAL, MAX_PER_STATE = 280, 28
by_state = defaultdict(int)
final = []
# round-robin-ish: keep sorted by status rank, then interleave states
for c in kept:
    if len(final) >= MAX_TOTAL: break
    if by_state[c['state_code']] >= MAX_PER_STATE: continue
    by_state[c['state_code']] += 1
    final.append(c)

print('final:', len(final), Counter(c['state_code'] for c in final).most_common(), file=sys.stderr)

# ── 5. emit CaseDetail JSON ──────────────────────────────────────────────────
STATUS_EVENT = {
    'CLOSED_CONVICTED': ('CONVICTION','JUDGMENT',True),
    'CLOSED_ACQUITTED': ('ACQUITTAL','JUDGMENT',True),
    'APPEALED': ('APPEAL_FILED','APPEAL',False),
    'CHARGES_FRAMED': ('CHARGES_FRAMED','COURT_PROCEEDINGS',False),
    'CHARGESHEET_FILED': ('CHARGESHEET_FILED','CHARGESHEET',True),
    'TRIAL_IN_PROGRESS': ('HEARING_HELD','COURT_PROCEEDINGS',False),
    'UNDER_INVESTIGATION': ('ARREST_MADE','ARREST',True),
    'REPORTED': ('FIR_REGISTERED','FIR_FILING',True),
}
SRC_CODE = {
    'The Times of India':'TOI','The Hindu':'HINDU','NDTV':'NDTV','The Indian Express':'IE',
    'Hindustan Times':'HT','India Today':'IT','Deccan Herald':'DH','Telegraph India':'TI',
    'The Tribune':'TRIB','Live Law':'LL','Bar and Bench':'BB','News18':'N18',
    'Free Press Journal':'FPJ','Deccan Chronicle':'DC','The New Indian Express':'NIE',
    'ThePrint':'TP',
}

out, seq_by_state = [], defaultdict(int)
for c in sorted(final, key=lambda x: x['pub_date'], reverse=True):
    code = c['state_code']
    seq_by_state[code] += 1
    seq = seq_by_state[code]
    year = c['pub_date'][:4]
    cid = f'live-ing-{code.lower()}-{year}-{seq:03d}'
    headline = re.sub(r'\s*[-|–]\s*[A-Za-z0-9 .&\']+$', '', c['title']).strip()
    etype, ecat, milestone = STATUS_EVENT[c['status']]
    src_code = SRC_CODE.get(c['source'], re.sub(r'[^A-Z]', '', c['source'].upper())[:6] or 'NEWS')
    out.append({
        'id': cid,
        'case_ref': f'PRJ-LIVE-{code}-{year}-{seq:04d}',
        'victim_pseudonym': f'VICTIM-{code}-{year}-{seq:04d}',
        'headline': headline,
        'crime_category': c['crime_category'],
        'status': c['status'],
        'incident_date': c['pub_date'],
        'incident_date_approx': True,
        'state': c['state'],
        'district': c['district'],
        'ipc_sections': c['ipc_sections'],
        'pocso_applicable': c['pocso_applicable'],
        'fast_track_court': c['fast_track_court'],
        'num_victims': 1,
        'event_count': 1,
        'last_event_at': c['pub_date'] + 'T00:00:00',
        'overall_confidence': 0.7,
        'conviction_achieved': c['conviction_achieved'],
        'created_at': c['pub_date'] + 'T00:00:00',
        'updated_at': c['pub_date'] + 'T00:00:00',
        'events': [{
            'id': f'evt-{cid}-1',
            'event_type': etype,
            'event_category': ecat,
            'event_date': c['pub_date'],
            'event_date_approx': True,
            'summary': headline,
            'court_name': None,
            'source_attribution': [{
                'source_code': src_code,
                'source_name': c['source'],
                'published_at': c['pub_date'],
                'source_url': c['link'],
            }],
            'source_quote': None,
            'confidence_score': 0.7,
            'moderation_status': 'APPROVED',
            'is_milestone': milestone,
        }],
    })

with open(sys.argv[1] if len(sys.argv) > 1 else 'live-cases-ingested.json', 'w') as f:
    json.dump(out, f, ensure_ascii=False)
print('written:', len(out), file=sys.stderr)
