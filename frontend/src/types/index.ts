export type Role = "admin" | "employee";
export type UserStatus = "pending" | "active" | "inactive";

// Curated job designations offered in the employee forms and the AI
// recommendation picker. Stored free-form on the backend, so this list can grow
// without a migration.
export const DESIGNATIONS = [
  "Software Engineer",
  "Senior Software Engineer",
  "Tech Lead",
  "Engineering Manager",
  "Frontend Developer",
  "Backend Developer",
  "Full Stack Developer",
  "QA Engineer",
  "Automation Test Engineer",
  "DevOps Engineer",
  "Cloud Engineer",
  "Data Engineer",
  "Data Scientist",
  "Machine Learning Engineer",
  "UI/UX Designer",
  "Business Analyst",
  "Product Manager",
  "Project Manager",
  "Scrum Master",
  "Database Administrator",
  "System Administrator",
  "Security Engineer",
  "Support Engineer",
  "Intern / Trainee",
] as const;

export interface DepartmentBrief {
  id: number;
  name: string;
}

export interface User {
  id: number;
  first_name: string;
  last_name: string;
  username: string;
  email: string;
  employee_id?: string | null;
  designation?: string | null;
  status: UserStatus;
  is_active: boolean;
  role: Role;
  department?: DepartmentBrief | null;
  last_login_at?: string | null;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface Department {
  id: number;
  name: string;
  description?: string | null;
  is_active: boolean;
  created_at: string;
}

export interface Group {
  id: number;
  name: string;
  description?: string | null;
  is_active: boolean;
  member_count: number;
  created_at: string;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export type CourseType = "mandatory" | "optional";
export type CourseStatus = "draft" | "published" | "archived";
export type DocumentStatus = "uploaded" | "processing" | "processed" | "failed";

export interface CourseDocument {
  id: number;
  original_filename: string;
  file_type: string;
  content_type?: string | null;
  size_bytes: number;
  status: DocumentStatus;
  processing_error?: string | null;
  text_chars: number;
  source_url?: string | null;
  created_at: string;
}

export interface Course {
  id: number;
  name: string;
  description?: string | null;
  category?: string | null;
  trainer?: string | null;
  course_type: CourseType;
  status: CourseStatus;
  start_date?: string | null;
  end_date?: string | null;
  has_quiz: boolean;
  passing_percentage: number;
  quiz_question_count: number;
  allow_retry: boolean;
  retry_count: number;
  thumbnail_path?: string | null;
  document_count: number;
  is_expired: boolean;
  published_at?: string | null;
  created_at: string;
}

export interface CourseDetail extends Course {
  documents: CourseDocument[];
}

export interface TrendingCourse {
  title: string;
  description?: string | null;
  category?: string | null;
  level: string;
  why?: string | null;
  skills: string[];
}

export interface TrendingRecommendations {
  items: TrendingCourse[];
  focus?: string | null;
  designation?: string | null;
  level?: string | null;
  source: "ai" | "fallback";
}

export type EnrollmentStatus =
  | "not_started"
  | "in_progress"
  | "quiz_pending"
  | "completed"
  | "failed"
  | "overdue"
  | "expired";

export type AssignmentTargetType = "all" | "department" | "group" | "individual";

export interface AssignResult {
  assigned: number;
  already_assigned: number;
  total_targeted: number;
  message: string;
}

export interface Enrollment {
  id: number;
  status: EnrollmentStatus;
  best_score?: number | null;
  attempts_used: number;
  assigned_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  user: {
    id: number;
    first_name: string;
    last_name: string;
    username: string;
    email: string;
    department?: string | null;
  };
}

export interface AppNotification {
  id: number;
  type: string;
  title: string;
  message: string;
  course_id?: number | null;
  is_read: boolean;
  email_status: string;
  created_at: string;
}

export interface Certificate {
  id: number;
  certificate_number: string;
  course_id: number;
  score?: number | null;
  issued_at: string;
}

export interface CertificateVerify {
  valid: boolean;
  certificate_number?: string;
  employee_name?: string;
  course_name?: string;
  score?: number | null;
  issued_at?: string;
}

export type QuestionType = "mcq" | "true_false" | "scenario";
export type Difficulty = "easy" | "medium" | "hard";

export interface QuizQuestionView {
  answer_id: number;
  question_id: number;
  question_type: QuestionType;
  difficulty: Difficulty;
  question_text: string;
  options: string[];
  display_order: number;
}

export interface QuizView {
  attempt_id: number;
  course_id: number;
  course_name: string;
  status: string;
  total_questions: number;
  passing_percentage: number;
  attempt_number: number;
  started_at: string;
  questions: QuizQuestionView[];
}

export interface AnswerReview {
  question_text: string;
  options: string[];
  selected?: string | null;
  correct_answer: string;
  is_correct: boolean;
  explanation?: string | null;
  topic?: string | null;
}

export interface QuizResult {
  attempt_id: number;
  course_id: number;
  total_questions: number;
  correct_count: number;
  score_percentage: number;
  passing_percentage: number;
  passed: boolean;
  status: string;
  submitted_at?: string | null;
  can_retry: boolean;
  attempts_used: number;
  max_attempts: number;
  review: AnswerReview[];
}

export interface QuizAttemptSummary {
  attempt_id: number;
  attempt_number: number;
  status: string;
  score_percentage?: number | null;
  passed?: boolean | null;
  total_questions: number;
  correct_count: number;
  submitted_at?: string | null;
}

export interface QuestionBankStats {
  total: number;
  difficulty_breakdown: Record<string, number>;
  type_breakdown: Record<string, number>;
  generated_by: Record<string, number>;
}

export interface QuestionBankOut {
  id: number;
  question_type: QuestionType;
  difficulty: Difficulty;
  question_text: string;
  options: string[];
  correct_answer: string;
  explanation?: string | null;
  topic?: string | null;
  reference_section?: string | null;
  generated_by: string;
  is_active: boolean;
}

export interface GenerationResult {
  generated: number;
  total_in_bank: number;
  source: string;
  difficulty_breakdown: Record<string, number>;
  type_breakdown: Record<string, number>;
  message: string;
}

export interface MyCourse {
  course_id: number;
  name: string;
  description?: string | null;
  category?: string | null;
  course_type: CourseType;
  start_date?: string | null;
  end_date?: string | null;
  has_quiz: boolean;
  passing_percentage: number;
  quiz_question_count: number;
  document_count: number;
  status: EnrollmentStatus;
  best_score?: number | null;
  attempts_used: number;
  max_attempts: number;
  can_attempt_quiz: boolean;
  started_at?: string | null;
  completed_at?: string | null;
  is_overdue: boolean;
}
