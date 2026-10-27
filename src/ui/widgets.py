"""공용 시각화 조각: 스틱 스펙트럼, 구조 카드, 근거 막대."""
import html

import plotly.graph_objects as go
import streamlit as st

from .theme import GREY, GOLD, MUTED, ORANGE, SKY, TEAL, P, style_fig

STATUS_COLOR = {"유지": TEAL, "노이즈 하한 미만": GREY, "전구체 초과": GOLD, "상위 100개 밖": SKY}


def _tf(v):
    """표시용 강도 변환: 사이드바 '√강도' 토글이 켜져 있으면 제곱근 (약한 조각 피크가 보이게)."""
    if st.session_state.get("sqrt", True):
        return [(abs(a) ** 0.5) * (1 if a >= 0 else -1) for a in v]
    return list(v)


def _ylab():
    return "√상대 강도" if st.session_state.get("sqrt", True) else "상대 강도"


def _sticks(x, y):
    xs, ys = [], []
    for a, b in zip(x, y):
        xs += [a, a, None]; ys += [0, b, None]
    return xs, ys


def stick_trace(x, y, color, name, width=1.6, hover=None, legend=True):
    xs, ys = _sticks(x, y)
    line = go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=width), name=name,
                      hoverinfo="skip", showlegend=legend, legendgroup=name)
    pts = go.Scatter(x=list(x), y=list(y), mode="markers", marker=dict(color=color, size=4), name=name,
                     showlegend=False, legendgroup=name, hovertext=hover, hoverinfo="text" if hover else "x+y")
    return [line, pts]


def raw_vs_clean_fig(sp, h=430):
    """위: 원본(제거 사유별 색), 아래(거울상): 전처리 후."""
    fig = go.Figure()
    mx = max(sp["raw_it"]) if sp["raw_it"] else 1.0
    for status, color in STATUS_COLOR.items():
        idx = [i for i, s in enumerate(sp["raw_status"]) if s == status]
        if not idx:
            continue
        x = [sp["raw_mz"][i] for i in idx]; y = [sp["raw_it"][i] / mx for i in idx]
        hv = [f"m/z {a:.4f}<br>상대 강도 {b:.3f}<br>{status}" for a, b in zip(x, y)]
        for t in stick_trace(x, _tf(y), color, f"원본 · {status}", hover=hv):
            fig.add_trace(t)
    x, y = sp["clean_mz"], [-v for v in sp["clean_it"]]
    hv = [f"m/z {a:.4f}<br>상대 강도 {-b:.3f}" for a, b in zip(x, y)]
    for t in stick_trace(x, _tf(y), TEAL, "전처리 후 (아래)", hover=hv):
        fig.add_trace(t)
    fig.add_vline(x=sp["prec"], line=dict(color=ORANGE, dash="dot", width=1))
    fig.add_annotation(x=sp["prec"], y=1.05, text=f"전구체 {sp['prec']:.4f}", showarrow=False, font=dict(color=ORANGE, size=11))
    fig.update_yaxes(title=f"{_ylab()} (위: 원본 / 아래: 전처리 후)", range=[-1.12, 1.12])
    fig.update_xaxes(title="m/z")
    return style_fig(fig, h)


def annotated_fig(sp, who, title, h=380):
    """조각 설명: 후보 구조의 1~2결합 절단 조각으로 설명되는 피크(청록)와 설명 안 되는 피크(회색)."""
    ann = sp["ann"].get(who)
    fig = go.Figure()
    if not ann:
        return style_fig(fig, h)
    mz, it = sp["clean_mz"], sp["clean_it"]
    m_idx = [i for i, m in enumerate(ann["match"]) if m]
    u_idx = [i for i, m in enumerate(ann["match"]) if not m]
    hv_u = [f"m/z {mz[i]:.4f}<br>설명 안 됨" + (f"<br>전구체-손실: {ann['loss'][i]}" if ann["loss"][i] else "") for i in u_idx]
    for t in stick_trace([mz[i] for i in u_idx], _tf([it[i] for i in u_idx]), GREY, "설명 안 된 피크", hover=hv_u):
        fig.add_trace(t)
    hv_m = []
    for i in m_idx:
        s = f"m/z {mz[i]:.4f} ↔ 조각 이온 {ann['ion'][i]:.4f}<br>오차 {1000 * (mz[i] - ann['ion'][i]):+.1f} mDa, H 이동 {ann['dh'][i]:+d}"
        if ann["frag_smiles"][i]:
            s += f"<br>조각: {html.escape(ann['frag_smiles'][i][:60])}"
        if ann["loss"][i]:
            s += f"<br>전구체-손실: {ann['loss'][i]}"
        hv_m.append(s)
    for t in stick_trace([mz[i] for i in m_idx], _tf([it[i] for i in m_idx]), TEAL, "조각으로 설명된 피크", hover=hv_m):
        fig.add_trace(t)
    top = sorted(m_idx, key=lambda i: -it[i])[:6]
    for i in top:
        fig.add_annotation(x=mz[i], y=_tf([it[i]])[0], text=f"{mz[i]:.3f}", showarrow=False, yshift=10, font=dict(size=10, color=P()["ann_teal"]))
    fig.update_layout(title=dict(text=title, font=dict(size=14)))
    fig.update_yaxes(title=_ylab(), range=[0, 1.15]); fig.update_xaxes(title="m/z")
    return style_fig(fig, h)


