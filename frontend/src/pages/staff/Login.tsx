import { useCallback } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { api } from "../../api";
import { useAuth } from "../../auth";

export default function StaffLogin() {
  const { user, loading } = useAuth();
  const navigate = useNavigate();

  const go = useCallback(async () => {
    try {
      const data = await api<{ url: string }>("/api/staff/login-url");
      window.location.href = data.url;
    } catch {
      navigate("/");
    }
  }, [navigate]);

  if (user) return <Navigate to="/staff" replace />;

  return (
    <section className="panel narrow">
      <h1>Вход для стаффа</h1>
      <p className="muted">Войдите через Discord — доступ только для членов семьи со staff-ролью.</p>
      <button className="btn" onClick={() => void go()} disabled={loading}>
        Войти через Discord →
      </button>
    </section>
  );
}
