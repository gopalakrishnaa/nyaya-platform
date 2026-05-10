-- =============================================================================
-- NYAYA PLATFORM — Seed Data for Testing
-- All cases are fictional and properly anonymized.
-- Victim pseudonyms are HMAC-derived tokens (no real names stored).
-- =============================================================================

-- =============================================================================
-- SAMPLE CASES
-- =============================================================================

-- Case 1: POCSO case from Maharashtra, fast-track court, conviction achieved
INSERT INTO cases (
  id, case_ref, victim_pseudonym, crime_category, status,
  incident_date, incident_date_approx, state, district,
  fir_number, fir_police_station,
  ipc_sections, pocso_applicable, fast_track_court,
  court_name, court_case_number, sessions_case_number,
  num_victims, num_accused, victim_age_group,
  conviction_achieved, conviction_date, sentence_years, compensation_inr,
  overall_confidence, source_count
) VALUES (
  'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
  'MH-MUM-2023-001',
  'VICTIM-A1B2C3',
  'POCSO_VIOLATION',
  'CLOSED_CONVICTED',
  '2023-03-15', FALSE,
  'MH', 'Mumbai',
  '45/2023', 'Andheri Police Station',
  ARRAY[376, 354], TRUE, TRUE,
  'Fast Track Special Court No. 3, Mumbai', 'FTSC/3/2023/45', 'SC/215/2023',
  1, 1, 'MINOR_UNDER_12',
  TRUE, '2024-01-20', 20.00, 500000,
  0.92, 4
);

-- Case 2: Domestic violence case from Delhi, trial in progress
INSERT INTO cases (
  id, case_ref, victim_pseudonym, crime_category, status,
  incident_date, incident_date_approx, state, district,
  fir_number, fir_police_station,
  ipc_sections, pocso_applicable, fast_track_court,
  court_name, court_case_number, sessions_case_number,
  num_victims, num_accused, victim_age_group,
  overall_confidence, source_count
) VALUES (
  'b2c3d4e5-f6a7-8901-bcde-f12345678901',
  'DL-NDW-2023-042',
  'VICTIM-B2C3D4',
  'DOMESTIC_VIOLENCE',
  'TRIAL_IN_PROGRESS',
  '2023-06-08', FALSE,
  'DL', 'New Delhi',
  '112/2023', 'Dwarka North Police Station',
  ARRAY[498, 498, 323, 506], FALSE, FALSE,
  'Additional Sessions Court, Dwarka', 'ASC/DWK/2023/112', 'SC/487/2023',
  1, 2, 'ADULT_18_30',
  0.87, 3
);

-- Case 3: Acid attack case from Uttar Pradesh, chargesheet filed, accused on bail
INSERT INTO cases (
  id, case_ref, victim_pseudonym, crime_category, status,
  incident_date, incident_date_approx, state, district,
  fir_number, fir_police_station,
  ipc_sections, pocso_applicable, fast_track_court,
  court_name, court_case_number,
  num_victims, num_accused, victim_age_group,
  overall_confidence, source_count
) VALUES (
  'c3d4e5f6-a7b8-9012-cdef-123456789012',
  'UP-LKO-2023-089',
  'VICTIM-C3D4E5',
  'ACID_ATTACK',
  'CHARGESHEET_FILED',
  '2023-09-22', FALSE,
  'UP', 'Lucknow',
  '221/2023', 'Hazratganj Police Station',
  ARRAY[326, 307, 34], FALSE, FALSE,
  'Sessions Court, Lucknow', 'SC/LKO/2023/221',
  1, 2, 'ADULT_18_30',
  0.85, 5
);

-- Case 4: Rape case from West Bengal, judgment delivered, acquittal (monitoring required)
INSERT INTO cases (
  id, case_ref, victim_pseudonym, crime_category, status,
  incident_date, incident_date_approx, state, district,
  fir_number, fir_police_station,
  ipc_sections, pocso_applicable, fast_track_court,
  court_name, court_case_number, sessions_case_number, hc_case_number,
  num_victims, num_accused, victim_age_group,
  conviction_achieved,
  overall_confidence, source_count
) VALUES (
  'd4e5f6a7-b8c9-0123-defa-234567890123',
  'WB-KOL-2022-156',
  'VICTIM-D4E5F6',
  'RAPE',
  'APPEALED',
  '2022-04-11', FALSE,
  'WB', 'Kolkata',
  '89/2022', 'New Market Police Station',
  ARRAY[376], FALSE, FALSE,
  'Sessions Court, Kolkata', 'SC/KOL/2022/89', 'ST/2022/89', 'CRA/HC/KOL/2024/33',
  1, 1, 'ADULT_31_45',
  FALSE,
  0.78, 6
);

