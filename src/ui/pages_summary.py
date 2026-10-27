"""15개 성능 요약: 시나리오(C1/C2/C3)별 Top-1/Top-5/MRR. 작은 표본임을 분명히 적는다."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .. import config as C
from ..bundle import perf_table
from .theme import GREY, ORANGE, TEAL, style_fig
from .widgets import note, rank_text


def render_summary(ctx):
    idx = ctx["index"]
    mols = [m for m in idx["molecules"] if m["scenario"] in ("C1", "C2", "C3")]
    st.title("15개 성능 요약")
    st.caption("MetID 시연 분자(아세트아미노펜 등)는 이 통계에 넣지 않았습니다.")
    note(f"표본이 시나리오당 {idx['n_per']}개, 전체 {len(mols)}개뿐이라 숫자 하나하나의 오차가 큽니다 (분자 1개가 바뀌면 Top-1 비율이 20%p 움직임). "
         "엔진 성능의 근거로 쓰기보다는 화면에서 본 사례들을 한눈에 정리한 표로 봐 주세요.")
    t = perf_table(mols)
    show = t.copy()
    for c in ("Top-1", "Top-5", "Top-25", "후보 포함"):
        show[c] = [f"{v} / {n}" for v, n in zip(t[c], t["분자 수"])]
    show["MRR"] = t["MRR"].map(lambda v: f"{v:.3f}")
    show["시나리오"] = [f"{s} · {C.SCEN_TEXT[s][0]}" if s in C.SCEN_TEXT else s for s in t["시나리오"]]
    st.dataframe(show, hide_index=True, width="stretch")
    st.caption("MRR = 정답 순위의 역수 평균(1위 = 1, 2위 = 0.5, 25위 밖 = 0). 대회 채점과 같은 방식(InChIKey 앞 14자리 일치)으로 셌습니다. "
               "'후보 포함' = 정답이 엔진의 후보 목록에 들어온 분자 수(순위와 무관한 상한).")
    fig = go.Figure()
    for s, col in (("C1", TEAL), ("C2", "#6CA6D9"), ("C3", ORANGE)):
        ms = [m for m in mols if m["scenario"] == s]
        fig.add_trace(go.Bar(x=[m["mid"] for m in ms], y=[(26 - m["truth_rank"]) if m["truth_rank"] and m["truth_rank"] <= 25 else 0.3 for m in ms],
                             name=s, marker_color=col, text=[rank_text(m["truth_rank"]) if m["in_candidates"] else "후보 없음" for m in ms],
                             textposition="outside", cliponaxis=False,
                             hovertext=[f"{m['formula']} · 후보 {m['n_cand']:,}개" for m in ms]))
    fig.update_yaxes(title="막대가 높을수록 상위 (26 - 순위)", range=[0, 29]); fig.update_xaxes(title="데모 분자")
    st.plotly_chart(style_fig(fig, 380), width="stretch")
    st.dataframe(pd.DataFrame([{"ID": m["mid"], "시나리오": m["scenario"], "화학식": m["formula"], "정답 순위": rank_text(m["truth_rank"]) if m["in_candidates"] else "후보에 없음",
                                "후보 포함": "예" if m["in_candidates"] else "아니오", "후보 수": m["n_cand"], "1위 신뢰도": m["level"], "GSH 신호": m.get("alert_signal", "-"),
                                "1위 구조 경고": ", ".join(m.get("top1_struct_alerts", [])) or "없음"} for m in mols]),
                 hide_index=True, width="stretch", height=36 * (len(mols) + 1) + 4)
    cal = idx["calibration"]
    with st.expander("참고: 신뢰도 등급이 어떻게 정해졌나"):
        st.markdown(f"랭커를 구조 단위 5-fold로 교차검증한 결과(검증 질의 {cal['n_queries']:,}건, 그중 시험 장비 천연물 {cal['n_primary']:,}건)에서 "
                    "1위·2위 후보의 점수 차를 3등분해 등급을 정하고, 등급별로 1위가 실제 정답이었던 비율을 셌습니다. "
                    "검증 시뮬레이션은 실제 미지 시료보다 쉬울 수 있으므로 절대 수치보다 등급 간 차이를 봐 주세요.")
        rows = [r for r in cal["table"] if r["part"] == "primary"]
        st.dataframe(pd.DataFrame([{"등급": r["level"], "질의 수": r["n"], "1위 적중률": f"{r['top1']:.0%}" if r["top1"] is not None else "-"}
                                   for r in rows]), hide_index=True, width="stretch")
