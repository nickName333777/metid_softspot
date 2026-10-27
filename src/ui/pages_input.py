"""입력 데이터 화면: 메타 정보, 원본 vs 전처리 스펙트럼, 전처리에서 빠진 피크."""
from collections import Counter

import pandas as pd
import streamlit as st

from .. import config as C
from .widgets import STATUS_COLOR, note, raw_vs_clean_fig, tag, theory_banner


def spectrum_picker(mol, key):
    sp = mol["spectra"]
    if len(sp) == 1:
        return 0
    opts = [f"#{i + 1} · {s['adduct']} · {s['mode']} · CE {', '.join(f'{x:g}' for x in s['ce']) or '-'} eV"
            for i, s in enumerate(sp)]
    return st.selectbox("스펙트럼 선택", range(len(sp)), format_func=lambda i: opts[i], key=key)


def render_input(ctx):
    mol = ctx["mol"]
    m = mol["meta"]
    st.title("입력 데이터")
    st.markdown(f"{tag(m['scenario'], 't')} **{m['mid']}** · {C.SCEN_TEXT[m['scenario']][0]}", unsafe_allow_html=True)
    theory_banner(mol)
    st.markdown("엔진이 받는 입력은 **MS/MS 스펙트럼과 측정 조건뿐**입니다. 화학식이나 구조는 주지 않습니다 "
                "(아래 '화학식·질량'은 비교용 정답 정보).")
    a, b, c, d = st.columns(4)
    a.metric("스펙트럼 수", m["n_spec"])
    b.metric("전구체 m/z", ", ".join(f"{x:.4f}" for x in sorted(set(m["prec"]))[:2]) + (" …" if len(set(m["prec"])) > 2 else ""))
    c.metric("엔진이 계산한 중성 질량", f"{m['target_mass']:.4f} Da", help="전구체 m/z와 이온 형태로 계산한 값 (여러 스펙트럼이면 중앙값)")
    d.metric("정답 대비 질량 오차", f"{m['mass_err_ppm']:+.2f} ppm")
    meta = pd.DataFrame([
        ("이온 형태 (adduct)", ", ".join(m["adducts"])),
        ("이온화 모드", ", ".join(m["modes"])),
        ("충돌 에너지 (CE)", ", ".join(f"{x:g}" for x in m["ce"]) + " eV" if m["ce"] else "-"),
        ("장비", ", ".join(m["instrument"])),
        ("원본 라이브러리", ", ".join(m["library"])),
        ("(정답) 화학식 · 단일동위 질량", f"{m['formula']} · {m['mass']:.4f} Da"),
        ("(정답) 구조 계열 (간이 규칙)", m["rough_class"]),
    ], columns=["항목", "값"])
    st.dataframe(meta, hide_index=True, width="stretch")

    st.subheader("원본 스펙트럼 vs 전처리 후")
    i = spectrum_picker(mol, "inp_spec")
    sp = mol["spectra"][i]
    st.plotly_chart(raw_vs_clean_fig(sp), width="stretch")
    cnt = Counter(sp["raw_status"])
    cols = st.columns(4)
    for col, (s, color) in zip(cols, STATUS_COLOR.items()):
        col.markdown(f'<div class="card"><h4 style="color:{color}">{s}</h4><p style="font-size:1.4rem">{cnt.get(s, 0)}개 피크</p></div>',
                     unsafe_allow_html=True)
    st.write("")
    s = ctx["index"]["settings"]
    note(f"전처리 규칙: ① 전구체 m/z + {s['max_above_prec']} Da보다 큰 피크 제거 ② 최대 피크의 {100 * s['int_floor']:.1f}% 미만 제거 "
         f"③ 강한 순으로 {s['topk']}개만 유지 ④ 최대 피크 = 1로 정규화. 학습 라이브러리 250만 스펙트럼에도 똑같이 적용합니다.")
    with st.expander("피크 목록 (원본)"):
        st.dataframe(pd.DataFrame({"m/z": sp["raw_mz"], "상대 강도": sp["raw_it"], "처리": sp["raw_status"]}),
                     hide_index=True, width="stretch", height=300)