-- Case 5: Dowry death case from Karnataka, investigation stage
INSERT INTO cases (
  id, case_ref, victim_pseudonym, crime_category, status,
  incident_date, incident_date_approx, state, district,
  fir_number, fir_police_station,
  ipc_sections, pocso_applicable, fast_track_court,
  num_victims, num_accused, victim_age_group,
  overall_confidence, source_count
) VALUES (
  'e5f6a7b8-c9d0-1234-efab-345678901234',
  'KA-BLR-2024-003',
  'VICTIM-E5F6A7',
  'DOWRY_DEATH',
  'UNDER_INVESTIGATION',
  '2024-01-03', FALSE,
  'KA', 'Bengaluru Urban',
  '7/2024', 'Jayanagar Police Station',
  ARRAY[304, 306, 498, 34], FALSE, FALSE,
  1, 3, 'ADULT_18_30',
  0.80, 2
);

-- =============================================================================
-- SAMPLE CASE EVENTS
-- =============================================================================

-- Events for Case 1 (MH-MUM-2023-001 — POCSO conviction)
INSERT INTO case_events (
  id, case_id, event_type, event_category, event_date,
  summary, confidence_score, moderation_status, is_milestone,
  source_attribution
) VALUES
  (
    'f1e2d3c4-b5a6-7890-1234-567890abcdef',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'FIR_REGISTERED', 'FIR_FILING', '2023-03-15',
    'FIR registered at Andheri Police Station under IPC 376 and POCSO Act. Victim is a minor under 12 years of age.',
    0.95, 'APPROVED', TRUE,
    '[{"source_code": "PTI", "url": "https://ptinews.com/crime/mumbai-pocso-fir-2023-03-15", "published_at": "2023-03-16"}]'
  ),
  (
    'f2e3d4c5-b6a7-8901-2345-678901abcdef',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'MEDICAL_EXAMINATION', 'MEDICAL', '2023-03-15',
    'Victim medically examined at KEM Hospital within 6 hours of FIR. Forensic samples collected.',
    0.92, 'APPROVED', FALSE,
    '[{"source_code": "PTI", "url": "https://ptinews.com/crime/mumbai-pocso-medical-2023-03-15", "published_at": "2023-03-16"}]'
  ),
  (
    'f3e4d5c6-b7a8-9012-3456-789012abcdef',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'ARREST_MADE', 'ARREST', '2023-03-17',
    'Accused arrested by Andheri Police. Remand sought.',
    0.93, 'APPROVED', TRUE,
    '[{"source_code": "ANI", "url": "https://aninews.in/news/mumbai-pocso-arrest-march-2023", "published_at": "2023-03-17"}]'
  ),
  (
    'f4e5d6c7-b8a9-0123-4567-890123abcdef',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'CHARGESHEET_FILED', 'CHARGESHEET', '2023-05-10',
    'Chargesheet filed within 60-day POCSO deadline. 150-page chargesheet names one accused.',
    0.96, 'APPROVED', TRUE,
    '[{"source_code": "THEHINDU", "url": "https://thehindu.com/news/cities/mumbai/pocso-chargesheet-filed-2023", "published_at": "2023-05-11"}]'
  ),
  (
    'f5e6d7c8-b9a0-1234-5678-901234abcdef',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'CASE_TRANSFERRED_FTSC', 'ADMINISTRATIVE', '2023-06-02',
    'Case transferred to Fast Track Special Court No. 3 as mandated under POCSO Amendment Act 2019.',
    0.97, 'APPROVED', TRUE,
    '[{"source_code": "ECOURTS", "url": "https://ecourts.gov.in/MH/case/FTSC3/2023/45", "published_at": "2023-06-05"}]'
  ),
  (
    'f6e7d8c9-b0a1-2345-6789-012345abcdef',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'CONVICTION', 'JUDGMENT', '2024-01-20',
    'Accused convicted on all charges under IPC 376AB and POCSO Sections 4 and 6. Trial completed within one year as mandated.',
    0.98, 'APPROVED', TRUE,
    '[{"source_code": "INDIAKANOON", "url": "https://indiankanoon.org/doc/MH-FTSC3-2023-45", "published_at": "2024-01-21"}, {"source_code": "PTI", "url": "https://ptinews.com/crime/mumbai-pocso-conviction-2024", "published_at": "2024-01-21"}]'
  ),
  (
    'f7e8d9c0-b1a2-3456-7890-123456abcdef',
    'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
    'SENTENCE_PRONOUNCED', 'JUDGMENT', '2024-01-20',
    'Sentenced to 20 years rigorous imprisonment. Compensation of Rs. 5,00,000 ordered from DSHA fund.',
    0.98, 'APPROVED', TRUE,
    '[{"source_code": "INDIAKANOON", "url": "https://indiankanoon.org/doc/MH-FTSC3-2023-45-sentence", "published_at": "2024-01-21"}]'
  );

