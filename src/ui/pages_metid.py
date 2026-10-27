"""MetID 시연 화면: 아세트아미노펜 → NAPQI → GSH 포합체 흐름으로 반응성 대사체 경고를 보여 준다."""
import pandas as pd
import streamlit as st

from .. import config as C
from .pages_engine import alert_validation_text
from .widgets import alert_fig, mol_html, note, tag


def _pick(mid):
    st.session_state["mid"] = mid
    st.session_state["mid_sel"] = mid


def _struct_tags(alerts):
    return " ".join(tag(a["name"], "o") for a in alerts) or tag("구조 경고 없음", "g")


def render_metid(ctx):
    idx = ctx["index"]
    md = idx.get("metid")
    st.title("MetID 시연: 반응성 대사체 경고")
    if not md:
        st.info("이 번들에는 MetID 시연 데이터가 없습니다. 번들을 다시 만드세요."); return
    st.markdown("약은 간에서 대사되며 대부분 안전하게 배설되지만, 일부는 단백질과 결합하는 **반응성 대사체**로 바뀌어 간독성의 원인이 됩니다. "
                "반응성 대사체는 수명이 짧아 직접 보이지 않으므로, 실험에서는 **글루타티온(GSH)으로 포획**한 뒤 포합체를 LC-MS/MS로 찾습니다. "
                "엔진은 이 포합체의 MS/MS 지문과 후보 구조의 위험 부분구조를 자동으로 점검해 **주의 플래그**를 띄웁니다.")

    st.subheader("① 대사 경로: 아세트아미노펜 → NAPQI → GSH 포합체")
    pw, steps = md["pathway"], md["steps"]
    cols = st.columns([4, 1.4, 4, 1.4, 4])
    for k, p in enumerate(pw):
        with cols[2 * k]:
            cap = (f"<b>{p['name']}</b> · {p['role']}<br>{p['formula']} · {p['mass']:.4f} Da<br>"
                   f"<span class='hint'>{p['note']}</span><br>{_struct_tags(p['struct_alerts'])}")
            st.markdown(mol_html(p["svg"], cap, truth=p["role"] == "반응성 대사체"), unsafe_allow_html=True)
        if k < len(pw) - 1:
            s = steps[k]
            cols[2 * k + 1].markdown(f"<div style='text-align:center;padding-top:70px'><span style='font-size:1.6rem'>→</span><br>"
                                     f"<b>{s['delta']:+.3f}</b><br><span class='hint'>{s['label']}</span></div>",
                                     unsafe_allow_html=True)
    s02 = steps[2]
    st.caption(f"모약물 → 포합체 질량 차 {s02['delta']:+.4f} Da = {s02['label'] or 'GSH − 2H'}. "
               "엔진의 대사 변환 표(유사체 질량 차 이름 붙이기)에 같은 규칙이 들어 있습니다. "
               "NAPQI 자체는 불안정해 측정 스펙트럼이 없으며, 실제로 측정하는 것은 오른쪽 포합체입니다.")

    st.subheader("② 포합체 스펙트럼에서 GSH 신호 탐지")
    ms = [m for m in idx["molecules"] if m["scenario"] == "MetID"]
    for m in ms:
        mol = ctx["mols"][m["mid"]]
        sig = mol["alerts"]["signal"]
        head = (f"{tag(m['role'], 't')} <b>{m['mid']}</b> · {m['formula']} · GSH 신호 <b>{sig['level']}</b>"
                + (" · <span class='gold'>이론 예시 스펙트럼(실측 아님)</span>" if m.get("theoretical") else " · 실측 스펙트럼"))
        st.markdown(head, unsafe_allow_html=True)
        st.caption(mol["meta"].get("metid_note", ""))
        hit = [sp for sp in mol["spectra"] if sp.get("alerts")]
        if hit:
            by_mode = {}
            for sp in hit:
                by_mode.setdefault(sp["mode"], sp)
            cs = st.columns(len(by_mode))
            for c, (mode, sp) in zip(cs, by_mode.items()):
                c.plotly_chart(alert_fig(sp, f"{mode} {sp['adduct']} · 전구체 {sp['prec']:.3f}", h=320), width="stretch",
                               key=f"metid_{m['mid']}_{mode}")
        else:
            st.success("GSH 포합체 신호 없음 — 모약물 스펙트럼에서는 경고가 뜨지 않아야 정상입니다.")
        st.markdown(f"구조 경고(이 분자): {_struct_tags(mol['alerts']['truth_struct'])}", unsafe_allow_html=True)
        st.button("이 분자를 선택해 엔진 화면에서 보기", key=f"metid_pick_{m['mid']}", on_click=_pick, args=(m["mid"],))
        st.divider()

    st.subheader("③ 탐지 규칙은 얼마나 믿을 만한가")
    av = md["validation"]
    g, e, r = av["gsh"], av["enveda"], av["random"]
    st.dataframe(pd.DataFrame([
        {"점검 대상 (학습 라이브러리 실측)": f"GSH 포합체 {g['n_struct']}종 · 양이온 스펙트럼", "스펙트럼 수": g["n_spec_pos"], "신호 탐지 비율": f"{g['hit_pos']:.0%}"},
        {"점검 대상 (학습 라이브러리 실측)": f"GSH 포합체 {g['n_struct']}종 · 음이온 스펙트럼", "스펙트럼 수": g["n_spec_neg"], "신호 탐지 비율": f"{g['hit_neg']:.0%}"},
        {"점검 대상 (학습 라이브러리 실측)": "GSH가 아닌 무작위 스펙트럼 (우연 탐지)", "스펙트럼 수": r["n_spec"], "신호 탐지 비율": f"{r['hit']:.1%}"},
        {"점검 대상 (학습 라이브러리 실측)": "시험 장비 천연물 (우연 탐지)", "스펙트럼 수": e["n_spec"], "신호 탐지 비율": f"{e['hit']:.1%}"},
    ]), hide_index=True, width="stretch")
    st.caption(alert_validation_text(av))
    demo = [m for m in idx["molecules"] if m["scenario"] in ("C1", "C2", "C3")]
    n_sig = sum(m.get("alert_signal", "없음") != "없음" for m in demo)
    n_st = sum(bool(m.get("top1_struct_alerts")) for m in demo)
    st.markdown(f"- 천연물 데모 15개 중 GSH 신호가 잡힌 분자: **{n_sig}개** (거짓 양성 점검)\n"
                f"- 천연물 데모 15개 중 1위 후보에 구조 경고가 있는 분자: **{n_st}개** — 마이클 수용체·퓨란 같은 부분구조는 천연물에 흔해서, "
                "구조 경고만으로는 판단하지 않고 스펙트럼 신호와 함께 봅니다.")
    st.markdown("**해석**: 양이온 129 손실은 놓치는 경우가 많고(문헌에서도 알려진 한계), 음이온 m/z 272가 더 잘 잡힙니다. "
                "그래서 실무에서는 두 모드를 함께 측정하고 둘 중 하나라도 잡히면 확인 실험 대상으로 올립니다.")
    note(C.ALERT_CAUTION + " 약물 대사체(MetID) 전용 규칙(1상·2상 반응 질량 이동, 포획제 종류 확대)은 향후 PoC에서 확장할 예정입니다.")
