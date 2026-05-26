import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Zap, Mail, Lock, User, AlertCircle, Loader2, Eye, EyeOff } from "lucide-react";
import { api } from "../api/client";
import "./LoginPage.css";

export default function LoginPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState("login");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  // Состояние для отображения пароля (глазок)
  const [showPassword, setShowPassword] = useState(false);

  const [loginForm, setLoginForm] = useState({ email: "", password: "" });
  const [regForm, setRegForm] = useState({ email: "", password: "", full_name: "" });

  // Функция перевода серверных ошибок
  const getRussianErrorMessage = (msg) => {
    if (!msg) return "Произошла непредвиденная ошибка";
    const lowerMsg = msg.toLowerCase();
    
    if (lowerMsg.includes("invalid") || lowerMsg.includes("credentials") || lowerMsg.includes("password")) {
      return "Неверный email или пароль";
    }
    if (lowerMsg.includes("not found") || lowerMsg.includes("user does not exist")) {
      return "Пользователь с таким email не найден";
    }
    if (lowerMsg.includes("already exists") || lowerMsg.includes("registered")) {
      return "Пользователь с таким email уже зарегистрирован";
    }
    if (lowerMsg.includes("network") || lowerMsg.includes("fetch")) {
      return "Ошибка сети. Проверьте подключение";
    }
    return msg;
  };

  const switchTab = (newTab) => {
    setTab(newTab);
    setError("");
    setShowPassword(false);
  };

  const handleInputChange = (type, field, value) => {
    if (error) setError(""); 
    if (type === "login") {
      setLoginForm((prev) => ({ ...prev, [field]: value }));
    } else {
      setRegForm((prev) => ({ ...prev, [field]: value }));
    }
  };

  // Валидация email перед отправкой (замена браузерной)
  const validateEmail = (email) => {
    const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return re.test(String(email).toLowerCase());
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (loading) return;

    if (!validateEmail(loginForm.email)) {
      setError("Пожалуйста, введите корректный адрес электронной почты (например, user@example.com)");
      return;
    }

    setLoading(true);
    try {
      const tokens = await api.auth.login(loginForm);
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      setError(""); 
      navigate("/");
    } catch (err) {
      const systemError = err.response?.data?.detail || err.message || "";
      setError(getRussianErrorMessage(systemError));
    } finally {
      setLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    if (loading) return;

    if (!validateEmail(regForm.email)) {
      setError("Пожалуйста, введите корректный адрес электронной почты");
      return;
    }

    if (regForm.password.length < 8) {
      setError("Пароль должен содержать минимум 8 символов");
      return;
    }

    setLoading(true);
    try {
      await api.auth.register(regForm);
      const tokens = await api.auth.login({ email: regForm.email, password: regForm.password });
      localStorage.setItem("access_token", tokens.access_token);
      localStorage.setItem("refresh_token", tokens.refresh_token);
      setError("");
      navigate("/");
    } catch (err) {
      const systemError = err.response?.data?.detail || err.message || "";
      setError(getRussianErrorMessage(systemError));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-page__card-wrap card fade-in">
        
        <header className="login-page__header">
          <div className="login-page__logo-icon-wrap">
            <Zap size={30} strokeWidth={2.5} />
          </div>
          <h1 className="login-page__title">TestGen AI</h1>
          <p className="login-page__subtitle">
            Умная генерация тест-кейсов из вашей документации
          </p>
        </header>

        <div className="login-page__tabs">
          <button
            type="button"
            className={`login-page__tab ${tab === "login" ? "login-page__tab--active" : ""}`}
            onClick={() => switchTab("login")}
            disabled={loading}
          >
            Войти
          </button>
          <button
            type="button"
            className={`login-page__tab ${tab === "register" ? "login-page__tab--active" : ""}`}
            onClick={() => switchTab("register")}
            disabled={loading}
          >
            Регистрация
          </button>
        </div>

        {/* Контейнер кастомной ошибки */}
        <div className={`login-page__error-container ${error ? "login-page__error-container--active" : ""}`}>
          {error && (
            <div className="login-page__error">
              <AlertCircle size={18} className="login-page__error-icon" />
              <span className="login-page__error-text">{error}</span>
            </div>
          )}
        </div>

        {tab === "login" ? (
          <form onSubmit={handleLogin} noValidate className="login-page__form">
            <div className="login-page__field">
              <label className="login-page__label">Электронная почта</label>
              <div className="input-icon-wrap">
                <Mail size={16} className="input-icon" />
                <input
                  className="lp-input"
                  type="email" 
                  required
                  disabled={loading}
                  placeholder="name@company.com"
                  value={loginForm.email}
                  onChange={(e) => handleInputChange("login", "email", e.target.value)}
                />
              </div>
            </div>

            <div className="login-page__field">
              <label className="login-page__label">Пароль</label>
              <div className="input-icon-wrap">
                <Lock size={16} className="input-icon" />
                <input
                  className="lp-input"
                  type={showPassword ? "text" : "password"} 
                  required
                  disabled={loading}
                  placeholder="••••••••"
                  value={loginForm.password}
                  onChange={(e) => handleInputChange("login", "password", e.target.value)}
                />
                <button
                  type="button"
                  className="input-eye-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={loading}
                  title={showPassword ? "Скрыть пароль" : "Показать пароль"}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button type="submit" className="login-page__submit-btn" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 size={18} className="spinner-rotate" />
                  <span>Проверка...</span>
                </>
              ) : (
                "Открыть Дашборд"
              )}
            </button>
          </form>
        ) : (
          <form onSubmit={handleRegister} noValidate className="login-page__form">
            <div className="login-page__field">
              <label className="login-page__label">Ваше имя</label>
              <div className="input-icon-wrap">
                <User size={16} className="input-icon" />
                <input
                  className="lp-input"
                  type="text" 
                  required 
                  minLength={2}
                  disabled={loading}
                  placeholder="Алексей Петров"
                  value={regForm.full_name}
                  onChange={(e) => handleInputChange("register", "full_name", e.target.value)}
                />
              </div>
            </div>

            <div className="login-page__field">
              <label className="login-page__label">Электронная почта</label>
              <div className="input-icon-wrap">
                <Mail size={16} className="input-icon" />
                <input
                  className="lp-input"
                  type="email" 
                  required
                  disabled={loading}
                  placeholder="name@company.com"
                  value={regForm.email}
                  onChange={(e) => handleInputChange("register", "email", e.target.value)}
                />
              </div>
            </div>

            <div className="login-page__field">
              <label className="login-page__label">Придумайте пароль</label>
              <div className="input-icon-wrap">
                <Lock size={16} className="input-icon" />
                <input
                  className="lp-input"
                  type={showPassword ? "text" : "password"} 
                  required 
                  disabled={loading}
                  placeholder="Минимум 8 символов"
                  value={regForm.password}
                  onChange={(e) => handleInputChange("register", "password", e.target.value)}
                />
                <button
                  type="button"
                  className="input-eye-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  disabled={loading}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button type="submit" className="login-page__submit-btn" disabled={loading}>
              {loading ? (
                <>
                  <Loader2 size={18} className="spinner-rotate" />
                  <span>Создание...</span>
                </>
              ) : (
                "Зарегистрироваться"
              )}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}