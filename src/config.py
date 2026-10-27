"""앱 상수: 이름, 번들 위치, 메뉴."""
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
REPO_DIR = APP_DIR.parent
BUNDLE_DIR = Path(os.getenv("CASMI_DEMO_BUNDLE", APP_DIR / "data" / "demo_bundle"))
APP_NAME = "MS/MS 구조 추정 엔진 데모"
TAGLINE = "Kaggle CASMI 2026 데이터로 개발 중인 엔진 · 스펙트럼 → 구조 후보 Top-25 + 근거"
BUILD_CMD = "/mnt/14903B8A903B717A/venvs_1T/.venv_p313/bin/python scripts/build_demo_bundle.py"
MENU = ["개요", "데모 데이터 선택", "입력 데이터", "엔진 처리 과정", "최종 결과", "예시 보고서", "MetID 시연 (반응성 대사체)",
        "15개 성능 요약"]
SCEN_TEXT = {
    "C1": ("공개 스펙트럼이 있는 화합물", "같은 화합물의 MS/MS가 공개 라이브러리(GNPS, MoNA 등)에 있는 경우. "
           "데모에서는 시험 장비(timsTOF) 원본 기록만 지우고 다른 기관의 스펙트럼은 남겼습니다."),
    "C2": ("구조는 알려졌지만 스펙트럼이 없는 화합물", "화합물 DB에는 구조가 있지만 어떤 라이브러리에도 MS/MS가 없는 경우. "
           "데모에서는 이 구조의 모든 스펙트럼(입체·호변 변형 포함)을 참조에서 지웠습니다."),
    "C3": ("우리 참조 데이터에 없는 신규 구조", "학습용 구조 목록에도 없고 스펙트럼도 없는 경우. 정답은 외부 구조 DB(COCONUT, PubChem)나 "
           "엔진이 만든 유도체 후보로만 찾을 수 있습니다."),
    "MetID": ("MetID 시연 (반응성 대사체)", "아세트아미노펜 → NAPQI → 글루타티온(GSH) 포합체 흐름으로 반응성 대사체 경고 기능을 보여 주는 별도 예시. "
              "C1~C3 성능 통계에는 넣지 않습니다."),
}
ALERT_CAUTION = ("반응성 대사체 경고는 '확인해 볼 가능성'을 알리는 표시이며 확정이 아닙니다. GSH 포합체 신호는 놓치는 경우와 우연히 겹치는 경우가 "
                 "모두 있고, 구조 경고는 위험 부분구조가 있다는 뜻일 뿐 실제 생체활성화 여부는 포획 실험으로 확인해야 합니다.")
