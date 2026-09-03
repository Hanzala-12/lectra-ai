/**
 * Central API client for the Lectra AI backend.
 * Base URL comes from VITE_API_BASE_URL (falls back to same-origin / proxy).
 */

const API_BASE = ((import.meta as any).env?.VITE_API_BASE_URL || '').trim();

export function buildUrl(path: string): string {
  if (!path) return path;
  if (path.startsWith('http://') || path.startsWith('https://')) return path;
  if (API_BASE) return `${API_BASE.replace(/\/$/, '')}${path}`;
  return path;
}

async function req<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(buildUrl(path), {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      detail = body.detail || body.error || detail;
    } catch {
      /* ignore */
    }
    const err = new Error(detail) as Error & { status?: number };
    err.status = res.status;
    throw err;
  }
  return res.json() as Promise<T>;
}

// ---------- types ----------
export type LectureSummary = {
  id: string;
  title: string;
  created_at: number;
  duration?: number;
  has_notes: boolean;
  has_quiz: boolean;
  has_schedule: boolean;
  has_evaluation: boolean;
  word_count: number;
  quiz_attempts: number;
  best_score: number | null;
};

export type TranscriptSegment = {
  start: number;
  end: number;
  text: string;
  speaker?: string | null;
};

export type Lecture = {
  id: string;
  title: string;
  created_at: number;
  transcript_text: string;
  transcript_segments: TranscriptSegment[];
  diarization: any[];
  metadata: Record<string, any>;
  notes: string | null;
  quiz: QuizQuestion[] | null;
  schedule: Schedule | null;
  evaluation: Evaluation | null;
  chat_history: { question: string; answer: string }[];
};

export type QuizQuestion = {
  question: string;
  options: string[];
  answer_index: number;
  explanation: string;
};

export type Schedule = {
  plan: { day: number; focus: string; tasks: string[]; est_minutes: number }[];
  tips: string[];
};

export type Evaluation = {
  main_topics: string[];
  difficulty: string;
  estimated_study_minutes: number;
  prerequisites: string[];
  comprehension_questions: string[];
  summary: string;
};

export type ChatResponse = {
  answer: string;
  sources: { text: string; score: number }[];
};

export type GradeResult = {
  score: number;
  correct: number;
  total: number;
  breakdown: {
    question: string;
    your_answer: number | null;
    correct_answer: number;
    is_correct: boolean;
    explanation: string;
  }[];
};

// ---------- endpoints ----------
export const api = {
  llmStatus: () => req<{ configured: boolean; model: string | null }>('/api/llm-status'),

  library: () => req<{ lectures: LectureSummary[] }>('/api/library'),
  getLecture: (id: string) => req<Lecture>(`/api/lecture/${id}`),
  deleteLecture: (id: string) =>
    req<{ deleted: boolean }>(`/api/lecture/${id}`, { method: 'DELETE' }),

  notes: (id: string, refresh = false) =>
    req<{ notes: string; cached: boolean }>(
      `/api/lecture/${id}/notes?refresh=${refresh}`,
      { method: 'POST' },
    ),

  quiz: (id: string, num_questions = 5, refresh = false) =>
    req<{ quiz: QuizQuestion[]; cached: boolean }>(
      `/api/lecture/${id}/quiz?refresh=${refresh}`,
      { method: 'POST', body: JSON.stringify({ num_questions }) },
    ),

  gradeQuiz: (id: string, answers: number[]) =>
    req<GradeResult>(`/api/lecture/${id}/quiz/grade`, {
      method: 'POST',
      body: JSON.stringify({ answers }),
    }),

  schedule: (id: string, days = 7, refresh = false) =>
    req<{ schedule: Schedule; cached: boolean }>(
      `/api/lecture/${id}/schedule?refresh=${refresh}`,
      { method: 'POST', body: JSON.stringify({ days }) },
    ),

  evaluate: (id: string, refresh = false) =>
    req<{ evaluation: Evaluation; cached: boolean }>(
      `/api/lecture/${id}/evaluate?refresh=${refresh}`,
      { method: 'POST' },
    ),

  chat: (id: string, question: string, top_k = 4) =>
    req<ChatResponse>(`/api/lecture/${id}/chat`, {
      method: 'POST',
      body: JSON.stringify({ question, top_k }),
    }),
};
