import { useState, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Upload, FileText, Trash2, Zap, ChevronLeft,
  TestTube2, Download, CheckCircle2, AlertCircle,
  FileUp, Loader2,
} from "lucide-react";
import { api } from "../api/client";
import "./ProjectPage.css";

const CONTENT_TYPE_LABELS = {
  "application/pdf": "PDF",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "DOCX",
  "text/markdown": "MD",
  "text/plain": "TXT",
};

const PRIORITY_CONFIG = {
  low:      { label: "Низкий",      cls: "badge-slate" },
  medium:   { label: "Средний",     cls: "badge-indigo" },
  high:     { label: "Высокий",     cls: "badge-amber" },
  critical: { label: "Критический", cls: "badge-red" },
};

const TYPE_CONFIG = {
  functional:  { label: "Функц.",    cls: "badge-indigo" },
  negative:    { label: "Негатив.", cls: "badge-red" },
  boundary:    { label: "Граничн.", cls: "badge-amber" },
  performance: { label: "Произв.",  cls: "badge-slate" },
  security:    { label: "Безопасн.",cls: "badge-slate" },
};

/* ── TestCase detail card ─────────────────────────────────────────────── */
function TestCaseCard({ tc }) {
  const [open, setOpen] = useState(false);
  const pri = PRIORITY_CONFIG[tc.priority] || PRIORITY_CONFIG.medium;
  const typ = TYPE_CONFIG[tc.case_type] || TYPE_CONFIG.functional;

  return (
    <div className={`tc-card ${open ? "tc-card--open" : ""}`}>
      <div className="tc-card__header" onClick={() => setOpen((o) => !o)}>
        <div className="tc-card__badges">
          <span className={`badge ${pri.cls}`}>{pri.label}</span>
          <span className={`badge ${typ.cls}`}>{typ.label}</span>
          {tc.confidence_score >= 0.9 && (
            <span className="badge badge-green" title="Высокая уверенность LLM">
              <CheckCircle2 size={10} /> {Math.round(tc.confidence_score * 100)}%
            </span>
          )}
        </div>
        <h4 className="tc-card__title">{tc.title}</h4>
        <span className="tc-card__toggle">{open ? "▲" : "▼"}</span>
      </div>

      {open && (
        <div className="tc-card__body fade-in">
          {tc.description && <p className="tc-card__desc">{tc.description}</p>}

          {tc.preconditions && (
            <div className="tc-section">
              <span className="tc-section__label">Предусловия</span>
              <p>{tc.preconditions}</p>
            </div>
          )}

          {tc.steps.length > 0 && (
            <div className="tc-section">
              <span className="tc-section__label">Шаги</span>
              <ol className="tc-steps">
                {tc.steps.map((s, i) => (
                  <li key={i} className="tc-step">
                    <div className="tc-step__action">{s.step}</div>
                    <div className="tc-step__expected">→ {s.expected}</div>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {tc.expected_result && (
            <div className="tc-section">
              <span className="tc-section__label">Итоговый результат</span>
              <p className="tc-section__result">{tc.expected_result}</p>
            </div>
          )}

          {tc.tags.length > 0 && (
            <div className="tc-tags">
              {tc.tags.map((t) => (
                <span key={t} className="tc-tag">#{t}</span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Suite viewer ─────────────────────────────────────────────────────── */
function SuiteViewer({ suite, projectId }) {
  const queryClient = useQueryClient();
  const deleteMutation = useMutation({
    mutationFn: () => api.testCases.deleteSuite(suite.id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["suites", projectId] }),
  });

  return (
    <div className="suite card">
      <div className="suite__header">
        <div>
          <h3 className="suite__name">{suite.name}</h3>
          <span className="suite__count">{suite.test_cases.length} тест-кейсов</span>
        </div>
        <div className="suite__actions">
          {/* Просто вызываем функции из нашего api, передавая id и имя сьюта */}
          <button
            onClick={() => api.testCases.exportExcel(suite.id, suite.name)}
            className="btn btn-secondary btn-sm"
          >
            <Download size={13} /> Excel
          </button>
          <button
            onClick={() => api.testCases.exportJson(suite.id, suite.name)}
            className="btn btn-secondary btn-sm"
          >
            <Download size={13} /> JSON
          </button>
          <button
            className="btn btn-danger btn-sm"
            onClick={() => window.confirm("Удалить suite?") && deleteMutation.mutate()}
          >
            <Trash2 size={13} />
          </button>
        </div>
      </div>

      <div className="suite__cases">
        {suite.test_cases.map((tc) => (
          <TestCaseCard key={tc.id} tc={tc} />
        ))}
      </div>
    </div>
  );
}
/* ── Main page ────────────────────────────────────────────────────────── */
export default function ProjectPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const fileInputRef = useRef(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");

  const { data: project } = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => api.projects.list().then((list) => list.find((p) => p.id === Number(projectId))),
  });

  const { data: documents = [], isLoading: docsLoading } = useQuery({
    queryKey: ["documents", projectId],
    queryFn: () => api.documents.list(projectId),
  });

  const { data: suites = [], isLoading: suitesLoading } = useQuery({
    queryKey: ["suites", projectId],
    queryFn: () => api.testCases.suites(projectId),
  });

  const deleteDocMutation = useMutation({
    mutationFn: (id) => api.documents.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["documents", projectId] }),
  });

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError("");
    try {
      await api.documents.upload(projectId, file);
      queryClient.invalidateQueries({ queryKey: ["documents", projectId] });
    } catch (err) {
      setUploadError(err.message || "Ошибка загрузки");
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file) {
      const dt = new DataTransfer();
      dt.items.add(file);
      fileInputRef.current.files = dt.files;
      fileInputRef.current.dispatchEvent(new Event("change", { bubbles: true }));
    }
  };

  return (
    <div className="project-page">
      {/* Header */}
      <div className="page-header">
        <div className="page-header__left">
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => navigate("/")}
          >
            <ChevronLeft size={16} /> Назад
          </button>
          <div className="page-header__icon" style={{ background: "var(--indigo-50)", color: "var(--indigo-500)" }}>
            <TestTube2 size={18} />
          </div>
          <div>
            <h1 className="page-header__title">{project?.name || "Проект"}</h1>
            {project?.description && (
              <p className="page-header__sub">{project.description}</p>
            )}
          </div>
        </div>
      </div>

      <div className="project-page__body">
        {/* Left column — documents */}
        <div className="project-page__col">
          <div className="section-title">
            <FileText size={16} /> Документы
          </div>

          {/* Drop zone */}
          <div
            className="drop-zone card"
            onDrop={handleDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() => fileInputRef.current.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".pdf,.docx,.doc,.md,.txt"
              style={{ display: "none" }}
              onChange={handleUpload}
            />
            {uploading ? (
              <>
                <Loader2 size={28} className="drop-zone__icon drop-zone__icon--spin" />
                <span className="drop-zone__text">Загружаем и извлекаем текст...</span>
              </>
            ) : (
              <>
                <FileUp size={28} className="drop-zone__icon" />
                <span className="drop-zone__text">Перетащи файл или нажми</span>
                <span className="drop-zone__hint">PDF, DOCX, MD, TXT — до 10 МБ</span>
              </>
            )}
          </div>

          {uploadError && (
            <div className="error-banner">
              <AlertCircle size={14} /> {uploadError}
            </div>
          )}

          {/* Document list */}
          {docsLoading ? (
            <div className="loading-row"><span className="spinner" /> Загружаем...</div>
          ) : documents.length === 0 ? (
            <p className="empty-hint">Загрузи документ чтобы начать генерацию</p>
          ) : (
            <div className="doc-list">
              {documents.map((doc) => (
                <div key={doc.id} className="doc-item card">
                  <div className="doc-item__left">
                    <span className={`badge ${doc.content_type === "application/pdf" ? "badge-red" : "badge-indigo"}`}>
                      {CONTENT_TYPE_LABELS[doc.content_type] || "FILE"}
                    </span>
                    <div className="doc-item__info">
                      <span className="doc-item__name" title={doc.filename}>{doc.filename}</span>
                      <span className="doc-item__meta">~{doc.token_count.toLocaleString("ru")} токенов</span>
                    </div>
                  </div>
                  <div className="doc-item__actions">
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={() => navigate(`/projects/${projectId}/generate/${doc.id}`)}
                      title="Сгенерировать тест-кейсы"
                    >
                      <Zap size={13} /> Генерировать
                    </button>
                    <button
                      className="btn btn-ghost btn-sm"
                      onClick={() => window.confirm("Удалить документ?") && deleteDocMutation.mutate(doc.id)}
                      title="Удалить документ"
                    >
                      <Trash2 size={13} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Right column — suites */}
        <div className="project-page__col project-page__col--wide">
          <div className="section-title">
            <TestTube2 size={16} /> Тест-сьюты
          </div>

          {suitesLoading ? (
            <div className="loading-row"><span className="spinner" /> Загружаем...</div>
          ) : suites.length === 0 ? (
            <div className="empty-suites card">
              <TestTube2 size={40} strokeWidth={1} style={{ color: "var(--slate-300)" }} />
              <p>Тест-кейсы появятся здесь после генерации</p>
            </div>
          ) : (
            <div className="suites-list">
              {suites.map((suite) => (
                <SuiteViewer key={suite.id} suite={suite} projectId={projectId} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}