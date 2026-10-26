import { useEffect, useState } from "react";

import { api } from "../api";

type RosterData = { unique_count: number; messages: string[] };

export default function Roster() {
  const [data, setData] = useState<RosterData | null>(null);

  useEffect(() => {
    void api<RosterData>("/api/roster")
      .then(setData)
      .catch(() => setData({ unique_count: 0, messages: [] }));
  }, []);

  return (
    <>
      <section className="panel">
        <h1>Состав Akiyama</h1>
        <p className="muted">Всего в составе: <strong>{data?.unique_count ?? 0}</strong> человек.</p>
      </section>
      {data?.messages.map((message, index) => (
        <section className="panel" key={index}>
          <pre className="roster-message">{message}</pre>
        </section>
      ))}
      {data && data.messages.length === 0 && (
        <section className="panel">
          <p className="muted">Состав не сгенерирован — запустите синхронизацию бота (/refresh).</p>
        </section>
      )}
    </>
  );
}