-- Events for Case 2 (DL-NDW-2023-042 — Domestic violence, trial in progress)
INSERT INTO case_events (
  id, case_id, event_type, event_category, event_date,
  summary, confidence_score, moderation_status, is_milestone,
  source_attribution
) VALUES
  (
    'e1d2c3b4-a5f6-7890-abcd-ef0123456789',
    'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    'FIR_REGISTERED', 'FIR_FILING', '2023-06-08',
    'FIR registered at Dwarka North PS under IPC 498A, 323, and 506 against husband and mother-in-law.',
    0.90, 'APPROVED', TRUE,
    '[{"source_code": "HT", "url": "https://hindustantimes.com/delhi/domestic-violence-dwarka-2023-06-09", "published_at": "2023-06-09"}]'
  ),
  (
    'e2d3c4b5-a6f7-8901-bcde-f01234567890',
    'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    'BAIL_APPLIED', 'BAIL', '2023-08-15',
    'Accused filed bail application before Sessions Court, Dwarka.',
    0.82, 'APPROVED', FALSE,
    '[{"source_code": "ECOURTS", "url": "https://ecourts.gov.in/DL/case/ASC/DWK/2023/112", "published_at": "2023-08-16"}]'
  ),
  (
    'e3d4c5b6-a7f8-9012-cdef-012345678901',
    'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    'BAIL_REJECTED', 'BAIL', '2023-08-28',
    'Bail rejected. Court noted history of harassment and flight risk.',
    0.88, 'APPROVED', FALSE,
    '[{"source_code": "ECOURTS", "url": "https://ecourts.gov.in/DL/case/ASC/DWK/2023/112/bail", "published_at": "2023-08-29"}]'
  ),
  (
    'e4d5c6b7-a8f9-0123-defa-123456789012',
    'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    'CHARGESHEET_FILED', 'CHARGESHEET', '2023-09-05',
    'Chargesheet filed naming husband (accused 1) and mother-in-law (accused 2).',
    0.91, 'APPROVED', TRUE,
    '[{"source_code": "ECOURTS", "url": "https://ecourts.gov.in/DL/case/ASC/DWK/2023/112/chargesheet", "published_at": "2023-09-06"}]'
  ),
  (
    'e5d6c7b8-a9f0-1234-efab-234567890123',
    'b2c3d4e5-f6a7-8901-bcde-f12345678901',
    'TRIAL_COMMENCED', 'COURT_PROCEEDINGS', '2024-02-12',
    'Trial commenced at Additional Sessions Court, Dwarka. Charges framed against both accused.',
    0.85, 'APPROVED', TRUE,
    '[{"source_code": "ECOURTS", "url": "https://ecourts.gov.in/DL/case/ASC/DWK/2023/112/trial", "published_at": "2024-02-13"}]'
  );