def mol_html(svg, caption="", truth=False, small=False):
    cls = "molcard truth" if truth else "molcard"
    body = f'<div class="mol">{svg}</div>' if svg else '<div class="hint" style="padding:30px;text-align:center">구조 이미지 없음</div>'
    return f'<div class="{cls}">{body}<div class="cap">{caption}</div></div>'


def show_mol(svg, caption="", truth=False):
    st.markdown(mol_html(svg, caption, truth), unsafe_allow_html=True)


def tag(text, kind="g"):
    return f'<span class="tag tag-{kind}">{html.escape(str(text))}</span>'


def cards(items, cols=3):
    for i in range(0, len(items), cols):
        row = st.columns(cols)
        for c, (title, body) in zip(row, items[i:i + cols]):
            c.markdown(f'<div class="card"><h4>{title}</h4><p>{body}</p></div>', unsafe_allow_html=True)


def note(text):
    st.markdown(f'<div class="note">{text}</div>', unsafe_allow_html=True)


def rank_text(r):
    if not r:
        return "순위 없음"
    return f"{r}위" if r <= 25 else f"{r}위 (Top-25 밖)"


def hbar(labels, values, colors=None, h=300, xtitle="", fmt="{:.3f}"):
    fig = go.Figure(go.Bar(x=values, y=labels, orientation="h", marker_color=colors or TEAL,
                           text=[fmt.format(v) for v in values], textposition="outside", cliponaxis=False))
    fig.update_yaxes(autorange="reversed"); fig.update_xaxes(title=xtitle)
    return style_fig(fig, h, legend=False)


__all__ = ["raw_vs_clean_fig", "annotated_fig", "show_mol", "mol_html", "tag", "cards", "note", "rank_text", "hbar",
           "MUTED"]


def theory_banner(mol):
    """이론 예시 스펙트럼 분자에는 모든 화면 위에 같은 경고를 띄운다."""
    if mol["meta"].get("theoretical"):
        st.warning("이 분자의 입력은 **실측이 아닌 이론 예시 스펙트럼**입니다. 알려진 GSH 포합체 조각 규칙으로 피크 위치를 계산했고 "
                   "강도는 임의 값입니다. 반응성 대사체 경고 기능을 보여 주기 위한 것이며, 엔진 순위는 성능 근거가 아닙니다.")
    elif mol["meta"].get("scenario") == "MetID":
        st.info("MetID 시연 분자입니다. 실측 스펙트럼이지만 검증용 분리 대상이 아니어서(딥러닝 모델이 학습 중 이 구조를 봤을 수 있음) "
                "순위는 성능 근거가 아닙니다. " + mol["meta"].get("metid_note", ""))


def alert_fig(sp, title, h=360):
    """GSH 포합체 신호 피크를 주황으로 강조한 스펙트럼 (중성 손실은 전구체에서 화살표)."""
    mz, it = sp["clean_mz"], sp["clean_it"]
    hits = {round(a["mz"], 4): a for a in sp.get("alerts", [])}
    hi = [i for i, x in enumerate(mz) if round(x, 4) in hits]
    lo = [i for i in range(len(mz)) if i not in hi]
    fig = go.Figure()
    for t in stick_trace([mz[i] for i in lo], _tf([it[i] for i in lo]), GREY, "기타 피크",
                         hover=[f"m/z {mz[i]:.4f}" for i in lo]):
        fig.add_trace(t)
    hv = [f"m/z {mz[i]:.4f}<br>{hits[round(mz[i], 4)]['label']}<br>오차 {hits[round(mz[i], 4)]['err_mda']:+.1f} mDa" for i in hi]
    for t in stick_trace([mz[i] for i in hi], _tf([it[i] for i in hi]), ORANGE, "GSH 포합체 신호", hover=hv, width=2.6):
        fig.add_trace(t)
    for i in hi:
        a = hits[round(mz[i], 4)]
        y = _tf([it[i]])[0]
        fig.add_annotation(x=mz[i], y=y, text=a["kind"].replace("NL", "−").replace("F", "m/z "), showarrow=False, yshift=12,
                           font=dict(size=11, color=P()["ann_orange"]))
        if a["kind"].startswith("NL"):
            fig.add_annotation(x=mz[i], y=y, ax=sp["prec"], ay=y, xref="x", yref="y", axref="x", ayref="y", showarrow=True,
                               arrowhead=2, arrowcolor=ORANGE, arrowwidth=1.2)
    fig.add_vline(x=sp["prec"], line=dict(color=MUTED, dash="dot", width=1))
    fig.update_layout(title=dict(text=title, font=dict(size=14)))
    fig.update_yaxes(title=_ylab(), range=[0, 1.2]); fig.update_xaxes(title="m/z")
    return style_fig(fig, h)
