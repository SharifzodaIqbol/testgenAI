import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { FolderPlus, Folder, Trash2, ChevronRight, LayoutDashboard, X } from "lucide-react";
import { api } from "../api/client";
import "./DashboardPage.css";

function CreateProjectModal({ onClose, onCreate }) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await onCreate({ name, description });
      onClose();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal card fade-in" onClick={(e) => e.stopPropagation()}>
        <div className="modal__header">
          <h2 className="modal__title">Новый проект</h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose}><X size={16} /></button>
        </div>
        <form onSubmit={handleSubmit} className="modal__form">
          <div>
            <label className="label">Название проекта *</label>
            <input
              className="input" required autoFocus
              placeholder="Мой проект"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div>
            <label className="label">Описание</label>
            <textarea
              className="input"
              rows={3}
              placeholder="Краткое описание проекта..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              style={{ resize: "vertical" }}
            />
          </div>
          <div className="modal__actions">
            <button type="button" className="btn btn-secondary" onClick={onClose}>Отмена</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>
              {loading ? <span className="spinner" /> : "Создать проект"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showModal, setShowModal] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: api.projects.list,
  });

  const createMutation = useMutation({
    mutationFn: api.projects.create,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => api.projects.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["projects"] }),
    onSettled: () => setDeletingId(null),
  });

  const handleDelete = (e, id) => {
    e.stopPropagation();
    if (window.confirm("Удалить проект и все его данные?")) {
      setDeletingId(id);
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="dashboard">
      {/* Page header */}
      <div className="page-header">
        <div className="page-header__left">
          <div className="page-header__icon"><LayoutDashboard size={18} /></div>
          <div>
            <h1 className="page-header__title">Дашборд</h1>
            <p className="page-header__sub">Управляй проектами и документами</p>
          </div>
        </div>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>
          <FolderPlus size={16} /> Новый проект
        </button>
      </div>

      {/* Stats row */}
      <div className="dashboard__stats">
        <div className="stat-card card">
          <span className="stat-card__value">{projects.length}</span>
          <span className="stat-card__label">Проектов</span>
        </div>
        <div className="stat-card card">
          <span className="stat-card__value" style={{ color: "var(--indigo-500)" }}>∞</span>
          <span className="stat-card__label">Тест-кейсов</span>
        </div>
        <div className="stat-card card">
          <span className="stat-card__value" style={{ color: "var(--green-600)" }}>LLM</span>
          <span className="stat-card__label">LLaMA 3 70B</span>
        </div>
      </div>

      {/* Projects grid */}
      {isLoading ? (
        <div className="dashboard__loading">
          <span className="spinner" style={{ width: 28, height: 28 }} />
          <span>Загружаем проекты...</span>
        </div>
      ) : projects.length === 0 ? (
        <div className="dashboard__empty card">
          <Folder size={48} strokeWidth={1} style={{ color: "var(--slate-300)" }} />
          <p className="dashboard__empty-title">Пока нет проектов</p>
          <p className="dashboard__empty-sub">Создай первый проект и загрузи документацию</p>
          <button className="btn btn-primary" onClick={() => setShowModal(true)}>
            <FolderPlus size={16} /> Создать проект
          </button>
        </div>
      ) : (
        <div className="projects-grid">
          {projects.map((project) => (
            <div
              key={project.id}
              className="project-card card"
              onClick={() => navigate(`/projects/${project.id}`)}
            >
              <div className="project-card__header">
                <div className="project-card__icon">
                  <Folder size={18} />
                </div>
                <button
                  className="btn btn-ghost btn-sm project-card__delete"
                  onClick={(e) => handleDelete(e, project.id)}
                  disabled={deletingId === project.id}
                  title="Удалить проект"
                >
                  <Trash2 size={14} />
                </button>
              </div>
              <h3 className="project-card__name">{project.name}</h3>
              {project.description && (
                <p className="project-card__desc">{project.description}</p>
              )}
              <div className="project-card__footer">
                <span className="project-card__date">
                  {new Date(project.created_at).toLocaleDateString("ru-RU", {
                    day: "numeric", month: "short", year: "numeric",
                  })}
                </span>
                <ChevronRight size={16} style={{ color: "var(--slate-400)" }} />
              </div>
            </div>
          ))}
        </div>
      )}

      {showModal && (
        <CreateProjectModal
          onClose={() => setShowModal(false)}
          onCreate={createMutation.mutateAsync}
        />
      )}
    </div>
  );
}