-- Events for Case 3 (UP-LKO-2023-089 — Acid attack)
INSERT INTO case_events (
  id, case_id, event_type, event_category, event_date,
  summary, bail_amount_inr, confidence_score, moderation_status, is_milestone,
  source_attribution
) VALUES
  (
    'd1c2b3a4-f5e6-7890-abcd-ef9012345678',
    'c3d4e5f6-a7b8-9012-cdef-123456789012',
    'FIR_REGISTERED', 'FIR_FILING', '2023-09-22',
    'FIR registered under IPC 326 (grievous hurt by acid), 307 (attempt to murder), and 34 (common intention).',
    NULL, 0.93, 'APPROVED', TRUE,
    '[{"source_code": "ANI", "url": "https://aninews.in/news/lucknow-acid-attack-fir-sept-2023", "published_at": "2023-09-22"}]'
  ),
  (
    'd2c3b4a5-f6e7-8901-bcde-f90123456789',
    'c3d4e5f6-a7b8-9012-cdef-123456789012',
    'MEDICAL_EXAMINATION', 'MEDICAL', '2023-09-22',
    'Victim admitted to KGMU Trauma Centre with 45% burns to face and upper body. Critical condition.',
    NULL, 0.95, 'APPROVED', FALSE,
    '[{"source_code": "HT", "url": "https://hindustantimes.com/lucknow/acid-attack-kgmu-2023-09-23", "published_at": "2023-09-23"}]'
  ),
  (
    'd3c4b5a6-f7e8-9012-cdef-a01234567890',
    'c3d4e5f6-a7b8-9012-cdef-123456789012',
    'ARREST_MADE', 'ARREST', '2023-09-24',
    'Primary accused arrested within 48 hours. Second accused absconding.',
    NULL, 0.92, 'APPROVED', TRUE,
    '[{"source_code": "PTI", "url": "https://ptinews.com/crime/lucknow-acid-arrest-2023-09-24", "published_at": "2023-09-24"}]'
  ),
  (
    'd4c5b6a7-f8e9-0123-defa-b12345678901',
    'c3d4e5f6-a7b8-9012-cdef-123456789012',
    'BAIL_GRANTED', 'BAIL', '2024-01-10',
    'Primary accused granted bail by Sessions Court, Lucknow. Bail amount Rs. 1,00,000 with surety.',
    100000, 0.89, 'APPROVED', FALSE,
    '[{"source_code": "ECOURTS", "url": "https://ecourts.gov.in/UP/case/SC/LKO/2023/221/bail-order", "published_at": "2024-01-11"}]'
  ),
  (
    'd5c6b7a8-f9e0-1234-efab-c23456789012',
    'c3d4e5f6-a7b8-9012-cdef-123456789012',
    'CHARGESHEET_FILED', 'CHARGESHEET', '2023-12-18',
    'Chargesheet filed naming both accused. Second accused still absconding; NBW issued.',
    NULL, 0.91, 'APPROVED', TRUE,
    '[{"source_code": "ECOURTS", "url": "https://ecourts.gov.in/UP/case/SC/LKO/2023/221/chargesheet", "published_at": "2023-12-20"}]'
  );

-- Events for Case 4 (WB-KOL-2022-156 — Acquittal, now in HC appeal)
INSERT INTO case_events (
  id, case_id, event_type, event_category, event_date,
  summary, confidence_score, moderation_status, is_milestone,
  source_attribution
) VALUES
  (
    'c1b2a3f4-e5d6-7890-abcd-ef8901234567',
    'd4e5f6a7-b8c9-0123-defa-234567890123',
    'FIR_REGISTERED', 'FIR_FILING', '2022-04-11',
    'FIR registered at New Market PS under IPC 376.',
    0.88, 'APPROVED', TRUE,
    '[{"source_code": "ABP", "url": "https://anandabazar.com/kolkata-rape-fir-april-2022", "published_at": "2022-04-12"}]'
  ),
  (
    'c2b3a4f5-e6d7-8901-bcde-f89012345678',
    'd4e5f6a7-b8c9-0123-defa-234567890123',
    'CHARGESHEET_FILED', 'CHARGESHEET', '2022-07-05',
    'Chargesheet filed after 85 days — 5 days beyond the 90-day statutory deadline. Delay noted.',
    0.86, 'APPROVED', TRUE,
    '[{"source_code": "ECOURTS", "url": "https://ecourts.gov.in/WB/case/SC/KOL/2022/89/chargesheet", "published_at": "2022-07-06"}]'
  ),
  (
    'c3b4a5f6-e7d8-9012-cdef-890123456789',
    'd4e5f6a7-b8c9-0123-defa-234567890123',
    'VICTIM_HOSTILE', 'COURT_PROCEEDINGS', '2023-03-14',
    'Victim turned hostile during cross-examination. Court ordered video-link deposition.',
    0.79, 'APPROVED', FALSE,
    '[{"source_code": "INDIAKANOON", "url": "https://indiankanoon.org/doc/WB-SC-KOL-2022-89-hostile", "published_at": "2023-03-15"}]'
  ),
  (
    'c4b5a6f7-e8d9-0123-defa-901234567890',
    'd4e5f6a7-b8c9-0123-defa-234567890123',
    'ACQUITTAL', 'JUDGMENT', '2023-11-30',
    'Accused acquitted due to insufficient evidence and victim turning hostile. Judgment criticized by State for improper application of corroboration doctrine.',
    0.91, 'APPROVED', TRUE,
    '[{"source_code": "INDIAKANOON", "url": "https://indiankanoon.org/doc/WB-SC-KOL-2022-89-judgment", "published_at": "2023-12-01"}, {"source_code": "HT", "url": "https://hindustantimes.com/kolkata/rape-acquittal-controversy-2023-12-01", "published_at": "2023-12-01"}]'
  ),
  (
    'c5b6a7f8-e9d0-1234-efab-012345678901',
    'd4e5f6a7-b8c9-0123-defa-234567890123',
    'HIGH_COURT_APPEAL_FILED', 'APPEAL', '2024-02-20',
    'State of West Bengal filed appeal against acquittal at Calcutta High Court under Section 378 CrPC.',
    0.88, 'APPROVED', TRUE,
    '[{"source_code": "ABP", "url": "https://anandabazar.com/calcutta-hc-appeal-rape-acquittal-2024", "published_at": "2024-02-21"}]'
  );

