import { useEffect, useState } from "react";

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

type TopPlayer = {
  name: string;
  side?: string;
  kills: number;
  damage: number;
  accuracy: number;
};

type War = {
  war_id: string;
  territory?: string;
  attacker_name?: string;
  defender_name?: string;
  won?: boolean | null;
  posted_at?: string;
};

export default function Vzp() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [top, setTop] = useState<TopPlayer[]>([]);
  const [wars, setWars] = useState<War[]>([]);

  useEffect(() => {
    void api<Stats>("/api/vzp/stats").then(setStats).catch(() => setStats(null));
    void api<{ top: TopPlayer[] }>("/api/vzp/top")
      .then((data) => setTop(data.top))
      .catch(() => setTop([]));
    void api<{ wars: War[] }>("/api/vzp/wars")
      .then((data) => setWars(data.wars))
      .catch(() => setWars([]));
  }, []);

  return (
    <>
      <section className="panel">
        <h1>VZP · Akiyama</h1>
        <p className="muted">Сервер: Blaine · vzp-launcher.pro · не официальный API GTA5RP</p>
      </section>

      <section className="panel">
        <h2>Статистика</h2>
        {stats && stats.total ? (
          <div className="stats-grid">
            <Stat label="войн" value={stats.total} />
            <Stat label="победы" value={stats.wins} className="win" />
            <Stat label="поражения" value={stats.losses} className="loss" />
            <Stat label="без результата" value={stats.unknown} />
            <Stat label="выиграно" value={`${stats.winrate}%`} />
            <Stat label="взято атак." value={stats.caps_atk} />
            <Stat label="взято защит." value={stats.caps_def} />
          </div>
        ) : (
          <p className="muted">Пока нет статистики.</p>
        )}
      </section>

      <section className="panel">
        <h2>Топ игроков</h2>
        {top.length ? (
          <table className="table">
            <thead>
              <tr><th>#</th><th>Игрок</th><th>Фракция</th><th>Kills</th><th>Урон</th><th>Точность</th></tr>
            </thead>
            <tbody>
              {top.map((row, index) => (
                <tr key={row.name}>
                  <td>{index + 1}</td>
                  <td>{row.name}</td>
                  <td>{row.side || "—"}</td>
                  <td>{row.kills}</td>
                  <td>{row.damage}</td>
                  <td>{row.accuracy}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">Топ появится после войн с участниками.</p>
        )}
      </section>

      <section className="panel">
        <h2>История войн</h2>
        {wars.length ? (
          <table className="table">
            <thead>
              <tr><th>#</th><th>Территория</th><th>Нападающие</th><th>Защитники</th><th>Результат</th><th>Дата</th></tr>
            </thead>
            <tbody>
              {wars.map((war) => (
                <tr key={war.war_id}>
                  <td><a href={`https://vzp-launcher.pro/wars/${war.war_id}`} target="_blank" rel="noopener noreferrer">{war.war_id}</a></td>
                  <td>{war.territory || "—"}</td>
                  <td>{war.attacker_name || "—"}</td>
                  <td>{war.defender_name || "—"}</td>
                  <td>
                    {war.won === true && <span className="badge win">победа</span>}
                    {war.won === false && <span className="badge loss">поражение</span>}
                    {war.won === null && <span className="badge">—</span>}
                  </td>
                  <td>{war.posted_at || ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p className="muted">История пуста.</p>
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
