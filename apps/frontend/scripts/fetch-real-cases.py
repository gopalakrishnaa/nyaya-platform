#!/usr/bin/env python3
"""Fetch real GBV case reports from Google News RSS (15+ Indian outlets),
heuristically extract structured case records for the Nyaya platform.

Usage (from apps/frontend/):
  python3 scripts/fetch-real-cases.py cases_raw.json
  python3 scripts/build-cases-dataset.py src/lib/live-cases-ingested.json

Stage 1 (this script) pulls ~70 RSS queries (per-outlet + per-topic/year),
keyword-filters titles, extracts state/category/status heuristics.
Stage 2 (build-cases-dataset.py) regrades, dedupes, and emits CaseDetail[]."""
import json, re, sys, time, hashlib
import urllib.request, urllib.parse
import xml.etree.ElementTree as ET
from html import unescape

UA = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

# ── city/region → (state name, code) ────────────────────────────────────────
STATES = {
    'andhra pradesh': ('Andhra Pradesh','AP'), 'arunachal pradesh': ('Arunachal Pradesh','AR'),
    'assam': ('Assam','AS'), 'bihar': ('Bihar','BR'), 'chhattisgarh': ('Chhattisgarh','CG'),
    'goa': ('Goa','GA'), 'gujarat': ('Gujarat','GJ'), 'haryana': ('Haryana','HR'),
    'himachal pradesh': ('Himachal Pradesh','HP'), 'jharkhand': ('Jharkhand','JH'),
    'karnataka': ('Karnataka','KA'), 'kerala': ('Kerala','KL'),
    'madhya pradesh': ('Madhya Pradesh','MP'), 'maharashtra': ('Maharashtra','MH'),
    'manipur': ('Manipur','MN'), 'meghalaya': ('Meghalaya','ML'), 'mizoram': ('Mizoram','MZ'),
    'nagaland': ('Nagaland','NL'), 'odisha': ('Odisha','OD'), 'punjab': ('Punjab','PB'),
    'rajasthan': ('Rajasthan','RJ'), 'sikkim': ('Sikkim','SK'), 'tamil nadu': ('Tamil Nadu','TN'),
    'telangana': ('Telangana','TG'), 'tripura': ('Tripura','TR'),
    'uttar pradesh': ('Uttar Pradesh','UP'), 'uttarakhand': ('Uttarakhand','UK'),
    'west bengal': ('West Bengal','WB'), 'delhi': ('Delhi','DL'),
    'jammu and kashmir': ('Jammu & Kashmir','JK'), 'jammu & kashmir': ('Jammu & Kashmir','JK'),
    'kashmir': ('Jammu & Kashmir','JK'), 'chandigarh': ('Chandigarh','CH'),
    'puducherry': ('Puducherry','PY'), 'pondicherry': ('Puducherry','PY'),
}
CITIES = {
    # Maharashtra
    'mumbai':'maharashtra','pune':'maharashtra','nagpur':'maharashtra','thane':'maharashtra',
    'nashik':'maharashtra','aurangabad':'maharashtra','solapur':'maharashtra','kolhapur':'maharashtra',
    'navi mumbai':'maharashtra','palghar':'maharashtra','satara':'maharashtra','latur':'maharashtra',
    # UP
    'lucknow':'uttar pradesh','kanpur':'uttar pradesh','agra':'uttar pradesh','varanasi':'uttar pradesh',
    'prayagraj':'uttar pradesh','allahabad':'uttar pradesh','noida':'uttar pradesh','ghaziabad':'uttar pradesh',
    'meerut':'uttar pradesh','bareilly':'uttar pradesh','gorakhpur':'uttar pradesh','unnao':'uttar pradesh',
    'hathras':'uttar pradesh','banda':'uttar pradesh','shahjahanpur':'uttar pradesh','aligarh':'uttar pradesh',
    'moradabad':'uttar pradesh','saharanpur':'uttar pradesh','jhansi':'uttar pradesh','ayodhya':'uttar pradesh',
    'bulandshahr':'uttar pradesh','badaun':'uttar pradesh','etah':'uttar pradesh','firozabad':'uttar pradesh',
    'muzaffarnagar':'uttar pradesh','rampur':'uttar pradesh','sambhal':'uttar pradesh','hapur':'uttar pradesh',
    # Delhi
    'new delhi':'delhi','south delhi':'delhi','east delhi':'delhi','dwarka':'delhi','rohini':'delhi',
    # Rajasthan
    'jaipur':'rajasthan','jodhpur':'rajasthan','udaipur':'rajasthan','kota':'rajasthan','ajmer':'rajasthan',
    'alwar':'rajasthan','bikaner':'rajasthan','bharatpur':'rajasthan','sikar':'rajasthan','churu':'rajasthan',
    # WB
    'kolkata':'west bengal','howrah':'west bengal','durgapur':'west bengal','asansol':'west bengal',
    'siliguri':'west bengal','malda':'west bengal','hooghly':'west bengal','nadia':'west bengal',
    'north 24 parganas':'west bengal','south 24 parganas':'west bengal','sandeshkhali':'west bengal',
    # Karnataka
    'bengaluru':'karnataka','bangalore':'karnataka','mysuru':'karnataka','mysore':'karnataka',
    'mangaluru':'karnataka','hubli':'karnataka','hubballi':'karnataka','belagavi':'karnataka',
    'udupi':'karnataka','hassan':'karnataka','tumakuru':'karnataka','ballari':'karnataka',
    # TN
    'chennai':'tamil nadu','coimbatore':'tamil nadu','madurai':'tamil nadu','tiruchirappalli':'tamil nadu',
    'trichy':'tamil nadu','salem':'tamil nadu','tirunelveli':'tamil nadu','vellore':'tamil nadu',
    'pollachi':'tamil nadu','erode':'tamil nadu','thanjavur':'tamil nadu','tiruppur':'tamil nadu',
    # MP
    'bhopal':'madhya pradesh','indore':'madhya pradesh','gwalior':'madhya pradesh','jabalpur':'madhya pradesh',
    'ujjain':'madhya pradesh','sagar':'madhya pradesh','rewa':'madhya pradesh','satna':'madhya pradesh',
    'sidhi':'madhya pradesh','ratlam':'madhya pradesh','chhatarpur':'madhya pradesh',
    # Bihar
    'patna':'bihar','gaya':'bihar','muzaffarpur':'bihar','bhagalpur':'bihar','darbhanga':'bihar',
    'araria':'bihar','vaishali':'bihar','nalanda':'bihar','begusarai':'bihar','samastipur':'bihar',
    # AP / TG
    'visakhapatnam':'andhra pradesh','vijayawada':'andhra pradesh','guntur':'andhra pradesh',
    'nellore':'andhra pradesh','tirupati':'andhra pradesh','kurnool':'andhra pradesh',
    'hyderabad':'telangana','warangal':'telangana','nizamabad':'telangana','secunderabad':'telangana',
    'shamshabad':'telangana','karimnagar':'telangana',
    # Gujarat
    'ahmedabad':'gujarat','surat':'gujarat','vadodara':'gujarat','rajkot':'gujarat','bhavnagar':'gujarat',
    'gandhinagar':'gujarat','junagadh':'gujarat','dahod':'gujarat',
    # Kerala
    'thiruvananthapuram':'kerala','kochi':'kerala','kozhikode':'kerala','thrissur':'kerala',
    'kollam':'kerala','kannur':'kerala','kottayam':'kerala','palakkad':'kerala','ernakulam':'kerala',
    'alappuzha':'kerala','malappuram':'kerala','wayanad':'kerala','idukki':'kerala',
    # Odisha
    'bhubaneswar':'odisha','cuttack':'odisha','rourkela':'odisha','berhampur':'odisha','sambalpur':'odisha',
    'puri':'odisha','balasore':'odisha','koraput':'odisha',
    # Punjab / Haryana / HP / UK / JK / CH
    'ludhiana':'punjab','amritsar':'punjab','jalandhar':'punjab','patiala':'punjab','bathinda':'punjab',
    'mohali':'punjab','gurugram':'haryana','gurgaon':'haryana','faridabad':'haryana','rohtak':'haryana',
    'hisar':'haryana','panipat':'haryana','karnal':'haryana','ambala':'haryana','jind':'haryana',
    'sonipat':'haryana','shimla':'himachal pradesh','mandi':'himachal pradesh','kangra':'himachal pradesh',
    'dehradun':'uttarakhand','haridwar':'uttarakhand','rishikesh':'uttarakhand','nainital':'uttarakhand',
    'srinagar':'jammu and kashmir','jammu':'jammu and kashmir','kathua':'jammu and kashmir',
    # NE / others
    'guwahati':'assam','dibrugarh':'assam','silchar':'assam','jorhat':'assam','nagaon':'assam',
    'imphal':'manipur','shillong':'meghalaya','aizawl':'mizoram','kohima':'nagaland','dimapur':'nagaland',
    'agartala':'tripura','itanagar':'arunachal pradesh','gangtok':'sikkim','panaji':'goa','margao':'goa',
    'ranchi':'jharkhand','jamshedpur':'jharkhand','dhanbad':'jharkhand','bokaro':'jharkhand',
    'raipur':'chhattisgarh','bilaspur':'chhattisgarh','durg':'chhattisgarh','korba':'chhattisgarh',
}

