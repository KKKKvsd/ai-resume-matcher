import axios from "axios";
import { getToken, logoutAndRedirect, setToken } from "./auth";
import {
  type CreateSessionResponse,
  type AgentResponse,
  type ApiResponse,
  type FollowUpResponse,
  type Job,
  type LoginResponse,
  type MatchResult,
  type Resume,
  type User,
  type AgentMemoryInfo,
} from "../types/api";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

export const api = axios.create({
  baseURL: API_BASE_URL,
});

api.interceptors.request.use((config) => {
  const token = getToken();

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      logoutAndRedirect();
    }

    return Promise.reject(error);
  }
);

export async function registerUser(payload: {
  username: string;
  email: string;
  password: string;
}) {
  const res = await api.post<ApiResponse<User>>(
    "/api/v1/users/register",
    payload
  );
  return res.data.data;
}

export async function loginUser(payload: {
  email: string;
  password: string;
}) {
  const res = await api.post<ApiResponse<LoginResponse>>(
    "/api/v1/users/login",
    payload
  );

  setToken(res.data.data.access_token);

  return res.data.data;
}

export async function getMe() {
  const res = await api.get<ApiResponse<User>>("/api/v1/users/me");
  return res.data.data;
}

export async function getResumes() {
  const res = await api.get<ApiResponse<Resume[]>>("/api/v1/resumes");
  return res.data.data;
}

export async function uploadResume(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  const res = await api.post<ApiResponse<Resume>>(
    "/api/v1/resumes/upload",
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );

  return res.data.data;
}

export async function getJobs() {
  const res = await api.get<ApiResponse<Job[]>>("/api/v1/jobs");
  return res.data.data;
}

export async function createJob(payload: {
  title: string;
  company_name?: string;
  content: string;
  source?: string;
}) {
  const res = await api.post<ApiResponse<Job>>("/api/v1/jobs", payload);
  return res.data.data;
}

export async function analyzeMatch(payload: {
  resume_id: number;
  job_id: number;
}) {
  const res = await api.post<ApiResponse<MatchResult>>(
    "/api/v1/match/analyze",
    payload
  );
  return res.data.data;
}

export async function getMatchResults() {
  const res = await api.get<ApiResponse<MatchResult[]>>(
    "/api/v1/match/results"
  );
  return res.data.data;
}

export async function getMatchResultDetail(resultId: number) {
    const res = await api.get<ApiResponse<MatchResult>>(
        `/api/v1/match/results/${resultId}`
    );

    return res.data.data;
}

export async function askFollowUp(question: string) {
  const res = await api.post<ApiResponse<FollowUpResponse>>(
    "/api/v1/match/follow-up",
    { question }
  );
  
  return res.data.data;
}

export async function runAgent(query: string, sessionId?: string | null) {
  const res = await api.post<ApiResponse<AgentResponse>>(
    "/api/v1/match/agent",
    {
      query,
      session_id: sessionId ?? null,
    }
  );
  return res.data.data;
}

export async function createAgentSession() {
  const res = await api.post<ApiResponse<CreateSessionResponse>>(
    "/api/v1/match/agent/session"
  );
  return res.data.data;
}

export type AgentStreamEvent =
  | { type: "status"; data: { message: string } }
  | { type: "plan"; data: any }
  | { type: "tool_start"; data: { step_id: number; tool_name: string; reason: string } }
  | { type: "tool_done"; data: { step_id: number; tool_name: string; status: string; output_preview?: any; error?: string } }
  | { type: "token"; data: { text: string } }
  | { type: "memory"; data: AgentMemoryInfo }
  | { type: "warning"; data: { message: string } }
  | { type: "error"; data: { message: string; detail?: string } }
  | { type: "done"; data: any };

/**
 * 调用流式 Agent。回调形式接收事件。
 * 内部用 fetch + ReadableStream(EventSource 不支持 POST + 自定义 header)
 */
export async function streamAgent(
  query: string,
  sessionId: string | null | undefined,
  onEvent: (evt: AgentStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const token = localStorage.getItem("access_token");
  const baseUrl = API_BASE_URL;

  const response = await fetch(`${baseUrl}/api/v1/match/agent/stream`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: token ? `Bearer ${token}` : "",
    },
    body: JSON.stringify({ query, session_id: sessionId ?? null }),
    signal,
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }

  if (!response.body) {
    throw new Error("Streaming not supported by this browser");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";


  while (true) {
    const { value, done } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // SSE message 以空行分隔
    const messages = buffer.split("\n\n");
    // 最后一个可能不完整,保留到下一轮
    buffer = messages.pop() ?? "";

    for (const msg of messages) {
      if (!msg.trim()) continue;
      // 一个 message 可能有多行 data: ...,合并起来
      const dataLines = msg
        .split("\n")
        .filter((l) => l.startsWith("data: "))
        .map((l) => l.slice(6));

      if (dataLines.length === 0) continue;

      const fullData = dataLines.join("\n");
      try {
        const event = JSON.parse(fullData) as AgentStreamEvent;
        onEvent(event);
      } catch (e) {
        console.warn("Failed to parse SSE event:", fullData, e);
      }
    }
  }
}