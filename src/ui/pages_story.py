"""스토리 화면: 개요(문제 · 엔진 한 장 요약 · 5단계 흐름) 와 데모 데이터 선택."""
import statistics

import pandas as pd
import streamlit as st

from .. import config as C
from ..bundle import label
from .widgets import cards, mol_html, note, tag

STEPS = [
    ("1", "스펙트럼 정리", "전구체보다 큰 피크·노이즈 제거, 상위 100개 피크만 남기고 강도 정규화. 전구체 m/z와 이온 형태로 중성 질량 계산."),
    ("2", "후보 구조 검색", "중성 질량 ±10 ppm 안의 구조를 학습 라이브러리·COCONUT·PubChem에서 모으고, 비슷한 스펙트럼의 구조로부터 유도체 후보도 만듦."),
    ("3", "지문 예측 (딥러닝)", "스펙트럼만 보고 '어떤 부분구조가 있을지'를 예측하는 모델 3종(FP-net, FPNet, SpecNet)으로 후보마다 적합도를 매김."),
    ("4", "조각 점수", "각 후보 구조를 1~2개 결합에서 잘라 만든 조각 이온이 실제 피크를 얼마나 설명하는지 계산."),
    ("5", "학습형 랭커", "위 근거 56개 특징을 LightGBM 순위 모델이 종합해 Top-25 후보와 점수, 근거별 기여도를 냄."),
]


def flow_html():
    parts = []
    for i, (n, t, d) in enumerate(STEPS):
        parts.append(f'<div class="step"><div class="n">STEP {n}</div><b>{t}</b><br><span>{d}</span></div>')
        if i < len(STEPS) - 1:
            parts.append('<div class="arr">→</div>')
    return f'<div class="flow">{"".join(parts)}</div>'


def render_overview(ctx):
    st.title(C.APP_NAME)
    st.markdown(f"**{C.TAGLINE}**")
    st.divider()
    st.subheader("왜 필요한가: 대사체·미지 성분 해석의 병목")
    cards([
        ("사람 손에 의존하는 해석", "LC-MS/MS로 얻은 스펙트럼을 구조로 바꾸는 일(MetID, 불순물·분해산물 동정)은 숙련 연구자가 "
                              "피크를 하나씩 읽고 문헌·DB를 대조하는 수작업이 큰 비중을 차지합니다."),
        ("라이브러리에 없으면 막힘", "스펙트럼 라이브러리 검색은 등록된 화합물만 찾습니다. 새 대사체나 드문 천연물은 "
                               "일치하는 기록이 없어 후보를 사람이 직접 떠올려야 합니다."),
        ("근거가 흩어져 있음", "질량 오차, 조각 이온, 유사 화합물 스펙트럼, DB 존재 여부 같은 근거가 여러 도구에 흩어져 있어 "
                            "판단 근거를 한 장으로 남기기 어렵습니다."),
    ])
    st.subheader("우리 엔진 한 장 요약")
    a, b = st.columns([3, 2])
    with a:
        st.markdown(
            "- **입력**: 한 화합물의 MS/MS 스펙트럼 1~16개 (전구체 m/z, 이온 형태 `[M+H]+` 등, 극성)\n"
            "- **출력**: 구조 후보 **Top-25** (SMILES·구조 그림), 후보별 점수와 **근거별 기여도**, 분석 보고서\n"
            "- **근거 결합**: 라이브러리 직접 일치 · 유사 구조 스펙트럼 · 조각 설명 · 딥러닝 지문 예측을 하나의 순위 모델로 결합\n"
            "- **후보 범위**: 학습 라이브러리 구조 + 천연물 DB(COCONUT) + PubChem 일부 + 엔진이 만든 유도체 후보\n"
            "- **개발 단계**: Kaggle CASMI 2026(Enveda 주최, 천연물 MS/MS 구조 동정) 데이터로 개발·검증 중인 엔진")
    with b:
        mols = ctx.get("index", {}).get("molecules", [])
        if mols:
            t = [sum(ctx["mol_time"].get(m["mid"], {}).values()) for m in mols if ctx["mol_time"].get(m["mid"])]
            st.metric("데모 분자 1개 처리 시간 (중앙값)", f"{statistics.median(t):.1f} 초" if t else "-",
                      help="이 PC(1080Ti, i7)에서 번들 생성 때 잰 시간. 참조 인덱스 준비 시간은 제외.")
            st.metric("데모 분자당 검토한 후보 구조 수 (중앙값)", f"{statistics.median([m['n_cand'] for m in mols]):,.0f} 개")
    st.subheader("5단계 처리 흐름")
    st.markdown(flow_html(), unsafe_allow_html=True)
    st.write("")
    note("이 데모는 미팅 중 안정성을 위해 엔진을 실시간으로 돌리지 않고, 미리 실행해 저장한 결과(데모 번들)를 보여 줍니다. "
         "데모 분자는 정답 구조를 아는 검증용 데이터이므로 '정답 순위'를 함께 표시합니다. 실제 미지 시료에서는 정답이 표시되지 않습니다.")
    st.subheader("화면 안내")
    st.markdown("**데모 데이터 선택** → **입력 데이터** → **엔진 처리 과정** → **최종 결과** → **예시 보고서** 순서로 보시면 됩니다. "
                "**15개 성능 요약**은 데모 분자 전체의 결과입니다.")


