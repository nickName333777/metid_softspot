"""엔진 처리 과정 화면: 5단계 탭으로 중간 산출물을 보여 준다."""
from collections import defaultdict

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .. import config as C
from .pages_input import spectrum_picker
from .theme import GOLD, GREY, MUTED, ORANGE, SKY, TEAL, style_fig
from .widgets import alert_fig, annotated_fig, hbar, mol_html, note, rank_text, tag, theory_banner

SRC_COLOR = {"학습 라이브러리 구조": SKY, "COCONUT 등 천연물 DB": TEAL, "PubChem": GOLD, "엔진 생성(유도체)": "#B07CC6"}
FEAT_KO = {
    "pv_gap": "FPNet 점수 - 분자 내 최고", "pv_rank": "FPNet 점수 순위", "pv_z": "FPNet 점수 표준화", "pv_nrm_rank": "FPNet 정규화 순위",
    "pv_top": "FPNet 1위 여부", "ap3_rank": "유사체 근거(ap3) 순위", "ap3_gap": "유사체 근거 - 최고", "t_max": "유사체와 최대 Tanimoto",
    "sn_gap": "SpecNet - 최고", "sn_rank": "SpecNet 순위", "sn": "SpecNet 점수", "frag_rank": "조각 설명 순위", "frag_gap": "조각 설명 - 최고",
    "frag": "조각 설명 비율", "is_gen": "생성 후보 여부", "lib": "라이브러리 직접 일치", "lib_gap": "라이브러리 일치 - 최고",
    "lib_rank": "라이브러리 일치 순위", "fp_tc": "FP-net 연속 Tanimoto", "fp_tc_rank": "FP-net Tanimoto 순위", "fp_tc_gap": "FP-net - 최고",
    "fp_ll": "FP-net 로그우도", "fp_ll_rank": "FP-net 로그우도 순위", "fp_ll_gap": "FP-net 로그우도 - 최고", "abs_ppm": "질량 오차 |ppm|",
    "libsh": "어덕트 보정 라이브러리 일치", "libsh_rank": "어덕트 보정 일치 순위", "libsh_gap": "어덕트 보정 일치 - 최고",
    "t_top": "최고 유사체와 Tanimoto", "t_wmean": "유사체 가중 평균 Tanimoto", "n_close": "가까운 유사체 수", "ap1": "유사체 근거 ap1",
    "ap2": "유사체 근거 ap2", "ap3": "유사체 근거 ap3", "ap4": "유사체 근거 ap4", "ap6": "유사체 근거 ap6",
    "x_lib_sn": "라이브러리×SpecNet", "x_ap_sn": "유사체×SpecNet", "gen_sim": "생성 모체 스펙트럼 유사도", "gen_tan": "생성 모체와 Tanimoto",
    "gen_steps": "생성 단계 수", "lib_mean": "라이브러리 일치 평균", "lib_cnt_log": "라이브러리 스펙트럼 수(log)",
}


def fk(f):
    return FEAT_KO.get(f, f)


def _tab_clean(mol, ctx):
    m = mol["meta"]
    st.markdown("**무엇을 하나**: 측정 스펙트럼에서 해석에 방해되는 피크를 지우고, 전구체 m/z와 이온 형태로 **중성 분자 질량**을 계산합니다. "
                "이 질량이 다음 단계의 후보 검색 기준이 됩니다.")
    rows = []
    for i, s in enumerate(mol["spectra"], 1):
        rows.append({"#": i, "이온 형태": s["adduct"], "모드": s["mode"], "전구체 m/z": s["prec"],
                     "CE (eV)": ", ".join(f"{x:g}" for x in s["ce"]), "원본 피크": len(s["raw_mz"]), "정리 후 피크": len(s["clean_mz"])})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
    a, b = st.columns(2)
    a.metric("계산된 중성 질량", f"{m['target_mass']:.4f} Da")
    b.metric("정답 대비 오차", f"{m['mass_err_ppm']:+.2f} ppm")
    st.caption("원본과 정리 후 스펙트럼 비교는 '입력 데이터' 화면에 있습니다.")


