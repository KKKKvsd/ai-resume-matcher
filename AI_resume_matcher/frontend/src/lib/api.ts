import axios from "axios";
import { getToken, logoutAndRedirect, setToken } from "./auth";
import type {
  AgentResponse,
  ApiResponse,
  FollowUpResponse,
  Job,
  LoginResponse,
  MatchResult,
  Resume,
  User,
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

export async function runAgent(query: string) {
  const res = await api.post<ApiResponse<AgentResponse>>(
    "/api/v1/match/agent",
    { query }
  );
  return res.data.data;
}