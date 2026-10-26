import { useEffect, useState } from "react";

import { api } from "../api";

export default function Online() {
  const [server, setServer] = useState("");
  const [online, setOnline] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api<{ server: string; online: number | null; error: string | null }>("/api/online")
      .then((data) => {
        setServer(data.server);
        setOnline(data.online);
        setError(data.error);
      })
      .catch(() => setError("Не удалось получить данные"));
  }, []);

  return (
    <section className="panel">
      <h1>Онлайн · {server || "сервер"}</h1>
      {online === null ? (
        <p className="big-online muted">данные недоступны</p>
      ) : (
        <p className="big-online">{online} <span className="muted">чейнлов онлайн</span></p>
      )}
      {error && <p className="error-note">{error}</p>}
    </section>
  );
}
