export type CaseStatus =
  | 'REPORTED'
  | 'UNDER_INVESTIGATION'
  | 'CHARGESHEET_FILED'
  | 'CHARGES_FRAMED'
  | 'TRIAL_IN_PROGRESS'
  | 'JUDGMENT_DELIVERED'
  | 'APPEALED'
  | 'CLOSED_CONVICTED'
  | 'CLOSED_ACQUITTED'
  | 'CLOSED_COMPROMISED'
  | 'CLOSED_NO_EVIDENCE'
  | 'SUPPRESSED';

export type CrimeCategory =
  | 'RAPE'
  | 'GANG_RAPE'
  | 'SEXUAL_ASSAULT'
  | 'POCSO_VIOLATION'
  | 'ACID_ATTACK'
  | 'DOMESTIC_VIOLENCE'
  | 'DOWRY_DEATH'
  | 'DOWRY_HARASSMENT'
  | 'STALKING'
  | 'TRAFFICKING'
  | 'MOLESTATION'
  | 'EVE_TEASING'
  | 'HONOR_KILLING'
  | 'FORCED_MARRIAGE'
  | 'MARITAL_RAPE'
  | 'CYBER_CRIME_AGAINST_WOMEN'
  | 'OTHER';

export interface Case {
  id: string;
  case_ref: string;
  victim_pseudonym: string;
  crime_category: CrimeCategory;
  status: CaseStatus;
  incident_date: string | null;
  incident_date_approx: boolean;
  state: string;
  district: string;
  ipc_sections: number[];
  pocso_applicable: boolean;
  fast_track_court: boolean;
  num_victims: number | null;
  num_accused: number | null;
  victim_age_group: string | null;
  event_count: number;
  last_event_at: string | null;
  overall_confidence: number | null;
  conviction_achieved: boolean;
  conviction_date: string | null;
  sentence_years: number | null;
  compensation_inr: number | null;
  created_at: string;
  updated_at: string;
}

export interface CaseListResponse {
  items: Case[];
  total: number;
  page: number;
  page_size: number;
}

export interface GeoStat {
  state: string;
  district?: string;
  year?: number;
  total_cases: number;
  convicted_cases: number;
  acquitted_cases: number;
  pending_cases: number;
  avg_days_to_chargesheet: number | null;
  avg_days_to_judgment: number | null;
  pocso_cases: number;
  fast_track_cases: number;
}

export interface PlatformStats {
  total_cases: number;
  total_convictions: number;
  states_covered: number;
  avg_conviction_rate: number;
  total_pocso: number;
  total_fast_track: number;
}
