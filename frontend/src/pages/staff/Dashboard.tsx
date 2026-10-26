import { useEffect, useState } from "react";
import { Link, Navigate } from "react-router-dom";

import { api } from "../../api";
import { useAuth } from "../../auth";

export default function StaffDashboard() {
  const { user, loading, logout } = useAuth();
  const [openTickets, setOpenTickets] = useState(0);
  const [activeEvents, setActiveEvents] = useState(0);
  const [online, setOnline] = useState<number | null>(null);

  useEffect(() => {
    if (!user) return;
    void api<{ tickets: unknown[] }>("/api/staff/tickets?status=open")
      .then((data) => setOpenTickets(data.tickets.length))
      .catch(() => setOpenTickets(0));
    void api<{ gatherings: unknown[] }>("/api/staff/gatherings")
      .then((data) => setActiveEvents(data.gatherings.length))
      .catch(() => setActiveEvents(0));
    void api<{ online: number }>("/api/online")
      .then((data) => setOnline(data.online))
      .catch(() => setOnline(null));
  }, [user]);

  if (loading) return <p className="muted">Загрузка…</p>;
  if (!user) return <Navigate to="/staff/login" replace />;

  return (
    <section className="panel">
      <h1>Панель стаффа</h1>
      <p className="muted">Вы вошли как {user.name}</p>
      <div className="cards">
        <div className="card">
          <div className="card-title">Заявки</div>
          <div className="card-value"><Link to="/staff/applications?status=open">{openTickets}</Link></div>
          <div className="card-sub">открытые</div>
        </div>
        <div className="card">
          <div className="card-title">Сборы</div>
          <div className="card-value"><Link to="/staff/gatherings">{activeEvents}</Link></div>
          <div className="card-sub">активные</div>
        </div>
        <div className="card">
          <div className="card-title">Онлайн</div>
          <div className="card-value">{online === null ? "—" : online}</div>
          <div className="card-sub"><Link to="/online">→</Link></div>
        </div>
      </div>
      <div className="actions">
        <Link className="btn" to="/staff/gatherings">+ Создать сбор</Link>
        <button className="btn btn-ghost" onClick={() => void logout()}>Выйти</button>
      </div>
    </section>
  );
}