EXCLUDE = re.compile(r'\b(cases rise|cases up|crime rate|ncrb|statistics|study|survey|report says|'
    r'opinion|editorial|explained|why india|data shows|percent|per cent|movie|film|review|'
    r'web series|trailer|box office|analysis)\b', re.I)
RELEVANT = re.compile(r'\b(rape|raped|rapes|gang-rape|gangrape|pocso|molest\w*|sexual assault|'
    r'sexually assault\w*|dowry|acid attack|eve.teas\w*|stalk\w*|traffick\w*|honou?r killing|'
    r'sexual harass\w*|outraging modesty|domestic violence)\b', re.I)
CASE_SIGNAL = re.compile(r'\b(convict\w*|sentence\w*|arrest\w*|held|nabbed|detained|fir|chargesheet|'
    r'charge sheet|court|jail|imprisonment|death penalty|life term|rigorous|accused|booked|'
    r'tribunal|acquit\w*|bail|custody|pocso|victim|survivor|minor|girl|woman|man)\b', re.I)

def classify_category(t):
    tl = t.lower()
    if re.search(r'gang.?rape', tl): return 'GANG_RAPE'
    if 'acid' in tl: return 'ACID_ATTACK'
    if re.search(r'dowry\s+death', tl): return 'DOWRY_DEATH'
    if 'dowry' in tl: return 'DOWRY_HARASSMENT'
    if re.search(r'honou?r killing', tl): return 'HONOR_KILLING'
    if re.search(r'traffick', tl): return 'TRAFFICKING'
    if re.search(r'stalk', tl): return 'STALKING'
    if re.search(r'pocso|minor|girl child|\b(\d{1,2})[- ]year[- ]old girl', tl) and re.search(r'rape|assault|molest|abuse', tl):
        return 'POCSO_VIOLATION'
    if re.search(r'\brape', tl): return 'RAPE'
    if re.search(r'molest', tl): return 'MOLESTATION'
    if re.search(r'domestic violence|498a|cruelty by husband', tl): return 'DOMESTIC_VIOLENCE'
    if re.search(r'cyber|online|morph|deepfake|revenge porn', tl): return 'CYBER_CRIME_AGAINST_WOMEN'
    if re.search(r'sexual assault|sexually assault', tl): return 'SEXUAL_ASSAULT'
    if re.search(r'sexual harass|outraging modesty|eve.teas', tl): return 'SEXUAL_ASSAULT'
    return None