def _funnel(mol, ctx):
    f = mol["funnel"]; w = mol["window"]
    pool = ctx["index"]["settings"].get("pool_size")
    stages, vals = [], []
    if pool:
        stages.append("전체 구조 풀 (라이브러리+COCONUT)"); vals.append(pool)
    stages += [f"질량 창 안의 후보 (±{w['ppm']:g} ppm)", "최종 후보 (PubChem·유도체 추가 후)", "Top-25 제시"]
    n_window = f["n_cand"] - f["n_pubchem"] - f["n_gen"]
    vals += [n_window, f["n_cand"], min(25, mol["n_shown"])]
    fig = go.Figure(go.Funnel(y=stages, x=vals, marker=dict(color=[GREY, SKY, TEAL, ORANGE][-len(vals):]),
                              textinfo="value", texttemplate="%{value:,}", connector=dict(line=dict(color=MUTED))))
    fig.update_xaxes(type="log" if pool else "linear")
    return style_fig(fig, 300, legend=False)


def _tab_search(mol, ctx):
    w, f = mol["window"], mol["funnel"]
    st.markdown("**무엇을 하나**: 계산된 질량과 맞는 구조를 여러 구조 DB에서 모으고(질량 창), 비슷한 스펙트럼을 가진 화합물(유사체)을 찾습니다. "
                "유사체에서 질량 차이만큼 바뀐 **유도체 후보**도 엔진이 직접 만듭니다.")
    a, b, c, d = st.columns(4)
    a.metric(f"질량 창 (±{w['ppm']:g} ppm)", f"{w['target']:.4f}", help=f"{w['lo']:.4f} ~ {w['hi']:.4f} Da 안의 구조를 후보로 모읍니다.")
    b.metric("최종 후보 수", f"{f['n_cand']:,}")
    c.metric("PubChem에서 추가", f"{f['n_pubchem']:,}")
    d.metric("엔진이 만든 유도체", f"{f['n_gen']:,}")
    if len(w["tiers"]) > 1:
        st.caption(f"±{w['ppm']:g} ppm 안의 후보가 {ctx['index']['settings']['min_cands']}개 미만이라 창을 {', '.join(f'{x:g}' for x in w['fallback'])} ppm까지 넓혔습니다 "
                   "(넓힌 창의 후보는 항상 기본 창 후보 뒤에 놓입니다).")
    l, r = st.columns([3, 2])
    with l:
        st.markdown("**후보 깔때기**")
        st.plotly_chart(_funnel(mol, ctx), width="stretch")
    with r:
        st.markdown("**후보 출처**")
        src = f["by_src"]
        fig = go.Figure(go.Pie(labels=list(src), values=list(src.values()), hole=0.55,
                               marker=dict(colors=[SRC_COLOR.get(k, GREY) for k in src]), sort=False))
        st.plotly_chart(style_fig(fig, 300), width="stretch")
    cd = ctx["cands"]
    fig = go.Figure()
    for code, name in enumerate(SRC_COLOR):
        s = cd[cd.src == code]
        if len(s):
            fig.add_trace(go.Scatter(x=s.ppm, y=s.score, mode="markers", name=name, marker=dict(size=5, color=SRC_COLOR[name], opacity=0.7),
                                     hovertext=s.smiles.str.slice(0, 60), hoverinfo="text+x+y"))
    t = cd[cd.is_truth]
    if len(t):
        fig.add_trace(go.Scatter(x=t.ppm, y=t.score, mode="markers", name="정답", marker=dict(size=14, color=ORANGE, symbol="star",
                                                                                         line=dict(color="white", width=1))))
    fig.update_xaxes(title="질량 오차 (ppm)"); fig.update_yaxes(title="최종 랭커 점수")
    st.markdown("**후보 전체 분포** (가로: 질량 오차, 세로: 최종 점수 — 질량만으로는 후보를 가를 수 없다는 점이 보입니다)")
    st.plotly_chart(style_fig(fig, 340), width="stretch")

    st.markdown("**라이브러리 직접 일치** (같은 질량의 참조 스펙트럼과 엔트로피 유사도)")
    if mol["library"]:
        st.dataframe(pd.DataFrame([{"유사도": x["sim"], "참조 라이브러리": ", ".join(x["libs"]), "정답과 같은 구조": "예" if x["same_as_truth"] else "",
                                    "SMILES": x["smiles"]} for x in mol["library"]]), hide_index=True, width="stretch")
    else:
        st.info("같은 질량 창에 참조 스펙트럼이 없습니다 (C2·C3 상황에서는 정상).")
    st.markdown(f"**유사 구조 스펙트럼 (유사체)** — 질량이 달라도 조각 패턴이 비슷한 화합물 {f['n_analog']}개 중 상위 8개. "
                "질량 차이에 대사·생합성 변환 이름을 붙였습니다.")
    an = mol["analogs"]
    for i in range(0, len(an), 4):
        cols = st.columns(4)
        for col, x in zip(cols, an[i:i + 4]):
            cap = (f"스펙트럼 유사도 <b>{x['sim']:.3f}</b><br>질량 차 {x['delta']:+.4f} Da"
                   + (f" · <b>{x['delta_label']}</b>" if x["delta_label"] else "")
                   + f"<br>정답과 Tanimoto {x['tan_truth']:.2f}" + (" · <b>정답 구조</b>" if x["same_as_truth"] else ""))
            col.markdown(mol_html(x["svg"], cap), unsafe_allow_html=True)


