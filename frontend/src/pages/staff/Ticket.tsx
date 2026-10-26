import { useCallback, useEffect, useState } from "react";
import { Link, Navigate, useParams } from "react-router-dom";

import { api } from "../../api";
import { useAuth } from "../../auth";

type Answer = { question?: string; answer?: string };

type TicketDetail = {
  id: number;
  channel_id: number;
  kind: string;
  status: string;
  handler_id: number | null;
  answers: Answer[];
  applicant_label: string;
  handler_label: string;
  created_at: string | null;
};

export default function StaffTicket() {
  const { ticketId } = useParams();
  const { user, loading } = useAuth();
  const [ticket, setTicket] = useState<TicketDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const load = useCallback(async () => {
    if (!ticketId) return;
    try {
      setTicket(await api<TicketDetail>(`/api/staff/tickets/${ticketId}`));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Ошибка");
    }
  }, [ticketId]);

  useEffect(() => {
    if (user) void load();
  }, [user, load]);

  const action = useCallback(
    async (path: string, body?: FormData) => {
      if (!ticketId) return;
      setBusy(true);
      try {
        const data = await api<{ ok: boolean; message: string }>(`/api/staff/tickets/${ticketId}/${path}`, {
          method: "POST",
          body: body ?? undefined,
        });
        if (!data.ok) setError(data.message);
        await load();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Ошибка");
      } finally {
        setBusy(false);
      }
    },
    [ticketId, load],
  );

  if (loading) return <p className="muted">Загрузка…</p>;
  if (!user) return <Navigate to="/staff/login" replace />;
  if (!ticket) return <p className="muted">{error || "Загрузка…"}</p>;

  return (
    <section className="panel">
      <h1>Заявка #{ticket.id}</h1>
      <p className="muted">
        Вид: {ticket.kind === "main" ? "Main" : "VZP"} · статус: {ticket.status} ·
        заявитель: {ticket.applicant_label} · взят: {ticket.handler_label}
      </p>
      <p className="muted">Канал: {ticket.channel_id} · создана: {ticket.created_at || "—"}</p>

      {ticket.answers.length ? (
        <table className="table answers">
          <tbody>
            {ticket.answers.map((answer, index) => (
              <tr key={index}>
                <th>{answer.question || "Вопрос"}</th>
                <td>{answer.answer || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="muted">Ответы пусты.</p>
      )}

      {error && <p className="error-note">{error}</p>}

      <div className="actions">
        {ticket.status === "open" && (
          <button className="btn" disabled={busy} onClick={() => void action("claim")}>
            Взять заявку
          </button>
        )}
        {ticket.status === "claimed" && (
          <>
            <button className="btn btn-ghost" disabled={busy} onClick={() => void action("release")}>
              Освободить
            </button>
            <button className="btn btn-success" disabled={busy} onClick={() => void action("accept")}>
              Принять
            </button>
            <input
              type="text"
              value={rejectReason}
              placeholder="Причина отказа"
              onChange={(e) => setRejectReason(e.target.value)}
              style={{ width: 240, padding: "8px 10px", borderRadius: 8, background: "var(--panel-2)", border: "1px solid var(--line)", color: "var(--text)" }}
            />
            <button
              className="btn btn-danger"
              disabled={busy || !rejectReason.trim()}
              onClick={() => {
                const body = new FormData();
                body.append("reason", rejectReason);
                void action("reject", body);
              }}
            >
              Отклонить
            </button>
          </>
        )}
      </div>

      <p className="muted"><Link to="/staff/applications">← Назад к заявкам</Link></p>
    </section>
  );
}
