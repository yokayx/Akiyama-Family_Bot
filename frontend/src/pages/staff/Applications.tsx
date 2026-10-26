import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useSearchParams } from "react-router-dom";

import { api } from "../../api";
import { useAuth } from "../../auth";

type Ticket = {
  id: number;
  channel_id: number;
  kind: string;
  status: string;
  handler_id: number | null;
  created_at: string | null;
  applicant_label: string;
};

export default function StaffApplications() {
  const { user, loading } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [error, setError] = useState<string | null>(null);

  const status = searchParams.get("status") || "open";
  const kind = searchParams.get("kind") || "";

  const load = useCallback(async () => {
    try {
      const query = `?status=${encodeURIComponent(status)}&kind=${encodeURIComponent(kind)}`;
      const data = await api<{ tickets: Ticket[] }>(`/api/staff/tickets${query}`);
      setTickets(data.tickets);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }, [status, kind]);

  useEffect(() => {
    if (user) void load();
  }, [user, load]);

  if (loading) return <p className="muted">Загрузка…</p>;
  if (!user) return <Navigate to="/staff/login" replace />;

  return (
    <section className="panel">
      <h1>Заявки</h1>
      {error && <p className="error-note">{error}</p>}
      <form className="filters" onSubmit={(e) => e.preventDefault()}>
        <select value={status} onChange={(e) => setSearchParams({ status: e.target.value, kind })}>
          <option value="open">открытые</option>
          <option value="claimed">в работе</option>
          <option value="all">все</option>
        </select>
        <select value={kind} onChange={(e) => setSearchParams({ status, kind: e.target.value })}>
          <option value="">все виды</option>
          <option value="main">Main</option>
          <option value="vzp">VZP</option>
        </select>
      </form>
      {tickets.length ? (
        <table className="table">
          <thead>
            <tr><th>#</th><th>Канал</th><th>Вид</th><th>Статус</th></tr>
          </thead>
          <tbody>
            {tickets.map((ticket) => (
              <tr key={ticket.id}>
                <td><Link to={`/staff/applications/${ticket.id}`}>{ticket.id}</Link></td>
                <td>{ticket.channel_id}</td>
                <td>{ticket.kind === "main" ? "Main" : "VZP"}</td>
                <td>
                  {ticket.status === "claimed" ? `в работе · ${ticket.handler_id}` : ticket.status}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="muted">Заявок нет.</p>
      )}
    </section>
  );
}
