export interface BoundingBox {
  page: number;
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface Entity {
  id: number;
  entity_type: string;
  extracted_text: string;
  confidence_score: number;
  bounding_box_coords: BoundingBox | null;
  requires_review: boolean;
  created_at: string;
}

export interface CaseUploadResponse {
  case_id: string;
  task_id: string;
  case_number: string;
  status: string;
}

export interface CaseStatusResponse {
  case_id: string;
  case_number: string;
  status: string;
  created_at: string;
  updated_at: string;
  error_message: string | null;
  entity_count: number;
  entities: Entity[];
}

export interface CaseSummary {
  case_id: string;
  case_number: string;
  subject?: string | null;
  court_name?: string | null;
  department?: string | null;
  assigned_officer?: {
    id: string;
    email: string;
    full_name: string;
    department: string;
    role: string;
  } | null;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  deadline?: string | null;
  error_message: string | null;
  entity_count: number;
}

export interface UpdateEntityPayload {
  extracted_value?: string;
  status: 'VERIFIED' | 'REJECTED';
}

export interface ActionPlan {
  [key: string]: any;
}

export interface DashboardStats {
  overdue_count: number;
  critical_count: number;
  verified_this_month: number;
  pending_verification: number;
  last_week_overdue_diff: number;
  verified_growth_percent: number;
}

export interface AuditLogEntry {
  id: string;
  case_id: string;
  case_number: string;
  extraction_id: string | null;
  action: string;
  actor_id: string;
  actor_email: string;
  actor_name: string;
  actor_role: string;
  old_value: string | null;
  new_value: string | null;
  reason: string | null;
  ip_address: string | null;
  created_at: string | null;
}

export interface UserSummary {
  id: string;
  email: string;
  full_name: string;
  department: string;
  role: string;
  is_active: boolean;
  created_at: string | null;
  last_login_at: string | null;
}

export interface ApiError {
  detail: string;
  status: number;
}