def _pick(mid):
    st.session_state["mid"] = mid
    st.session_state["mid_sel"] = mid


def render_select(ctx):
    st.title("데모 데이터 선택")
    st.markdown("데모 분자 15개는 대회 학습 데이터 중 **시험 장비(timsTOF)로 측정한 천연물 250종**에서 고정 seed로 무작위로 뽑았습니다. "
                "각 분자를 아래 세 가지 상황 중 하나로 가정하고, 그 상황에 맞게 참조 데이터에서 정답 정보를 지운 뒤 엔진을 돌렸습니다.")
    cols = st.columns(3)
    for c, (k, (t, d)) in zip(cols, list(C.SCEN_TEXT.items())[:3]):
        c.markdown(f'<div class="card"><h4>{tag(k, "t")} {t}</h4><p>{d}</p></div>', unsafe_allow_html=True)
    st.write("")
    mols = ctx["index"]["molecules"]
    reveal = st.toggle("정답 구조 미리 보기", value=False, help="끄면 화학식·질량만 보입니다 (미팅에서 '맞혀 보기'용).")
    for scen in ("C1", "C2", "C3", "MetID"):
        ms = [m for m in mols if m["scenario"] == scen]
        if not ms:
            continue
        st.subheader(f"{scen} · {C.SCEN_TEXT[scen][0]}" if scen != "MetID" else C.SCEN_TEXT[scen][0])
        if scen == "MetID":
            st.caption(C.SCEN_TEXT[scen][1] + " 흐름 설명은 'MetID 시연' 화면에 있습니다.")
        row = st.columns(5)
        for c, m in zip(row, ms):
            with c:
                cap = (f"<b>{m['mid']}</b><br>{m['formula']} · {m['mass']:.4f} Da<br>{', '.join(m['adducts'])} · 스펙트럼 {m['n_spec']}개"
                       f"<br><span class='hint'>{m.get('role') or m['rough_class']}</span>"
                       + ("<br><span class='gold'>이론 예시 스펙트럼</span>" if m.get("theoretical") else ""))
                if reveal:
                    st.markdown(mol_html(m["truth_svg"], cap, truth=m["mid"] == st.session_state.get("mid")), unsafe_allow_html=True)
                else:
                    sel = " truth" if m["mid"] == st.session_state.get("mid") else ""
                    st.markdown(f'<div class="molcard{sel}" style="min-height:118px"><div class="cap">{cap}</div></div>', unsafe_allow_html=True)
                st.button("이 분자 보기", key=f"pick_{m['mid']}", on_click=_pick, args=(m["mid"],), width="stretch")
    cur = next((m for m in mols if m["mid"] == st.session_state.get("mid")), None)
    if cur:
        st.success(f"선택됨: {label(cur)} — 왼쪽 메뉴에서 '입력 데이터'로 이동하세요.")
    with st.expander("데모 분자 목록 표로 보기"):
        st.dataframe(pd.DataFrame([{"ID": m["mid"], "시나리오": m["scenario"], "화학식": m["formula"], "단일동위 질량": m["mass"],
                                    "이온 형태": ", ".join(m["adducts"]), "스펙트럼 수": m["n_spec"],
                                    "구조 계열(간이)": m["rough_class"]} for m in mols]), hide_index=True, width="stretch")
        st.caption("구조 계열은 SMARTS 규칙으로 붙인 참고용 표시이며, 분류 모델 결과가 아닙니다.")