def classify_status(t):
    tl = t.lower()
    if re.search(r'acquit', tl): return ('CLOSED_ACQUITTED', False)
    if re.search(r'convict\w*|sentenced|death penalty|life (term|imprisonment)|years? (of )?(rigorous |jail |imprisonment)|jail term|gets \d+ year', tl):
        return ('CLOSED_CONVICTED', True)
    if re.search(r'chargesheet|charge sheet', tl): return ('CHARGESHEET_FILED', False)
    if re.search(r'charges framed', tl): return ('CHARGES_FRAMED', False)
    if re.search(r'trial|hearing|court reserves|verdict|witness', tl): return ('TRIAL_IN_PROGRESS', False)
    if re.search(r'arrest\w*|held|nabbed|detained|custody|booked|surrender', tl): return ('UNDER_INVESTIGATION', False)
    if re.search(r'\bfir\b|complaint|registered', tl): return ('REPORTED', False)
    return ('REPORTED', False)

def find_state(t):
    tl = ' ' + t.lower() + ' '
    for name,(full,code) in STATES.items():
        if re.search(r'\b' + re.escape(name) + r'\b', tl): return (full, code, None)
    for city, st in CITIES.items():
        if re.search(r'\b' + re.escape(city) + r'\b', tl):
            full, code = STATES[st]
            return (full, code, city.title())
    return None