def _tab_fp(mol, ctx):
    st.markdown("**무엇을 하나**: 딥러닝 모델이 스펙트럼만 보고 분자 지문(부분구조 2,048개 비트)의 존재 확률을 예측합니다. "
                "후보마다 예측 지문과 얼마나 맞는지(연속 Tanimoto)를 계산해, 라이브러리에 없는 구조도 점수를 매길 수 있습니다. "
                "같은 역할의 모델 3종(FP-net, FPNet 6,930비트, SpecNet 임베딩)을 함께 씁니다.")
    bits = mol["bits"]
    lab = [f"비트 {b['bit']} · {b['sub'][:28] or '-'}" for b in bits]
    col = [ORANGE if b["in_truth"] else GREY for b in bits]
    l, r = st.columns([3, 2])
    with l:
        st.markdown("**예측 확률 상위 15개 비트** (주황 = 정답 구조에 실제로 있는 부분구조)")
        st.plotly_chart(hbar(lab, [b["prob"] for b in bits], col, h=440, xtitle="예측 확률"), width="stretch")
    with r:
        n_t = sum(b["in_truth"] for b in bits); n_1 = sum(b["in_top1"] for b in bits)
        st.metric("상위 15개 중 정답에 있는 비트", f"{n_t} / 15")
        st.metric("상위 15개 중 1위 후보에 있는 비트", f"{n_1} / 15")
        st.caption("부분구조 표기는 해당 비트를 만드는 원자 환경(Morgan 반경 0~2)을 SMILES로 적은 것입니다.")
    cd = ctx["cands"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=cd.fp_tc, y=cd.pv, mode="markers", name="후보", marker=dict(size=5, color=SKY, opacity=0.5),
                             hovertext=cd.smiles.str.slice(0, 60), hoverinfo="text"))
    top1 = mol["candidates"][0] if mol["candidates"] else None
    if top1:
        fig.add_trace(go.Scatter(x=[top1["fp_tc"]], y=[top1["pv"]], mode="markers", name="1위 후보",
                                 marker=dict(size=13, color=TEAL, symbol="diamond", line=dict(color="white", width=1))))
    t = cd[cd.is_truth]
    if len(t):
        fig.add_trace(go.Scatter(x=t.fp_tc, y=t.pv, mode="markers", name="정답", marker=dict(size=14, color=ORANGE, symbol="star",
                                                                                         line=dict(color="white", width=1))))
    fig.update_xaxes(title="FP-net 연속 Tanimoto"); fig.update_yaxes(title="FPNet(6,930비트) 점수")
    st.markdown("**모든 후보의 지문 적합도** (오른쪽 위일수록 두 모델이 모두 '맞다'고 봄)")
    st.plotly_chart(style_fig(fig, 360), width="stretch")
    st.dataframe(pd.DataFrame([{"순위": c["rank"], "정답": "★" if c["is_truth"] else "", "FP-net Tanimoto": c["fp_tc"],
                                "FPNet 점수": c["pv"], "SpecNet": c["sn"], "정답과 구조 Tanimoto": c["tan_truth"], "SMILES": c["smiles"]}
                               for c in mol["candidates"][:10] + [c for c in mol["candidates"][10:] if c["is_truth"]]]),
                 hide_index=True, width="stretch")