-- Events for Case 5 (KA-BLR-2024-003 — Dowry death, investigation)
INSERT INTO case_events (
  id, case_id, event_type, event_category, event_date,
  summary, confidence_score, moderation_status, is_milestone,
  source_attribution
) VALUES
  (
    'b1a2f3e4-d5c6-7890-abcd-ef7890123456',
    'e5f6a7b8-c9d0-1234-efab-345678901234',
    'FIR_REGISTERED', 'FIR_FILING', '2024-01-04',
    'FIR registered at Jayanagar PS under IPC 304B (dowry death), 306 (abetment of suicide), 498A, and 34. Deceased found in matrimonial home.',
    0.90, 'APPROVED', TRUE,
    '[{"source_code": "HT", "url": "https://hindustantimes.com/bangalore/dowry-death-jayanagar-2024-01-05", "published_at": "2024-01-05"}]'
  ),
  (
    'b2a3f4e5-d6c7-8901-bcde-f78901234567',
    'e5f6a7b8-c9d0-1234-efab-345678901234',
    'MEDICAL_EXAMINATION', 'MEDICAL', '2024-01-04',
    'Post-mortem conducted at Victoria Hospital. Preliminary report indicates strangulation. Final report awaited.',
    0.85, 'APPROVED', FALSE,
    '[{"source_code": "DB", "url": "https://bhaskar.com/bengaluru/dowry-death-postmortem-2024-01-05", "published_at": "2024-01-05"}]'
  ),
  (
    'b3a4f5e6-d7c8-9012-cdef-789012345678',
    'e5f6a7b8-c9d0-1234-efab-345678901234',
    'ARREST_MADE', 'ARREST', '2024-01-06',
    'Husband and in-laws (2 accused) arrested. Third accused (brother-in-law) absconding.',
    0.88, 'APPROVED', TRUE,
    '[{"source_code": "ANI", "url": "https://aninews.in/news/bangalore-dowry-death-arrest-jan-2024", "published_at": "2024-01-06"}]'
  );

-- =============================================================================
-- ARTICLE_CASE_LINKS (linking sanitized articles to cases)
-- These reference IDs would need real sanitized_articles rows in a full seed.
-- Included here as structural examples with placeholder UUIDs.
-- =============================================================================

-- NOTE: Full article ingestion requires the scraper service to be running.
-- The above case and event data are sufficient for testing the API and timeline engine.

-- =============================================================================
-- GEO_AGGREGATES (pre-computed sample data)
-- =============================================================================

INSERT INTO geo_aggregates (
  state, district, year, crime_category,
  total_cases, convicted_cases, acquitted_cases, pending_cases,
  avg_days_to_chargesheet, avg_days_to_judgment,
  pocso_cases, fast_track_cases
) VALUES
  ('MH', 'Mumbai',          2023, 'POCSO_VIOLATION',    42,  18,  4, 20,  55.3, 340.2,  42, 38),
  ('MH', 'Mumbai',          2023, 'RAPE',               67,  22, 12, 33,  78.1, 520.4,   0,  5),
  ('MH', 'Mumbai',          2023, 'DOMESTIC_VIOLENCE', 120,  15,  8, 97,  62.0, 610.0,   0,  0),
  ('DL', 'New Delhi',       2023, 'RAPE',               89,  28, 15, 46,  81.5, 490.3,   0,  6),
  ('DL', 'New Delhi',       2023, 'DOMESTIC_VIOLENCE', 210,  22, 11, 177, 59.2, 590.0,   0,  0),
  ('UP', 'Lucknow',         2023, 'RAPE',               55,  14,  8, 33,  88.2, 560.0,   0,  2),
  ('UP', 'Lucknow',         2023, 'ACID_ATTACK',         8,   3,  1,  4,  72.0, 480.0,   0,  0),
  ('WB', 'Kolkata',         2022, 'RAPE',               44,  10, 14, 20,  91.4, 620.1,   0,  1),
  ('KA', 'Bengaluru Urban', 2024, 'DOWRY_DEATH',        19,   0,  0, 19, NULL,  NULL,     0,  0);