def norm_title(t):
    t = re.sub(r'\s*[-|–]\s*[A-Za-z .&]+$', '', t)  # strip trailing outlet name
    t = re.sub(r'[^a-z0-9 ]', '', t.lower())
    return set(t.split())

def fetch(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:
            if i == tries-1:
                print(f'  FAIL {e}', file=sys.stderr)
                return None
            time.sleep(2)

def gnews(query):
    q = urllib.parse.quote(query)
    url = f'https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en'
    raw = fetch(url)
    if not raw: return []
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return []
    items = []
    for it in root.iter('item'):
        title = unescape((it.findtext('title') or '').strip())
        link = (it.findtext('link') or '').strip()
        pub = (it.findtext('pubDate') or '').strip()
        src = it.find('source')
        source = unescape(src.text.strip()) if src is not None and src.text else 'Google News'
        items.append({'title': title, 'link': link, 'pubDate': pub, 'source': source})
    return items

OUTLETS = [
    'timesofindia.indiatimes.com', 'hindustantimes.com', 'ndtv.com', 'indianexpress.com',
    'thehindu.com', 'indiatoday.in', 'deccanherald.com', 'telegraphindia.com',
    'tribuneindia.com', 'livelaw.in', 'barandbench.com', 'news18.com',
    'freepressjournal.in', 'deccanchronicle.com', 'newindianexpress.com', 'theprint.in',
]
TOPICS = [
    'rape case convicted court', 'POCSO court sentenced', 'gang rape arrested',
    'sexual assault FIR registered', 'dowry death husband arrested', 'acid attack woman case',
    'molestation case court', 'rape accused chargesheet', 'POCSO fast track court conviction',
    'trafficking girl rescued arrested', 'domestic violence case court india', 'honour killing arrested india',
]
YEARS = ['after:2024-01-01 before:2024-12-31', 'after:2025-01-01 before:2025-12-31', 'after:2026-01-01']

def main():
    queries = []
    for site in OUTLETS:
        queries.append(f'site:{site} rape case court sentenced')
        queries.append(f'site:{site} POCSO convicted')
    for t in TOPICS:
        for y in YEARS:
            queries.append(f'{t} {y}')

    raw_items, seen_links = [], set()
    for i, q in enumerate(queries):
        items = gnews(q)
        print(f'[{i+1}/{len(queries)}] {q!r} -> {len(items)}', file=sys.stderr)
        for it in items:
            if it['link'] in seen_links: continue
            seen_links.add(it['link'])
            raw_items.append(it)
        time.sleep(0.4)

    print(f'raw unique: {len(raw_items)}', file=sys.stderr)

    # filter + extract
    cases, title_sets = [], []
    for it in raw_items:
        t = it['title']
        if len(t) < 25: continue
        if EXCLUDE.search(t): continue
        if not RELEVANT.search(t): continue
        if not CASE_SIGNAL.search(t): continue
        st = find_state(t)
        if not st: continue
        cat = classify_category(t)
        if not cat: continue
        nt = norm_title(t)
        if any(len(nt & p) / max(1, len(nt | p)) > 0.55 for p in title_sets): continue
        title_sets.append(nt)
        status, convicted = classify_status(t)
        # pub date
        iso = None
        try:
            from email.utils import parsedate_to_datetime
            iso = parsedate_to_datetime(it['pubDate']).strftime('%Y-%m-%d')
        except Exception:
            pass
        pocso = cat == 'POCSO_VIOLATION' or bool(re.search(r'pocso|minor', t, re.I))
        ipc = sorted({int(m) for m in re.findall(r'\b(302|304B|306|326A|354|363|366|375|376|377|498A|509)\b', t, re.I) if m.isdigit()})
        cases.append({
            'title': t, 'link': it['link'], 'source': it['source'], 'pub_date': iso,
            'state': st[0], 'state_code': st[1], 'district': st[2] or st[0],
            'crime_category': cat, 'status': status, 'conviction_achieved': convicted,
            'pocso_applicable': pocso, 'fast_track_court': bool(re.search(r'fast.track', t, re.I)),
            'ipc_sections': ipc,
        })

    print(f'extracted: {len(cases)}', file=sys.stderr)
    with open(sys.argv[1] if len(sys.argv) > 1 else 'cases_raw.json', 'w') as f:
        json.dump(cases, f, indent=1, ensure_ascii=False)

if __name__ == '__main__':
    main()