def _tab_frag(mol, ctx):
    st.markdown("**무엇을 하나**: 후보 구조의 결합을 1~2개 끊어 나올 수 있는 조각 이온 질량을 모두 계산하고(수소 이동 ±2 허용), "
                "실제 피크와 0.01 Da 안에서 맞는지 봅니다. 맞는 피크의 강도 비율이 '조각 설명' 점수입니다.")
    i = spectrum_picker(mol, "frag_spec")
    sp = mol["spectra"][i]
    cands = mol["candidates"]
    top1 = cands[0] if cands else None
    same = top1 is not None and top1["is_truth"]
    if same:
        a = sp["ann"].get("top1", {})
        st.success("1위 후보가 정답과 같은 구조입니다.")
        st.plotly_chart(annotated_fig(sp, "top1", f"1위 후보(=정답): 설명된 강도 비율 {a.get('explained', 0):.0%}"), width="stretch")
    else:
        l, r = st.columns(2)
        with l:
            a = sp["ann"].get("top1", {})
            st.plotly_chart(annotated_fig(sp, "top1", f"1위 후보: 설명 비율 {a.get('explained', 0):.0%}"), width="stretch")
        with r:
            a = sp["ann"].get("truth", {})
            st.plotly_chart(annotated_fig(sp, "truth", f"정답 구조: 설명 비율 {a.get('explained', 0):.0%}"), width="stretch")
    who = "top1" if same else "truth"
    a = sp["ann"].get(who)
    if a:
        rows = [{"m/z": sp["clean_mz"][k], "상대 강도": sp["clean_it"][k], "조각 이온": a["ion"][k],
                 "오차 (mDa)": round(1000 * (sp["clean_mz"][k] - a["ion"][k]), 1) if a["ion"][k] else None,
                 "H 이동": a["dh"][k], "전구체에서 잃은 것": a["loss"][k], "조각 구조": a["frag_smiles"][k] or ""}
                for k in sorted(range(len(sp["clean_mz"])), key=lambda k: -sp["clean_it"][k])[:15]]
        st.markdown(f"**강한 피크 15개의 해석** ({'정답' if who == 'truth' else '1위 후보'} 기준)")
        df = pd.DataFrame(rows).astype(object)
        st.dataframe(df.where(df.notna(), ""), hide_index=True, width="stretch")
        st.caption("'전구체에서 잃은 것'은 전구체 m/z − 피크 m/z가 흔한 중성 손실(H2O, CO2, 헥소스 등)과 맞을 때만 표시합니다.")


