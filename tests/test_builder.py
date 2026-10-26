from types import SimpleNamespace

from bot.config import RANK_ROLES
from bot.roster.builder import _split_section, build_roster

LEADER = RANK_ROLES[0][0]
DEP = RANK_ROLES[1][0]
MAIN = RANK_ROLES[3][0]


def _member(
    user_id: int,
    nick: str | None,
    role_ids: list[int],
    *,
    bot: bool = False,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=user_id,
        nick=nick,
        display_name=nick or "User",
        bot=bot,
        roles=[SimpleNamespace(id=rid) for rid in role_ids],
    )


def test_header_unique_count_and_multi_role() -> None:
    members = [
        _member(1, "[Klyde] | Илья", [LEADER, MAIN]),
        _member(2, "[Alpha] | A", [MAIN]),
        _member(3, "nope", [MAIN]),
    ]
    payload = build_roster(members)
    assert payload.unique_count == 3
    assert payload.messages[0] == "# Состав Akiyama\n## Численность: 3"
    leader_msg = next(m for m in payload.messages if m.startswith("## Leader of Akiyama"))
    main_msg = next(m for m in payload.messages if m.startswith("## Main Staff of Akiyama"))
    assert "<@1>" in leader_msg
    assert "<@1>" in main_msg
    assert "<@3>" in main_msg


def test_empty_ranks_omitted() -> None:
    members = [_member(1, "[Klyde] | x", [LEADER])]
    payload = build_roster(members)
    joined = "\n".join(payload.messages)
    assert "## Leader of Akiyama" in joined
    assert "## Main Staff of Akiyama" not in joined
    assert "## Young Staff of Akiyama" not in joined


def test_sort_case_insensitive() -> None:
    members = [
        _member(10, "[bob] | x", [MAIN]),
        _member(11, "[Alice] | x", [MAIN]),
        _member(12, "[alice] | x", [MAIN]),
    ]
    payload = build_roster(members)
    main_msg = next(m for m in payload.messages if m.startswith("## Main Staff of Akiyama"))
    lines = [line for line in main_msg.splitlines() if line.startswith("<@")]
    assert lines[0].startswith("<@11>")
    assert lines[1].startswith("<@12>")
    assert lines[2].startswith("<@10>")


def test_bots_and_unrelated_skipped() -> None:
    members = [
        _member(1, "[Bot] | x", [MAIN], bot=True),
        _member(2, "[Guest] | x", [999]),
    ]
    payload = build_roster(members)
    assert payload.unique_count == 0
    assert len(payload.messages) == 1


def test_split_section_repeats_heading() -> None:
    lines = [f"<@{i}>" for i in range(80)]
    chunks = _split_section("Main Staff of Akiyama", lines, limit=200)
    assert len(chunks) > 1
    assert all(c.startswith("## Main Staff of Akiyama\n") for c in chunks)
    assert sum(c.count("<@") for c in chunks) == 80


def test_roster_line_is_tag_only() -> None:
    members = [
        _member(1, "Klyde | Илья", [MAIN]),
        _member(2, "[Akiyama] Alpha | A", [MAIN]),
        _member(3, "Илья | Клайд", [MAIN]),
    ]
    payload = build_roster(members)
    main_msg = next(m for m in payload.messages if m.startswith("## Main Staff of Akiyama"))
    lines = [line for line in main_msg.splitlines() if line.startswith("<@")]
    # имени из ника в строке нет — только тег; сортировка A→Z по нику
    assert lines == ["<@2>", "<@1>", "<@3>"]
