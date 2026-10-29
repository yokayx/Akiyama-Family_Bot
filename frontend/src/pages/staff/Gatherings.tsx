import { useCallback, useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

import { api } from "../../api";
import { useAuth } from "../../auth";

type Gathering = {
  id: number;
  title: string | null;
  reason: string;
  event_time: string;
  need_static: boolean;
  event_kind: string;
  channel_id: number;
};

export default function StaffGatherings() {
  const { user, loading } = useAuth();
  const [events, setEvents] = useState<Gathering[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ kind: "general", title: "", reason: "", event_time: "", need_static: false });

  const load = useCallback(async () => {
    try {
      const data = await api<{ gatherings: Gathering[] }>("/api/staff/gatherings");
      setEvents(data.gatherings);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }, []);

  useEffect(() => {
    if (user) void load();
  }, [user, load]);

  const create = useCallback(async () => {
    if (!user) return;
    setBusy(true);
    const body = new FormData();
    body.append("kind", form.kind);
    body.append("title", form.title);
    body.append("reason", form.reason);
    body.append("event_time", form.event_time);
    if (form.need_static) body.append("need_static", "true");
    try {
      await api("/api/staff/gatherings", { method: "POST", body });
      setForm({ kind: "general", title: "", reason: "", event_time: "", need_static: false });
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    } finally {
      setBusy(false);
    }
  }, [user, form, load]);

  if (loading) return <p className="muted">Загрузка…</p>;
  if (!user) return <Navigate to="/staff/login" replace />;

  return (
    <>
      <section className="panel">
        <h1>Сборы</h1>
        {error && <p className="error-note">{error}</p>}
        {events.length ? (
          <ul className="event-list">
            {events.map((event) => (
              <li className="event" key={event.id}>
                <div className="event-time">{event.event_time.replace("T", " ").slice(0, 16)}</div>
                <div>
                  <div className="event-title">{event.title || "Сбор"}</div>
                  <div>{event.reason}</div>
                  <div className="event-meta">
                    {event.event_kind === "vzp" ? "VZP" : "Общий"} · статик: {event.need_static ? "да" : "нет"} ·
                    канал: {event.channel_id}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        ) : (
          <p className="muted">Нет активных сборов.</p>
        )}
      </section>

      <section className="panel">
        <h2>Создать сбор</h2>
        <div className="form-grid">
          <label>
            Тип
            <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}>
              <option value="general">Общий</option>
              <option value="vzp">VZP</option>
            </select>
          </label>
          <label>
            Заголовок
            <input type="text" value={form.title} placeholder="Мероприятие"
              onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </label>
          <label>
            Причина
            <input type="text" value={form.reason} placeholder="Зачем сбор" required
              onChange={(e) => setForm({ ...form, reason: e.target.value })} />
          </label>
          <label>
            Время (по Москве)
            <input type="datetime-local" value={form.event_time} required
              onChange={(e) => setForm({ ...form, event_time: e.target.value })} />
          </label>
          <label className="checkbox">
            <input type="checkbox" checked={form.need_static}
              onChange={(e) => setForm({ ...form, need_static: e.target.checked })} />
            Требуется статик при записи
          </label>
          <div className="actions">
            <button className="btn" disabled={busy || !form.reason || !form.event_time}
              onClick={() => void create()}>Создать</button>
          </div>
        </div>
      </section>
    </>
  );
}
