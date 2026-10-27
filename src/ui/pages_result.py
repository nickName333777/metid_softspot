"""최종 결과 화면: Top-N 구조 카드·표, 정답 순위, 정답 vs 1위 비교, 신뢰도."""
import pandas as pd
import streamlit as st

from .. import config as C
from .widgets import mol_html, note, rank_text, tag, theory_banner


def confidence_text(mol, cal, primary=True):
    lv = mol["confidence"]["level"]
    row = next((r for r in cal["table"] if r["level"] == lv and r["part"] == ("primary" if primary else "all")), None)
    if row and row["top1"] is not None:
        return lv, f"검증 분자 {row['n']:,}건 중 같은 등급에서 1위가 정답이었던 비율 {row['top1']:.0%}"
    return lv, ""


def render_result(ctx):
    mol = ctx["mol"]; m = mol["meta"]; tr = mol["truth"]
    st.title("최종 결과")
    st.markdown(f"{tag(m['scenario'], 't')} **{m['mid']}** · {m['formula']} · {C.SCEN_TEXT[m['scenario']][0]}", unsafe_allow_html=True)
    theory_banner(mol)
    lv, lv_note = confidence_text(mol, ctx["index"]["calibration"])
    a, b, c, d = st.columns(4)
    a.metric("정답 순위", rank_text(tr["rank"]) if tr["in_candidates"] else "후보에 없음")
    b.metric("검토한 후보 수", f"{mol['funnel']['n_cand']:,}")
    c.metric("1위 신뢰도 등급", lv, help="1위와 2위 후보의 점수 차를 검증 분자의 실제 적중률로 환산한 등급입니다. " + lv_note)
    short = {"학습 라이브러리 구조": "라이브러리", "COCONUT 등 천연물 DB": "COCONUT 등", "엔진 생성(유도체)": "엔진 생성"}
    d.metric("정답 구조의 출처", short.get(tr["src"], tr["src"]) or "-", help="정답 구조가 어느 구조 DB를 통해 후보에 들어왔는지")
    if lv_note:
        st.caption(f"신뢰도 '{lv}': {lv_note} (랭커 교차검증 결과, 시험 장비 천연물 분자 기준).")
    if not tr["in_candidates"]:
        note("정답 구조가 엔진의 후보 목록에 들어오지 못했습니다. 검색한 구조 DB에 정답이 없으면 순위 모델이 아무리 좋아도 맞힐 수 없습니다. "
             "이런 경우를 줄이기 위해 유도체 생성과 외부 DB 확장을 개발 중입니다.")

    n = st.slider("표시할 후보 수 (Top-N)", 5, 25, 10, 5)
    cands = mol["candidates"]
    top = cands[:mol["n_shown"]][:n]
    st.subheader(f"구조 후보 Top-{n}")
    for i in range(0, len(top), 5):
        cols = st.columns(5)
        for col, x in zip(cols, top[i:i + 5]):
            cap = (f"<b>{x['rank']}위</b> · 점수 {x['score']:.2f} ({x['gap']:+.2f})<br>{x['formula']} · {x['src']}"
                   + ("<br><span class='truthtxt'>★ 정답</span>" if x["is_truth"] else f"<br>정답과 Tanimoto {x['tan_truth']:.2f}"))
            col.markdown(mol_html(x["svg"] or x["svg_small"], cap, truth=x["is_truth"]), unsafe_allow_html=True)
    df = pd.DataFrame([{"순위": x["rank"], "정답": "★" if x["is_truth"] else "", "점수": x["score"], "1위 대비": x["gap"],
                        "화학식": x["formula"], "질량 오차 (ppm)": x["ppm"], "라이브러리 일치": x["lib"], "유사체 근거": x["ap3"],
                        "조각 설명": x["frag"], "FP-net": x["fp_tc"], "SpecNet": x["sn"], "출처": x["src"], "SMILES": x["smiles"]}
                       for x in cands[:mol["n_shown"]]])
    st.dataframe(df.head(n), hide_index=True, width="stretch",
                 column_config={"점수": st.column_config.NumberColumn(format="%.3f"),
                                "1위 대비": st.column_config.NumberColumn(format="%+.3f")})
    st.download_button("Top-25 후보 CSV 내려받기", df.to_csv(index=False).encode("utf-8-sig"), f"{m['mid']}_top25.csv", "text/csv")

    st.subheader("정답 vs 1위 후보")
    t1 = cands[0] if cands else None
    tc = next((x for x in cands if x["is_truth"]), None)
    if t1 and t1["is_truth"]:
        st.success("엔진의 1위 후보가 정답과 같은 구조입니다 (대회 채점 기준: 입체·호변 이성질 무시한 InChIKey 앞 14자리 일치).")
    l, r = st.columns(2)
    with l:
        st.markdown("**정답 구조**")
        st.markdown(mol_html(tr["svg"], f"{m['formula']} · {m['mass']:.4f} Da · 엔진 순위 {rank_text(tr['rank']) if tr['in_candidates'] else '후보 없음'}",
                             truth=True), unsafe_allow_html=True)
    with r:
        if t1:
            st.markdown("**엔진 1위 후보**")
            st.markdown(mol_html(t1["svg"], f"{t1['formula']} · {t1['mass']:.4f} Da · 점수 {t1['score']:.2f}", truth=t1["is_truth"]),
                        unsafe_allow_html=True)
    if t1 and tc and not t1["is_truth"]:
        comp = pd.DataFrame([
            ("순위", t1["rank"], tc["rank"]), ("랭커 점수", t1["score"], tc["score"]), ("화학식", t1["formula"], tc["formula"]),
            ("라이브러리 직접 일치", t1["lib"], tc["lib"]), ("유사체 근거", t1["ap3"], tc["ap3"]), ("조각 설명 비율", t1["frag"], tc["frag"]),
            ("FP-net Tanimoto", t1["fp_tc"], tc["fp_tc"]), ("FPNet 점수", t1["pv"], tc["pv"]), ("SpecNet", t1["sn"], tc["sn"]),
            ("출처", t1["src"], tc["src"])], columns=["항목", "1위 후보", "정답"])
        st.dataframe(comp.astype(str), hide_index=True, width="stretch")
        st.caption(f"두 구조의 Tanimoto 유사도 {t1['tan_truth']:.2f} — 1에 가까울수록 골격이 비슷한 이성질체·유사체입니다.")
    al = mol.get("alerts")
    if al:
        st.subheader("주의 플래그 (반응성 대사체)")
        sig = al["signal"]
        kinds = ", ".join(sig["primary"] + sig["support"]) or "-"
        t1s = ", ".join(x["name"] for x in al["top1_struct"]) or "없음"
        if sig["level"] != "없음":
            st.error(f"GSH 포합체 스펙트럼 신호 **{sig['level']}** ({kinds}) — 반응성 대사체가 GSH에 포획된 형태일 가능성. "
                     "'엔진 처리 과정 ⑥'에서 신호 피크를 확인하세요.")
        else:
            st.success("GSH 포합체 스펙트럼 신호 없음.")
        (st.warning if al["top1_struct"] else st.info)(f"1위 후보 구조 경고: {t1s}")
        st.caption(C.ALERT_CAUTION)
    note("점수는 같은 분자의 후보끼리 비교하는 상대값입니다. 확률이 아니므로 다른 분자의 점수와 직접 비교하지 마세요.")
