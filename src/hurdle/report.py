"""판정 카드 렌더 — 심사 논쟁을 반증 가능한 형태로 강제하는 마지막 문장이 핵심."""


def pct(x, d=1):
    return "—" if x is None else f"{x*100:.{d}f}%"


def render_verdict(r: dict) -> str:
    lines = [f"# 딜 판정: {r['deal']}", ""]
    lines.append(f"**{r['verdict'] or '판정 불가'}** " + (f"({r['diff']*100:+.1f}%p, base 기준)" if r["diff"] is not None else ""))
    lines.append("")
    lines.append("| 시나리오 | IRR | MOIC |")
    lines.append("|---|---|---|")
    for name, s in r["scenarios"].items():
        lines.append(f"| {name} | {pct(s['irr'])} | {s['moic']:.1f}x |")
    lines.append("")
    if r["regime_tag"] == "HOT":
        lines.append(f"> ⚠ HOT 레짐 — exit 배수가 피크 멀티플에 앵커링됐을 가능성. "
                     f"base 배수 -25% 감액 시 IRR {pct(r['scenarios']['base_haircut25']['irr'])}. "
                     f"프리미엄 +{r['regime_add']*100:.1f}%p 자동 가산 적용.")
        lines.append("")
    if r["hurdle_adj"] is not None:
        add = f" + 레짐 가산 {r['regime_add']*100:.1f}%p" if r["regime_add"] else ""
        lines.append(f"본 딜 투자는 **[바스켓: {', '.join(r['basket'])}]** 기대수익률 {pct(r['basket_return'])}"
                     f" + 프리미엄 {r['premium']*100:.1f}%p{add} = 허들 **{pct(r['hurdle_adj'])}** 대비 "
                     f"**{r['diff']*100:+.1f}%p** (base 기준). "
                     f"초과수익의 근거를 IDM '엣지' 섹션에 서면 기재할 것.")
    else:
        lines.append("허들 계산 불가 — 해당 섹터 품질 통과 종목 부족. 재무 데이터를 입력할 것.")
    return "\n".join(lines)
