export type ApiResponse<T> = {
    code: number;
    message: string;
    data: T;
};

export type User = {
    id: number;
    username: string;
    email: string;
    created_at: string;
};

export type LoginResponse = {
    access_token: string;
    token_type: string;
};

export type Resume = {
    id: number;
    file_name: string;
    file_type: string;
    file_path?: string;
    raw_text: string | null;
    parsed_status: string;
    created_at: string;
};

export type Job = {
    id: number;
    title: string;
    company_name?: string | null;
    content: string;
    source?: string | null;
    created_at: string;
};

export type MatchResult = {
    id: number;
    resume_id: number;
    job_id: number;
    score: number | null;
    summary: string | null;

    strengths?: string[];
    weaknesses?: string[];
    suggestions?: string[];

    matched_keywords: string[];
    missing_keywords: string[];

    evidence?: Array<Record<string, unknown>>;
    model_name: string | null;
    analysis_mode: string | null;
    status: string;
    error_message?: string | null;
    created_at: string;
};

export type FollowUpResponse = {
    answer: string;
    based_on_result_id: number;
};

export type AgentMemoryInfo = {
    used_session_memory: boolean;
    used_longterm_memory: boolean;
    summary_compressed: boolean;
    session_id: string | null;
    tokens_estimate: number;
};

export type AgentResponse = {
    intent: string;
    final_answer: string | null;
    plan: Record<string, unknown>;
    steps: Array<Record<string, unknown>>;
    result: Record<string, unknown>;
    confidence: number | null;
    mode: string | null;
    warnings: string[];
    memory: AgentMemoryInfo | null;
};

export type CreateSessionResponse = {
    session_id: string;
};