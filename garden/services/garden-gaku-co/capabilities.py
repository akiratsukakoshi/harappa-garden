"""scope ごとの capability(使える行動 tool の集合)— ベンダー中立。

ADR 2026-06-03 vendor-neutral-interaction-layer 決定3・決定4 /
ADR 2026-05-31 memory-three-layer §4(情報境界)/ gaku-co5.0 app/config/channels.py 相当。

情報境界を **prompt 頼みでなく構造で** 保証する層。ある tool が scope の集合に
入っていなければ、その scope の頭脳には ToolSpec が渡らない = 呼びようがない。
財務・給与系 tool は staff / core_team の集合に**入れない**ことで漏洩経路を消す。

凡例(将来 tool が増えたらここに足す):
  - basic     : 誰でも(挨拶・echo・FAQ 等、無害なもの)
  - staff_ops : シフト・イベント準備・事務連絡(スタッフ公開可)
  - hmc_team  : コアの運営判断補助(運営スタッフまで)
  - private   : 財務・給与・経営機微(master のみ)
"""
from __future__ import annotations

# scope -> 使える tool 名の集合。
# S42: core_team 初の実 tool = get_event_roster(field_assistant、read-only)。
# line_staff には出さない(保護者・子どもの個人情報を扱うため staff_ops 階層ではない)。
CAPABILITIES: dict[str, frozenset[str]] = {
    "master":         frozenset({
        "echo",
        "get_event_roster",
        "get_weather",
        "request_meeting_coordination",
        "record_meeting_availability",
        "confirm_meeting_coordination",
    }),
    "line_core_team": frozenset({
        "echo",
        "get_event_roster",
        "get_weather",
        "request_meeting_coordination",
        "record_meeting_availability",
        "confirm_meeting_coordination",
    }),
    "line_staff":     frozenset({"echo"}),   # 将来: basic + staff_ops のみ(厳密)
}


def tools_for(scope: str) -> frozenset[str]:
    """その scope が呼べる tool 名集合。未知 scope は空(=何も呼べない安全側)。"""
    return CAPABILITIES.get(scope, frozenset())
