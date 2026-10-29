import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "../api";

type Stats = {
  total: number;
  wins: number;
  losses: number;
  unknown: number;
  winrate: number;
  caps_atk: number;
  caps_def: number;
};

type War = {
  war_id: string;
  territory?: string;
  won?: boolean | null;
};

export default function Home() {
  const [online, setOnline] = useState<number | null>(null);
  const [rosterCount, setRosterCount] = useState(0);
  const [stats, setStats] = useState<Stats | null>(null);
  const [wars, setWars] = useState<War[]>([]);

  useEffect(() => {
    void api<{ online: number }>("/api/online")
      .then((data) => setOnline(data.online))
      .catch(() => setOnline(null));
    void api<{ unique_count: number }>("/api/roster")
      .then((data) => setRosterCount(data.unique_count))
      .catch(() => setRosterCount(0));
    void api<Stats>("/api/vzp/stats")
      .then(setStats)
      .catch(() => setStats(null));
    void api<{ wars: War[] }>("/api/vzp/wars")
      .then((data) => setWars(data.wars.slice(0, 5)))
      .catch(() => setWars([]));
  }, []);

  return (
    <>
      <section className="hero">
        <h1>Akiyama Family</h1>
        <p className="sub">GTA5RP · VZP · состав и статистика семьи</p>
      </section>

      <div className="cards">
        <div className="card">
          <div className="card-title">Онлайн</div>
          <div className="card-value">{online === null ? "—" : online}</div>
          <div className="card-sub"><Link to="/online">сервер →</Link></div>
        </div>
        <div className="card">
          <div className="card-title">В составе</div>
          <div className="card-value">{rosterCount}</div>
          <div className="card-sub"><Link to="/roster">подробнее →</Link></div>
        </div>
        <div className="card">
          <div className="card-title">Сборы</div>
          <div className="card-sub"><Link to="/gatherings">активные сборы →</Link></div>
        </div>
      </div>

      <section className="panel">
        <h2>Статистика по войнам</h2>
        {stats && stats.total ? (
          <>
            <div className="stats-grid">
              <Stat label="войн" value={stats.total} />
              <Stat label="победы" value={stats.wins} className="win" />
              <Stat label="поражения" value={stats.losses} className="loss" />
              <Stat label="без результата" value={stats.unknown} />
              <Stat label="выиграно" value={`${stats.winrate}%`} />
              <Stat label="взято атак." value={stats.caps_atk} />
              <Stat label="взято защит." value={stats.caps_def} />
            </div>
            <p><Link to="/vzp">Все войны и топ игроков →</Link></p>
          </>
        ) : (
          <p className="muted">Статистика появится после первой доигранной войны.</p>
        )}
      </section>

      <section className="panel">
        <h2>Последние войны</h2>
        {wars.length ? (
          <table className="table">
            <thead>
              <tr><th>#</th><th>Территория</th><th>Результат</th></tr>
            </thead>
            <tbody>
              {wars.map((war) => (
                <tr key={war.war_id}>
                  <td><a href={`https://vzp-launcher.pro/wars/${war.war_id}`} target="_blank" rel="noopener noreferrer">{war.war_id}</a></td>
                  <td>{war.territory || "—"}</td>
                  <td>
                    {war.won === true && <span className="badge win">победа</span>}
                    {war.won === false && <span className="badge loss">поражение</span>}
                    {war.won === null && <span className="badge">—</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">Пока нет записанных войн.</p>
        )}
      </section>
    </>
  );
}

function Stat({ label, value, className }: { label: string; value: number | string; className?: string }) {
  return (
    <div>
      <span className={className}>{value}</span>
      <label>{label}</label>
    </div>
  );
}
