export type EventCategory =
  | 'FIR_FILING'
  | 'INVESTIGATION'
  | 'MEDICAL'
  | 'ARREST'
  | 'BAIL'
  | 'CHARGESHEET'
  | 'COURT_PROCEEDINGS'
  | 'JUDGMENT'
  | 'APPEAL'
  | 'COMPENSATION'
  | 'ADMINISTRATIVE'
  | 'MEDIA_COVERAGE';

export type ModerationStatus = 'PENDING' | 'APPROVED' | 'REJECTED' | 'ESCALATED' | 'AUTO_APPROVED';

export interface SourceAttribution {
  source_code: string;
  source_name: string;
  published_at: string | null;
  source_url: string;
}

export interface CaseEvent {
  id: string;
  case_id: string;
  event_type: string;
  event_category: EventCategory;
  event_date: string | null;
  event_date_approx: boolean;
  summary: string;
  court_name: string | null;
  order_number: string | null;
  ipc_sections_added: number[];
  ipc_sections_dropped: number[];
  sentence_years: number | null;
  bail_amount_inr: number | null;
  compensation_inr: number | null;
  source_attribution: SourceAttribution[];
  source_quote: string | null;
  confidence_score: number;
  moderation_status: ModerationStatus;
  is_milestone: boolean;
  created_at: string;
}

export interface TimelineStage {
  stage_name: string;
  status: 'COMPLETED' | 'ACTIVE' | 'PENDING';
  events: CaseEvent[];
  started_at: string | null;
  completed_at: string | null;
  duration_days: number | null;
}

export interface TimelineGap {
  from_event: string;
  to_event: string;
  actual_days: number;
  benchmark_days: number;
  significance: 'NORMAL' | 'DELAYED' | 'SEVERELY_DELAYED';
  legal_reference: string;
}

export interface Timeline {
  case_id: string;
  stages: TimelineStage[];
  gaps: TimelineGap[];
  milestone_events: string[];
  computed_at: string;
}
