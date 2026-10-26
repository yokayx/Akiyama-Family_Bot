import json
from datetime import UTC, datetime

from sqlalchemy import select

from bot.db import session_scope
from bot.models import PostedVzpWar, VzpDefense, VzpWarDetail
from bot.vzp.filter import family_side, family_won


async def already_posted(war_id: str) -> bool:
    async with session_scope() as session:
        row = await session.get(PostedVzpWar, war_id)
        return row is not None


async def mark_posted(war_id: str, message_id: int | None, detail: dict | None = None) -> None:
    """Запомнить войну как опубликованную. detail — JSON для сайта."""
    async with session_scope() as session:
        row = await session.get(PostedVzpWar, war_id)
        if row is None:
            session.add(PostedVzpWar(war_id=war_id, message_id=message_id))
        else:
            row.message_id = message_id

        if detail is not None:
            payload = json.dumps(detail, ensure_ascii=False)
            existing = await session.get(VzpWarDetail, war_id)
            if existing is None:
                session.add(VzpWarDetail(war_id=war_id, payload=payload))
            else:
                existing.payload = payload


async def has_any_posted() -> bool:
    async with session_scope() as session:
        row = (await session.scalars(select(PostedVzpWar.war_id).limit(1))).first()
        return row is not None


async def defense_noticed(war_id: str) -> bool:
    async with session_scope() as session:
        row = await session.get(VzpDefense, war_id)
        return row is not None


async def mark_defense(war_id: str, *, attacker: str, territory: str, event_id: int | None) -> None:
    async with session_scope() as session:
        row = await session.get(VzpDefense, war_id)
        if row is not None:
            return
        session.add(
            VzpDefense(
                war_id=war_id,
                attacker=attacker,
                territory=territory,
                noticed_at=datetime.now(UTC),
                event_id=event_id,
            )
        )


async def recent_wars(limit: int = 10) -> list[dict]:
    """Новые доигранные войны с деталями — для сайта."""
    async with session_scope() as session:
        result = await session.execute(
            select(VzpWarDetail)
            .order_by(VzpWarDetail.posted_at.desc())
            .limit(max(1, min(limit, 100)))
        )
        wars = []
        for row in result.scalars().all():
            try:
                detail = json.loads(row.payload or "{}")
            except json.JSONDecodeError:
                continue
            if isinstance(detail, dict):
                detail["posted_at"] = row.posted_at.isoformat() if row.posted_at else None
                wars.append(detail)
        return wars


def _war_outcome(war: dict) -> dict:
    """Из хранённой войны — результат для статистики семьи."""
    side = family_side(war)
    won = family_won(war)
    return {"side": side, "won": won}


async def war_stats() -> dict:
    """Общая статистика семьи по хранённым войнам."""
    wars = await recent_wars(limit=100)
    total = len(wars)
    wins = losses = draws = unknown = 0
    caps_atk = caps_def = 0
    for war in wars:
        outcome = _war_outcome(war)
        if outcome["won"] is True:
            wins += 1
        elif outcome["won"] is False:
            losses += 1
        elif outcome["won"] is None:
            unknown += 1
        else:
            draws += 1
        if outcome["side"] == "attacker" and outcome["won"] is True:
            caps_atk += 1
        elif outcome["side"] == "defender" and outcome["won"] is True:
            caps_def += 1
    decided = wins + losses
    return {
        "total": total,
        "wins": wins,
        "losses": losses,
        "unknown": unknown,
        "winrate": round(wins / decided * 100, 1) if decided else None,
        "caps_atk": caps_atk,
        "caps_def": caps_def,
    }


async def top_players(limit: int = 10) -> list[dict]:
    """Топ игроков семьи по kills/урону/точности за хранённые войны."""
    wars = await recent_wars(limit=100)
    stats: dict[str, dict] = {}
    for war in wars:
        side = family_side(war)
        for person in war.get("participants") or []:
            if not isinstance(person, dict):
                continue
            if side and person.get("family_side") != side:
                continue
            name = str(person.get("player_name") or "—")
            key = name.casefold()
            row = stats.setdefault(key, {"name": name, "kills": 0, "damage": 0, "games": 0})
            row["kills"] += int(person.get("kills") or 0)
            row["damage"] += int(person.get("damage") or 0)
            row["games"] += 1
    top = sorted(stats.values(), key=lambda r: (-r["kills"], -r["damage"]))
    return top[: max(1, min(limit, 50))]
