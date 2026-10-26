import { useEffect, useState } from "react";

import { api } from "../api";

type Gathering = {
  id: number;
  title: string | null;
  reason: string;
  event_time: string;
  need_static: boolean;
  event_kind: string;
  channel_id: number;
};

export default function Gatherings() {
  const [events, setEvents] = useState<Gathering[]>([]);

  useEffect(() => {
    void api<{ gatherings: Gathering[] }>("/api/gatherings")
      .then((data) => setEvents(data.gatherings))
      .catch(() => setEvents([]));
  }, []);

  return (
    <section className="panel">
      <h1>Сборы · Akiyama</h1>
      {events.length ? (
        <ul className="event-list">
          {events.map((event) => (
            <li className="event" key={event.id}>
              <div className="event-time">{event.event_time.replace("T", " ").slice(0, 16)}</div>
              <div>
                <div className="event-title">{event.title || "Сбор"}</div>
                <div>{event.reason}</div>
                <div className="event-meta">
                  {event.event_kind === "vzp" ? "VZP" : "Общий"} · требуется статик: {event.need_static ? "да" : "нет"}
                </div>
              </div>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted">Нет активных сборов.</p>
      )}
    </section>
  );
}