def _tab_ranker(mol, ctx):
    st.markdown("**무엇을 하나**: 앞 단계의 근거 56개를 LightGBM 순위 모델이 종합합니다. 아래 막대는 각 근거가 "
                "**이 분자의 평균 후보보다 점수를 얼마나 올리거나 내렸는지**(SHAP 기여도)입니다.")
    cands = mol["candidates"]
    top = [c for c in cands if c.get("shap")]
    if not top:
        st.info("기여도 정보가 없습니다."); return
    fams = list(top[0]["shap"]["family"])
    fig = go.Figure()
    pal = [TEAL, SKY, GOLD, "#B07CC6", "#8FB996"]
    shown = [c for c in top if c["rank"] and c["rank"] <= 3 and not c["is_truth"]][:3]
    tr = next((c for c in top if c["is_truth"]), None)
    for k, c in enumerate(([tr] if tr else []) + shown):
        name = f"정답 ({rank_text(c['rank'])})" if c["is_truth"] else f"{c['rank']}위 후보"
        fig.add_trace(go.Bar(y=fams, x=[c["shap"]["family"][f] for f in fams], orientation="h", name=name,
                             marker_color=ORANGE if c["is_truth"] else pal[k % len(pal)]))
    fig.update_layout(barmode="group"); fig.update_yaxes(autorange="reversed"); fig.update_xaxes(title="평균 후보 대비 점수 기여")
    st.plotly_chart(style_fig(fig, 460), width="stretch")
    c0 = tr or top[0]
    st.markdown(f"**{'정답' if c0['is_truth'] else '1위 후보'}의 기여 상위 특징 8개**")
    st.dataframe(pd.DataFrame([{"특징": fk(x["feature"]), "근거 계열": x["family"], "값": x["value"], "기여": x["contrib"]}
                               for x in c0["shap"]["top"]]), hide_index=True, width="stretch")

    st.markdown("**근거 하나만 썼을 때 정답 순위 vs 전체 결합**")
    sr = mol["single_rank"]
    rows = [(k, v) for k, v in sr.items()]
    lab = [k for k, _ in rows]
    val = [(v if isinstance(v, int) else None) for _, v in rows]
    disp = [rank_text(v) if v != "na" else "근거 없음" for _, v in rows]
    # 막대 길이: 1/순위 (1위 = 1)
    fig = go.Figure(go.Bar(y=lab, x=[1.0 / v if v else 0 for v in val], orientation="h", text=disp, textposition="outside",
                           cliponaxis=False, marker_color=[ORANGE if k.startswith("최종") else TEAL for k in lab]))
    fig.update_yaxes(autorange="reversed"); fig.update_xaxes(title="1 / 정답 순위 (길수록 좋음)", range=[0, 1.25])
    st.plotly_chart(style_fig(fig, 340, legend=False), width="stretch")
    st.caption("근거 하나만으로는 놓치는 정답을 결합으로 끌어올리는 것이 랭커의 역할입니다. 정답이 후보 목록에 없으면 모두 '순위 없음'입니다.")

    with st.expander("랭커 전체에서 근거 계열별 중요도 (LightGBM gain, 학습 데이터 기준)"):
        g = defaultdict(float)
        for f, v, fam in ctx["index"]["calibration"]["gain"]:
            g[fam] += v
        tot = sum(g.values())
        items = sorted(g.items(), key=lambda x: -x[1])
        st.plotly_chart(hbar([k for k, _ in items], [v / tot for _, v in items], h=330, xtitle="gain 비율", fmt="{:.1%}"),
                        width="stretch")
    tim = mol["timing"]
    st.markdown("**단계별 처리 시간 (이 분자, 초)**")
    st.dataframe(pd.DataFrame([{"단계": k, "시간 (초)": v} for k, v in tim.items()] +
                              [{"단계": "합계", "시간 (초)": round(sum(tim.values()), 2)}]), hide_index=True, width="stretch")
    st.caption(f"참조 인덱스 준비(시나리오마다 1회, {mol['index_build_s']:.0f}초)와 라이브러리 적재 시간은 제외했습니다.")


def alert_validation_text(av):
    g, e, r = av["gsh"], av["enveda"], av["random"]
    return (f"탐지 규칙 점검(학습 라이브러리 실측 스펙트럼): GSH 포합체 {g['n_struct']}종의 스펙트럼 중 신호가 잡힌 비율 "
            f"양이온 {g['hit_pos']:.0%}(n={g['n_spec_pos']}), 음이온 {g['hit_neg']:.0%}(n={g['n_spec_neg']}), 구조 단위 {g['struct_hit']}/{g['n_struct']}종. "
            f"GSH가 아닌 스펙트럼에서 우연히 잡힌 비율 {r['hit']:.1%}(무작위 {r['n_spec']:,}개), "
            f"시험 장비 천연물 {e['struct_hit']}/{e['n_struct']}종.")


