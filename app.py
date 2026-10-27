"""MS/MS 구조 추정 엔진 데모 — Streamlit (라우팅 / 데이터 로딩만 담당).
엔진은 실행하지 않고 scripts/build_demo_bundle.py가 만든 데모 번들만 읽는다 (미팅 중 안정성)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st  # noqa: E402

from src import config as C  # noqa: E402
from src.bundle import bundle_ok, label, load_cands, load_index, load_mol  # noqa: E402
from src.ui.theme import apply_theme, current_server_mode, sync_streamlit_theme  # noqa: E402

st.set_page_config(page_title=C.APP_NAME, page_icon="🧪", layout="wide")
# 화면 테마 (기본 다크). 새 세션은 서버의 현재 테마로 시작해, 창을 여러 개 열어도 서로 뒤집지 않는다.
st.session_state.setdefault("theme_choice", "라이트" if current_server_mode() == "light" else "다크")
with st.sidebar:
    st.radio("화면 테마", ["다크", "라이트"], key="theme_choice", horizontal=True)
sync_streamlit_theme()
apply_theme()

if not bundle_ok(C.BUNDLE_DIR):
    st.title(C.APP_NAME)
    st.error(f"데모 번들이 없습니다: `{C.BUNDLE_DIR}`")
    st.markdown("저장소 루트(casmi26 폴더)에서 엔진 환경으로 번들을 먼저 만드세요 (약 10~20분):")
    st.code(C.BUILD_CMD, language="bash")
    st.markdown("다른 위치의 번들을 쓰려면 환경변수 `CASMI_DEMO_BUNDLE`에 폴더를 지정하세요.")
    st.stop()


@st.cache_resource(show_spinner="데모 번들 읽는 중...")
def load_all(d: str):
    p = Path(d)
    idx = load_index(p)
    mols = {m["mid"]: load_mol(p, m["mid"]) for m in idx["molecules"]}
    cands = {m["mid"]: load_cands(p, m["mid"]) for m in idx["molecules"]}
    return idx, mols, cands


INDEX, MOLS, CANDS = load_all(str(C.BUNDLE_DIR))
MIDS = [m["mid"] for m in INDEX["molecules"]]
LABELS = {m["mid"]: label(m) for m in INDEX["molecules"]}
QP = st.query_params                       # 북마크용: ?mid=v_1757&page=3 (page = 메뉴 번호 0~7)
if "mid" not in st.session_state and QP.get("mid") in MIDS:
    st.session_state["mid"] = QP.get("mid")
if "menu" not in st.session_state and str(QP.get("page", "")).isdigit() and int(QP.get("page")) < len(C.MENU):
    st.session_state["menu"] = C.MENU[int(QP.get("page"))]
st.session_state.setdefault("mid", MIDS[0])
st.session_state.setdefault("mid_sel", st.session_state["mid"])

from src.ui import pages_engine, pages_input, pages_metid, pages_report, pages_result, pages_story, pages_summary  # noqa: E402

PAGES = {"개요": pages_story.render_overview, "데모 데이터 선택": pages_story.render_select, "입력 데이터": pages_input.render_input,
         "엔진 처리 과정": pages_engine.render_engine, "최종 결과": pages_result.render_result, "예시 보고서": pages_report.render_report,
         "MetID 시연 (반응성 대사체)": pages_metid.render_metid,
         "15개 성능 요약": pages_summary.render_summary}

with st.sidebar:
    st.title(C.APP_NAME)
    st.caption(C.TAGLINE)
    menu = st.radio("화면 선택", C.MENU, key="menu")
    st.markdown("---")
    st.selectbox("분석 분자", MIDS, format_func=lambda m: LABELS[m], key="mid_sel",
                 on_change=lambda: st.session_state.update(mid=st.session_state["mid_sel"]),
                 help="'입력 데이터'~'예시 보고서' 화면이 이 분자를 보여 줍니다.")
    st.toggle("스펙트럼 √강도 표시", value=True, key="sqrt", help="강한 전구체 피크 때문에 작은 조각 피크가 안 보일 때 켭니다 (표시만 바뀜).")
    st.markdown("---")
    st.caption(f"데모 번들: {INDEX['created']} 생성 · seed {INDEX['seed']} · 분자 {len(MIDS)}개")

mid = st.session_state["mid"]
ctx = {"index": INDEX, "mol": MOLS[mid], "cands": CANDS[mid], "mols": MOLS,
       "mol_time": {k: v["timing"] for k, v in MOLS.items()}}
PAGES[menu](ctx)
