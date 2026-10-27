"""다크 / 라이트 두 테마 + 공통 포인트 컬러 2개(주황 = 정답·강조, 청록 = 엔진 산출물). plotly는 style_fig()로 통일.

테마 전환: 사이드바 토글 → sync_streamlit_theme()이 Streamlit 기본 위젯 테마(theme.base 등)까지 바꾸고 다시 그린다.
Streamlit 설정은 서버 프로세스 전체에 걸리므로, 한 PC에서 한 사람이 쓰는 로컬 데모를 전제로 한다.
"""
import streamlit as st

ORANGE, TEAL = "#E4572E", "#2A9D8F"
GOLD, SKY, GREY, MUTED = "#F2C14E", "#6CA6D9", "#7a8aa0", "#7f93ad"

PALETTES = {
    "dark": dict(bg="#0f1c2e", panel="#16263d", side="#0a1424", text="#e6edf7", body="#c4d0e0", muted="#7f93ad",
                 line="#1f3350", hover="#0a1424", ann_teal="#bfeee7", ann_orange="#ffb59c", gold_text="#F2C14E",
                 truth_text="#ff9a7a", tag_o="#ff9a7a", tag_t="#7fe0d3", tag_g="#b8c6d8", note_bg="rgba(228,87,46,.07)",
                 btn_hover="#3cbcad"),
    "light": dict(bg="#f5f7fb", panel="#ffffff", side="#e9eef5", text="#14233a", body="#33465f", muted="#5b6b80",
                  line="#d3dbe6", hover="#ffffff", ann_teal="#1d7a6f", ann_orange="#b23a17", gold_text="#9a6b00",
                  truth_text="#c0391b", tag_o="#b23a17", tag_t="#1d7a6f", tag_g="#44556b", note_bg="rgba(228,87,46,.08)",
                  btn_hover="#238a7e"),
}
# Streamlit 기본 위젯(표, 선택 상자 등)에 넘기는 테마 값
ST_THEME = {
    "dark": dict(base="dark", primaryColor=ORANGE, backgroundColor="#0f1c2e", secondaryBackgroundColor="#16263d",
                 textColor="#e6edf7"),
    "light": dict(base="light", primaryColor=ORANGE, backgroundColor="#f5f7fb", secondaryBackgroundColor="#e9eef5",
                  textColor="#14233a"),
}


def mode():
    return "light" if st.session_state.get("theme_choice") == "라이트" else "dark"


def P():
    """현재 테마의 팔레트."""
    return PALETTES[mode()]


def current_server_mode():
    return "light" if st._config.get_option("theme.base") == "light" else "dark"


def sync_streamlit_theme():
    """토글 값과 Streamlit 테마 설정이 다르면 설정을 바꾸고 다시 실행한다 (기본 위젯·표 색까지 바뀜).
    config.toml은 실행한 폴더 기준으로 읽히므로(저장소 루트에서 실행하면 demo_app/.streamlit은 무시됨),
    설정이 비어 있을 때도 여기서 직접 채운다."""
    want = mode()
    if (st._config.get_option("theme.base") != want
            or st._config.get_option("theme.backgroundColor") != ST_THEME[want]["backgroundColor"]):
        for k, v in ST_THEME[want].items():
            st._config.set_option(f"theme.{k}", v)
        st.rerun()


def css():
    p = P()
    return f"""<style>
.stApp {{ background-color:{p['bg']}; color:{p['text']}; }}
[data-testid="stSidebar"] {{ background-color:{p['side']}; border-right:1px solid {p['line']}; }}
h1,h2,h3 {{ color:{p['text']}; font-weight:600; letter-spacing:-0.01em; }}
.stButton>button {{ background-color:{TEAL}; color:#04131a; border:none; font-weight:600; border-radius:8px; }}
.stButton>button:hover {{ background-color:{p['btn_hover']}; color:#04131a; }}
[data-testid="stMetric"] {{ background-color:{p['panel']}; padding:14px; border-radius:10px; border:1px solid {p['line']}; }}
[data-testid="stMetricLabel"] {{ color:{p['muted']}; }}
.stPlotlyChart {{ background-color:{p['panel']}; border-radius:10px; padding:8px; border:1px solid {p['line']}; }}
.card {{ background:{p['panel']}; border:1px solid {p['line']}; border-radius:12px; padding:14px 16px; height:100%; }}
.card h4 {{ margin:0 0 6px 0; font-size:1.02rem; color:{p['text']}; }}
.card p, .card li {{ color:{p['body']}; font-size:0.92rem; line-height:1.5; margin:0; }}
.tag {{ display:inline-block; padding:2px 9px; border-radius:999px; font-size:0.78rem; font-weight:600; margin-right:4px; }}
.tag-o {{ background:rgba(228,87,46,.15); color:{p['tag_o']}; border:1px solid rgba(228,87,46,.5); }}
.tag-t {{ background:rgba(42,157,143,.15); color:{p['tag_t']}; border:1px solid rgba(42,157,143,.5); }}
.tag-g {{ background:rgba(127,147,173,.15); color:{p['tag_g']}; border:1px solid {p['line']}; }}
.mol {{ background:#ffffff; border-radius:10px; padding:4px; text-align:center; border:1px solid {p['line']}; }}
.mol svg {{ max-width:100%; height:auto; }}
.molcard {{ background:{p['panel']}; border:1px solid {p['line']}; border-radius:12px; padding:8px; margin-bottom:10px; }}
.molcard.truth {{ border:2px solid {ORANGE}; box-shadow:0 0 0 2px rgba(228,87,46,.25); }}
.molcard .cap {{ font-size:0.82rem; color:{p['body']}; padding:6px 4px 2px 4px; line-height:1.45; }}
.flow {{ display:flex; gap:8px; align-items:stretch; flex-wrap:wrap; }}
.flow .step {{ flex:1 1 150px; background:{p['panel']}; border:1px solid {p['line']}; border-top:3px solid {TEAL};
  border-radius:10px; padding:12px; }}
.flow .step b {{ color:{p['text']}; }} .flow .step span {{ color:{p['body']}; font-size:0.86rem; }}
.flow .step .n {{ color:{TEAL}; font-weight:700; font-size:0.8rem; letter-spacing:.05em; }}
.flow .arr {{ align-self:center; color:{p['muted']}; font-size:1.3rem; }}
.note {{ border-left:3px solid {ORANGE}; background:{p['note_bg']}; padding:10px 14px; border-radius:0 8px 8px 0;
  color:{p['body']}; font-size:0.9rem; margin:6px 0 12px 0; }}
.hint {{ color:{p['muted']}; font-size:0.85rem; }}
.gold {{ color:{p['gold_text']}; font-weight:700; }}
.truthtxt {{ color:{p['truth_text']}; font-weight:700; }}
</style>"""


def apply_theme():
    st.markdown(css(), unsafe_allow_html=True)


def style_fig(fig, h=360, legend=True):
    p = P()
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color=p["text"], height=h,
                      margin=dict(l=20, r=20, t=40, b=20), showlegend=legend,
                      legend=dict(orientation="h", y=-0.22), hoverlabel=dict(bgcolor=p["hover"], font_color=p["text"]))
    fig.update_xaxes(gridcolor=p["line"], zerolinecolor=p["line"])
    fig.update_yaxes(gridcolor=p["line"], zerolinecolor=p["line"])
    return fig
