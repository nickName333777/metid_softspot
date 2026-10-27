"""예시 보고서 화면: 선택한 분자의 분석 보고서를 HTML로 보여 주고 내려받기."""
import streamlit as st
import streamlit.components.v1 as components

from ..report import build_report
from .pages_result import confidence_text
from .widgets import theory_banner


def render_report(ctx):
    mol = ctx["mol"]
    st.title("예시 보고서")
    st.markdown("선택한 분자의 분석 결과를 연구자에게 전달하는 형식으로 정리한 **HTML 한 파일**입니다. "
                "구조 그림과 스펙트럼이 파일 안에 들어 있어 메일 첨부·인쇄에 그대로 쓸 수 있습니다.")
    theory_banner(mol)
    lv, lv_note = confidence_text(mol, ctx["index"]["calibration"])
    doc = build_report(mol, ctx["index"], lv, lv_note)
    st.download_button("보고서 HTML 내려받기", doc.encode("utf-8"), f"report_{mol['meta']['mid']}.html", "text/html", type="primary")
    components.html(doc, height=1500, scrolling=True)
