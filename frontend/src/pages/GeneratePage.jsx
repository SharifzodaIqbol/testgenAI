import { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ChevronLeft, Zap, AlertCircle, CheckCircle2 } from "lucide-react";
import { api } from "../api/client";
import "./GeneratePage.css";

const CASE_TYPES = [
  { value: "functional",  label: "Функциональные" },
  { value: "negative",    label: "Негативные" },
  { value: "boundary",    label: "Граничные" },
  { value: "performance", label: "Производительность" },
  { value: "security",    label: "Безопасность" },
];

const STATUS_LABEL = {
  pending:    "В очереди...",
  processing: "Генерируем тест-кейсы...",
  completed:  "Готово!",
  failed:     "Ошибка генерации",
};

export default function GeneratePage() {
  const { projectId, docId } = useParams();
  const navigate = useNavigate();
  const wsRef = useRef(null);

  const [form, setForm] = useState({
    num_cases: 10,
    case_types: ["functional", "negative"],
    focus_area: "",
    language: "ru",
    suite_name: "",
  });

  const [taskId, setTaskId] = useState(null);
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState(null);
  const [suiteId, setSuiteId] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!taskId) return;
    const ws = new WebSocket(api.generation.wsUrl(taskId));
    wsRef.current = ws;
    ws.onmessage = (evt) => {
      const data = JSON.parse(evt.data);
      setProgress(data.progress ?? 0);
      setStatus(data.status);
      if (data.suite_id) setSuiteId(data.suite_id);
      if (data.error) setError(data.error);
    };
    ws.onerror = () => setError("Ошибка WebSocket-соединения");
    return () => ws.close();
  }, [taskId]);

  const toggleType = (type) => {
    setForm((f) => ({
      ...f,
      case_types: f.case_types.includes(type)
        ? f.case_types.filter((t) => t !== type)
        : [...f.case_types, type],
    }));
  };

  const setCount = (delta) => {
    setForm((f) => ({
      ...f,
      num_cases: Math.max(1, Math.min(50, f.num_cases + delta)),
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (form.case_types.length === 0) {
      setError("Выберите хотя бы один тип тест-кейсов");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const task = await api.generation.start({
        document_id: parseInt(docId),
        ...form,
      });
      setTaskId(task.id);
      setStatus("pending");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const barColor =
    status === "failed" ? "#ef4444" : status === "completed" ? "#22c55e" : "#6366f1";

  return (
    <div className="generate-page">
      <button className="generate-page__back" onClick={() => navigate(`/projects/${projectId}`)}>
        <ChevronLeft size={14} /> Назад к проекту
      </button>

      <h1 className="generate-page__title">Генерация тест-кейсов</h1>
      <p className="generate-page__sub">
        Настрой параметры — LLM создаст детальные тест-кейсы из документа
      </p>

      {!taskId ? (
        <form onSubmit={handleSubmit} className="gen-form">
          <div className="gen-form__section">
            <label className="label">Количество тест-кейсов</label>
            <div className="num-input-wrap">
              <button type="button" className="num-btn" onClick={() => setCount(-1)}>−</button>
              <input
                type="number" min={1} max={50}
                value={form.num_cases}
                onChange={(e) => setForm({ ...form, num_cases: parseInt(e.target.value) || 1 })}
              />
              <button type="button" className="num-btn" onClick={() => setCount(+1)}>+</button>
            </div>
          </div>

          <div className="gen-form__section">
            <label className="label">Типы тест-кейсов</label>
            <div className="type-pills">
              {CASE_TYPES.map(({ value, label }) => (
                <button
                  key={value} type="button"
                  className={`type-pill ${form.case_types.includes(value) ? "type-pill--active" : ""}`}
                  onClick={() => toggleType(value)}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div className="gen-form__section">
            <label className="label">
              Фокус на области{" "}
              <span style={{ fontWeight: 400, color: "var(--color-text-muted)" }}>(опционально)</span>
            </label>
            <input
              className="input"
              type="text"
              placeholder="Например: авторизация, оформление заказа, API..."
              value={form.focus_area}
              onChange={(e) => setForm({ ...form, focus_area: e.target.value })}
            />
          </div>

          <div className="gen-form__row">
            <div className="gen-form__section">
              <label className="label">Язык</label>
              <select
                className="input"
                value={form.language}
                onChange={(e) => setForm({ ...form, language: e.target.value })}
              >
                <option value="ru">Русский</option>
                <option value="en">English</option>
              </select>
            </div>
            <div className="gen-form__section">
              <label className="label">
                Название suite{" "}
                <span style={{ fontWeight: 400, color: "var(--color-text-muted)" }}>(опционально)</span>
              </label>
              <input
                className="input"
                type="text"
                placeholder="Авто"
                value={form.suite_name}
                onChange={(e) => setForm({ ...form, suite_name: e.target.value })}
              />
            </div>
          </div>

          {error && (
            <div className="error-banner">
              <AlertCircle size={14} /> {error}
            </div>
          )}

          <button type="submit" className="gen-submit" disabled={loading}>
            {loading ? <span className="spinner" /> : <Zap size={16} />}
            {loading ? "Запускаем..." : "Начать генерацию"}
          </button>
        </form>
      ) : (
        <div className="progress-panel card fade-in">
          {status === "completed" ? (
            <CheckCircle2 size={52} style={{ color: "var(--green-500)" }} />
          ) : status === "failed" ? (
            <AlertCircle size={52} style={{ color: "var(--red-500)" }} />
          ) : (
            <div style={{ display: "flex", gap: 6 }}>
              <span className="progress-dot" />
              <span className="progress-dot" />
              <span className="progress-dot" />
            </div>
          )}

          <div className="progress-status">{STATUS_LABEL[status] || "Обработка..."}</div>

          <div style={{ width: "100%" }}>
            <div className="progress-bar-wrap">
              <div className="progress-bar" style={{ width: `${progress}%`, background: barColor }} />
            </div>
            <p className="progress-pct" style={{ marginTop: 8 }}>{progress}%</p>
          </div>

          {error && (
            <div className="error-banner" style={{ width: "100%", boxSizing: "border-box" }}>
              <AlertCircle size={14} /> {error}
            </div>
          )}

          {status === "completed" && suiteId && (
            <button
              className="btn btn-primary btn-lg"
              onClick={() => navigate(`/projects/${projectId}`)}
            >
              Посмотреть результаты →
            </button>
          )}

          {status === "failed" && (
            <button
              className="btn btn-secondary"
              onClick={() => { setTaskId(null); setStatus(null); setProgress(0); setError(""); }}
            >
              Попробовать снова
            </button>
          )}
        </div>
      )}
    </div>
  );
}