def _tab_alert(mol, ctx):
    st.markdown("**무엇을 하나**: 약물이 대사되며 생길 수 있는 **반응성 대사체**를 두 갈래로 점검합니다.  \n"
                "① **스펙트럼 신호** — 글루타티온(GSH) 포획 실험에서 생기는 포합체의 지문: 양이온 모드 **중성 손실 129.043 Da**(피로글루탐산), "
                "음이온 모드 **조각 이온 m/z 272.089**(+ 보조 254 / 210 / 143 / 128).  \n"
                "② **구조 경고** — 후보 구조에 생체활성화가 잘 일어나는 부분구조(p-아미노페놀, 퀴논이민, 퓨란, 마이클 수용체 등)가 있는지.")
    al = mol.get("alerts")
    if not al:
        st.info("이 번들에는 경고 정보가 없습니다. 번들을 다시 만드세요."); return
    sig = al["signal"]
    a, b, c = st.columns(3)
    a.metric("GSH 포합체 스펙트럼 신호", sig["level"], help="강함: 주 신호 2종 또는 주 신호+보조 신호 / 약함: 주 신호 1종")
    b.metric("1위 후보 구조 경고", f"{len(al['top1_struct'])}건")
    c.metric("(정답) 구조 경고", f"{len(al['truth_struct'])}건")
    rows = []
    for i, sp in enumerate(mol["spectra"], 1):
        for x in sp.get("alerts", []):
            rows.append({"스펙트럼": f"#{i} {sp['adduct']}", "신호": x["label"], "m/z": round(x["mz"], 4),
                         "상대 강도": round(x["rel"], 3), "오차 (mDa)": round(x["err_mda"], 1), "주 신호": "예" if x["primary"] else "보조"})
    if rows:
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        hit = [i for i, sp in enumerate(mol["spectra"]) if sp.get("alerts")]
        opts = [f"#{i + 1} · {mol['spectra'][i]['adduct']} · {mol['spectra'][i]['mode']}" for i in hit]
        k = st.selectbox("신호가 잡힌 스펙트럼", range(len(hit)), format_func=lambda j: opts[j], key="alert_spec")
        sp = mol["spectra"][hit[k]]
        st.plotly_chart(alert_fig(sp, f"{sp['adduct']} · 주황 = GSH 포합체 신호"), width="stretch")
    else:
        st.success("이 분자의 스펙트럼에서는 GSH 포합체 신호가 보이지 않습니다.")
    st.markdown("**구조 경고** (후보 상위 10개와 정답)")
    srows = []
    for cnd in mol["candidates"]:
        if cnd.get("struct_alerts") is None:
            continue
        srows.append({"순위": cnd["rank"], "정답": "★" if cnd["is_truth"] else "", "화학식": cnd["formula"],
                      "구조 경고": " · ".join(x["name"] for x in cnd["struct_alerts"]) or "없음",
                      "왜 문제인가": " / ".join(x["note"] for x in cnd["struct_alerts"]), "SMILES": cnd["smiles"]})
    st.dataframe(pd.DataFrame(srows), hide_index=True, width="stretch")
    av = ctx["index"].get("metid", {}).get("validation")
    if av:
        st.caption(alert_validation_text(av))
    note(C.ALERT_CAUTION)


def render_engine(ctx):
    mol = ctx["mol"]; m = mol["meta"]
    st.title("엔진 처리 과정")
    st.markdown(f"{tag(m['scenario'], 't')} **{m['mid']}** · {m['formula']} · {C.SCEN_TEXT[m['scenario']][0]}", unsafe_allow_html=True)
    theory_banner(mol)
    tabs = st.tabs(["① 스펙트럼 정리", "② 후보 구조 검색", "③ 지문 예측 (딥러닝)", "④ 조각 점수", "⑤ 랭커 종합", "⑥ 반응성 대사체 경고"])
    with tabs[0]:
        _tab_clean(mol, ctx)
    with tabs[1]:
        _tab_search(mol, ctx)
    with tabs[2]:
        _tab_fp(mol, ctx)
    with tabs[3]:
        _tab_frag(mol, ctx)
    with tabs[4]:
        _tab_ranker(mol, ctx)
    with tabs[5]:
        _tab_alert(mol, ctx)
    note("모든 모델은 데모 분자의 구조를 학습에 쓰지 않은 버전입니다 (딥러닝 모델 3종은 검증용 구조를 빼고 학습, 랭커는 데모 15개 구조를 빼고 다시 학습).")
