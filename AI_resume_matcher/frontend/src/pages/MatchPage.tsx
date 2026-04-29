import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, RefreshCw } from "lucide-react";
import { analyzeMatch, getJobs, getResumes } from "../lib/api";
import type { Job, Resume } from "../types/api";
import PageHeader from "../components/common/PageHeader";
import LoadingCard from "../components/common/LoadingCard";
import ErrorCard from "../components/common/ErrorCard";
import ResumeUploader from "../components/match/ResumeUploader";
import ResumeSelector from "../components/match/ResumeSelector";
import JobEditor from "../components/match/JobEditor";
import JobSelector from "../components/match/JobSelector";
import AnalyzePanel from "../components/match/AnalyzePanel";

type Props = {
  onBack?: () => void;
};

export default function MatchPage({ onBack }: Props) {
  const navigate = useNavigate();

  const [resumes, setResumes] = useState<Resume[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [selectedResumeId, setSelectedResumeId] = useState<number | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<number | null>(null);

  const [loadingData, setLoadingData] = useState(true);
  const [dataError, setDataError] = useState("");
  const [analyzing, setAnalyzing] = useState(false);
  const [analyzeError, setAnalyzeError] = useState("");

  async function loadData() {
    try {
      setLoadingData(true);
      setDataError("");

      const [resumeList, jobList] = await Promise.all([getResumes(), getJobs()]);

      setResumes(Array.isArray(resumeList) ? resumeList : []);
      setJobs(Array.isArray(jobList) ? jobList : []);

      if (!selectedResumeId && resumeList[0]) {
        setSelectedResumeId(resumeList[0].id);
      }

      if (!selectedJobId && jobList[0]) {
        setSelectedJobId(jobList[0].id);
      }
    } catch (err: any) {
      console.error("加载匹配页面数据失败：", err);

      setDataError(
        err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "加载数据失败"
      );
    } finally {
      setLoadingData(false);
    }
  }

  useEffect(() => {
    loadData();
  }, []);

  function handleResumeUploaded(resume: Resume) {
    setResumes((current) => [resume, ...current]);
    setSelectedResumeId(resume.id);
  }

  function handleJobCreated(job: Job) {
    setJobs((current) => [job, ...current]);
    setSelectedJobId(job.id);
  }

  async function handleAnalyze() {
    if (!selectedResumeId || !selectedJobId) {
      setAnalyzeError("请先选择简历和岗位");
      return;
    }

    try {
      setAnalyzing(true);
      setAnalyzeError("");

      const result = await analyzeMatch({
        resume_id: selectedResumeId,
        job_id: selectedJobId,
      });

      navigate(`/results/${result.id}`);
    } catch (err: any) {
      console.error("匹配分析失败：", err);

      setAnalyzeError(
        err?.response?.data?.detail ||
          err?.response?.data?.message ||
          err?.message ||
          "匹配分析失败"
      );
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="简历岗位匹配分析"
        description="上传 PDF 简历，创建岗位 JD，然后生成 AI 匹配报告。分析成功后会自动进入结果详情页。"
        actions={
          <div className="flex flex-wrap gap-2">
            <button
              onClick={loadData}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border px-4 py-2 text-sm transition hover:bg-slate-50"
            >
              <RefreshCw className="h-4 w-4" />
              刷新
            </button>

            <button
              onClick={() => {
                if (onBack) {
                  onBack();
                } else {
                  navigate("/dashboard");
                }
              }}
              className="inline-flex items-center justify-center gap-2 rounded-2xl border px-4 py-2 text-sm transition hover:bg-slate-50"
            >
              <ArrowLeft className="h-4 w-4" />
              返回
            </button>
          </div>
        }
      />

      <div className="mt-6">
        {loadingData && <LoadingCard text="正在加载简历和岗位数据..." />}

        {!loadingData && dataError && <ErrorCard message={dataError} />}

        {!loadingData && !dataError && (
          <div className="grid gap-6 lg:grid-cols-[420px_1fr]">
            <aside className="space-y-6">
              <ResumeUploader onUploaded={handleResumeUploaded} />

              <ResumeSelector
                resumes={resumes}
                selectedResumeId={selectedResumeId}
                onSelect={setSelectedResumeId}
              />

              <AnalyzePanel
                selectedResumeId={selectedResumeId}
                selectedJobId={selectedJobId}
                analyzing={analyzing}
                onAnalyze={handleAnalyze}
              />

              {analyzeError && <ErrorCard message={analyzeError} />}
            </aside>

            <main className="space-y-6">
              <JobEditor onCreated={handleJobCreated} />

              <JobSelector
                jobs={jobs}
                selectedJobId={selectedJobId}
                onSelect={setSelectedJobId}
              />

              <section className="rounded-3xl bg-white p-6 shadow-sm">
                <h2 className="font-semibold text-slate-950">
                  当前工作流说明
                </h2>

                <div className="mt-5 space-y-4">
                  {[
                    "上传或选择一份 PDF 简历",
                    "创建或选择一个岗位 JD",
                    "点击开始分析",
                    "系统自动跳转到结果详情页",
                    "在详情页使用 Agent 继续追问",
                  ].map((item, index) => (
                    <div key={item} className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-slate-950 text-sm font-medium text-white">
                        {index + 1}
                      </div>

                      <div className="text-sm text-slate-600">{item}</div>
                    </div>
                  ))}
                </div>
              </section>
            </main>
          </div>
        )}
      </div>
    </div>
  );
}