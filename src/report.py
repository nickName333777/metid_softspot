"""분자 1개의 분석 보고서(HTML 한 파일). 외부 리소스 없이 구조 그림·스펙트럼을 SVG로 넣어 메일·인쇄에 그대로 쓸 수 있다."""
import datetime as dt
import html

from . import config as C

ORANGE, TEAL, GREY = "#E4572E", "#2A9D8F", "#9aa7b8"


def _e(x):
    return html.escape("" if x is None else str(x))


def _f(x, spec):
    return "" if x is None else format(x, spec)


def spectrum_svg(sp, ann=None, w=720, h=230):
    mz, it = sp["clean_mz"], sp["clean_it"]
    if not mz:
        return ""
    lo = max(0.0, min(mz) - 20); hi = max(max(mz), sp["prec"]) + 20
    X = lambda v: 40 + (v - lo) / (hi - lo) * (w - 60)
    Y = lambda v: h - 30 - (max(v, 0.0) ** 0.5) * (h - 60)        # √강도: 약한 조각 피크도 보이게
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" font-family="sans-serif" font-size="10">',
           f'<line x1="40" y1="{h - 30}" x2="{w - 20}" y2="{h - 30}" stroke="#333"/>']
    step = 50 if hi - lo < 600 else 100
    t = (int(lo / step) + 1) * step
    while t < hi:
        out.append(f'<line x1="{X(t):.1f}" y1="{h - 30}" x2="{X(t):.1f}" y2="{h - 26}" stroke="#333"/>'
                   f'<text x="{X(t):.1f}" y="{h - 14}" text-anchor="middle" fill="#333">{t}</text>')
        t += step
    match = ann["match"] if ann else [False] * len(mz)
    for x, y, mt in zip(mz, it, match):
        out.append(f'<line x1="{X(x):.1f}" y1="{Y(0):.1f}" x2="{X(x):.1f}" y2="{Y(y):.1f}" stroke="{TEAL if mt else GREY}" stroke-width="1.6"/>')
    for k in sorted(range(len(mz)), key=lambda k: -it[k])[:6]:
        out.append(f'<text x="{X(mz[k]):.1f}" y="{Y(it[k]) - 4:.1f}" text-anchor="middle" fill="#333">{mz[k]:.3f}</text>')
    out.append(f'<line x1="{X(sp["prec"]):.1f}" y1="{Y(0)}" x2="{X(sp["prec"]):.1f}" y2="{Y(1.05):.1f}" stroke="{ORANGE}" stroke-dasharray="3,3"/>'
               f'<text x="{X(sp["prec"]):.1f}" y="14" text-anchor="middle" fill="{ORANGE}">전구체 {sp["prec"]:.4f}</text>'
               f'<text x="{w - 20}" y="{h - 2}" text-anchor="end" fill="#555">m/z</text></svg>')
    return "".join(out)


def build_report(mol, index, conf_level, conf_note):
    m, tr = mol["meta"], mol["truth"]
    cands = mol["candidates"][:mol["n_shown"]]
    top5 = cands[:5]
    t1 = cands[0] if cands else None
    sp = max(mol["spectra"], key=lambda s: len(s["clean_mz"]))
    ann = sp["ann"].get("top1")
    today = dt.date.today().isoformat()
    rank = f"{tr['rank']}위" if tr["rank"] else ("25위 밖" if tr["in_candidates"] else "후보에 없음")
    rows5 = "".join(
        f"<tr class='{'truth' if c['is_truth'] else ''}'><td>{c['rank']}</td><td class='mol'>{c['svg']}</td>"
        f"<td>{_e(c['formula'])}<br><span class='s'>{_e(c['smiles'][:90])}</span></td><td>{c['score']:.2f}<br><span class='s'>{c['gap']:+.2f}</span></td>"
        f"<td>{c['lib']:.2f}</td><td>{c['ap3']:.2f}</td><td>{c['frag']:.2f}</td><td>{c['fp_tc']:.2f}</td><td>{_e(c['src'])}</td>"
        f"<td>{'★' if c['is_truth'] else ''}</td></tr>" for c in top5)
    peaks = ""
    if ann:
        ks = sorted(range(len(sp["clean_mz"])), key=lambda k: -sp["clean_it"][k])[:10]
        peaks = "".join(
            f"<tr><td>{sp['clean_mz'][k]:.4f}</td><td>{sp['clean_it'][k]:.3f}</td>"
            f"<td>{'설명됨' if ann['match'][k] else '-'}</td><td>{_f(ann['ion'][k], '.4f')}</td>"
            f"<td>{_f(ann['dh'][k], '+d')}</td><td>{_e(ann['loss'][k])}</td>"
            f"<td class='s'>{_e((ann['frag_smiles'][k] or '')[:70])}</td></tr>" for k in ks)
    fam = ""
    if t1 and t1.get("shap"):
        items = sorted(t1["shap"]["family"].items(), key=lambda x: -x[1])
        fam = "".join(f"<tr><td>{_e(k)}</td><td>{v:+.2f}</td></tr>" for k, v in items if abs(v) >= 0.01)
    lib = "".join(f"<li>유사도 {x['sim']:.2f} · {_e(', '.join(x['libs']))}{' (정답과 같은 구조)' if x['same_as_truth'] else ' (정답과 다른 구조)'}</li>"
                  for x in mol["library"][:3]) or "<li>같은 질량 창의 참조 스펙트럼 없음</li>"
    an = "".join(f"<li>스펙트럼 유사도 {x['sim']:.2f}, 질량 차 {x['delta']:+.4f} Da {('· ' + _e(x['delta_label'])) if x['delta_label'] else ''}</li>"
                 for x in mol["analogs"][:3]) or "<li>유사 스펙트럼 없음</li>"
    ce = ", ".join(f"{x:g}" for x in m["ce"]) or "-"
    al = mol.get("alerts") or {}
    sig = al.get("signal", {"level": "-", "primary": [], "support": []})
    sig_rows = "".join(f"<tr><td>{_e(sp['adduct'])}</td><td>{_e(x['label'])}</td><td>{x['mz']:.4f}</td><td>{x['rel']:.3f}</td>"
                       f"<td>{x['err_mda']:+.1f}</td></tr>" for sp in mol["spectra"] for x in sp.get("alerts", []))
    st_rows = "".join(f"<tr><td>{c['rank']}</td><td>{_e(c['formula'])}</td><td>{_e(' · '.join(x['name'] for x in c['struct_alerts']) or '없음')}</td>"
                      f"<td>{_e(' / '.join(x['note'] for x in c['struct_alerts']))}</td></tr>"
                      for c in top5 if c.get("struct_alerts") is not None)
    theory = ('<div class="warn"><b>이론 예시 입력</b>: 이 시료의 스펙트럼은 실측이 아니라 알려진 GSH 포합체 조각 규칙으로 계산한 '
              '예시입니다(강도 임의). 경고 기능 시연용이며 순위는 성능 근거가 아닙니다.</div>' if m.get("theoretical") else "")
    return f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>분석 보고서 {_e(m['mid'])}</title>
<style>
body{{font-family:'Noto Sans KR','Malgun Gothic',sans-serif;color:#1d2733;margin:0;background:#f4f6f9}}
.wrap{{max-width:980px;margin:0 auto;background:#fff;padding:32px 40px 40px}}
h1{{font-size:22px;margin:0 0 4px}} h2{{font-size:16px;border-bottom:2px solid {TEAL};padding-bottom:4px;margin-top:28px}}
.sub{{color:#5b6b7f;font-size:13px}} .badge{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;font-weight:600;background:#e6f4f2;color:#1f6f66;margin-right:6px}}
.badge.o{{background:#fde9e3;color:#a63c1d}}
table{{border-collapse:collapse;width:100%;font-size:12.5px}} th,td{{border:1px solid #dde3ea;padding:5px 7px;vertical-align:middle;text-align:left}}
th{{background:#f0f3f7}} tr.truth td{{background:#fff4ef}} td.mol svg{{width:150px;height:auto}} .s{{color:#6b7a8c;font-size:11px;word-break:break-all}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} .box{{border:1px solid #dde3ea;border-radius:8px;padding:12px}}
.box svg{{max-width:100%;height:auto}} .warn{{background:#fff8e6;border-left:4px solid #e0a800;padding:10px 14px;font-size:12.5px}}
ul{{margin:4px 0;padding-left:18px;font-size:13px}}
</style></head><body><div class="wrap">
<h1>MS/MS 구조 추정 분석 보고서 <span class="sub">(예시)</span></h1>
<div class="sub">시료 ID {_e(m['mid'])} · 작성일 {today} · {_e(C.TAGLINE)}</div>
{theory}
<h2>1. 요약</h2>
<div class="grid"><div class="box"><b>엔진 1위 후보</b><br>{t1['svg'] if t1 else ''}
<div class="sub">{_e(t1['formula'] if t1 else '')} · 점수 {t1['score']:.2f} · 출처 {_e(t1['src'] if t1 else '')}</div></div>
<div class="box"><b>판정 요약</b><ul>
<li>제시 후보 수: Top-{len(cands)} (검토 후보 {mol['funnel']['n_cand']:,}개)</li>
<li>1위 신뢰도 등급: <span class="badge">{_e(conf_level)}</span><br><span class="s">{_e(conf_note)}</span></li>
<li>검증용 정답 구조의 순위: <span class="badge o">{rank}</span> (시나리오 {_e(m['scenario'])}: {_e(C.SCEN_TEXT[m['scenario']][0])})</li>
<li>라이브러리 직접 일치:<ul>{lib}</ul></li><li>가장 가까운 유사 스펙트럼:<ul>{an}</ul></li></ul></div></div>
<h2>2. 입력 조건</h2>
<table><tr><th>스펙트럼 수</th><td>{m['n_spec']}</td><th>이온 형태</th><td>{_e(', '.join(m['adducts']))}</td></tr>
<tr><th>이온화 모드</th><td>{_e(', '.join(m['modes']))}</td><th>충돌 에너지</th><td>{_e(ce)} eV</td></tr>
<tr><th>장비</th><td>{_e(', '.join(m['instrument']))}</td><th>계산된 중성 질량</th><td>{m['target_mass']:.4f} Da (후보 창 ±{mol['window']['ppm']:g} ppm)</td></tr></table>
<p class="sub">대표 스펙트럼 ({_e(sp['adduct'])}, 전처리 후 피크 {len(sp['clean_mz'])}개). 청록 = 1위 후보의 조각으로 설명되는 피크 (세로축 √상대 강도).</p>
{spectrum_svg(sp, ann)}
<h2>3. 후보 Top-5</h2>
<table><tr><th>순위</th><th>구조</th><th>화학식 / SMILES</th><th>점수<br>(1위 대비)</th><th>라이브러리</th><th>유사체</th><th>조각 설명</th><th>FP-net</th><th>출처</th><th>정답</th></tr>{rows5}</table>
<h2>4. 근거 피크 (1위 후보 기준, 강한 피크 10개)</h2>
<table><tr><th>m/z</th><th>상대 강도</th><th>조각 설명</th><th>조각 이온</th><th>H 이동</th><th>중성 손실</th><th>조각 구조</th></tr>{peaks}</table>
<h2>5. 1위 후보 점수의 근거 계열별 기여 (평균 후보 대비)</h2>
<table><tr><th>근거 계열</th><th>기여</th></tr>{fam}</table>
<h2>6. 주의 플래그 (반응성 대사체)</h2>
<p>GSH 포합체 스펙트럼 신호: <span class="badge o">{_e(sig['level'])}</span> {_e(', '.join(sig['primary'] + sig['support']))}
<span class="s">(양이온 중성 손실 129.043 Da / 음이온 조각 m/z 272.089, 보조 254·210·143·128)</span></p>
{('<table><tr><th>스펙트럼</th><th>신호</th><th>m/z</th><th>상대 강도</th><th>오차 (mDa)</th></tr>' + sig_rows + '</table>') if sig_rows else ''}
<p>후보 Top-5 구조 경고:</p>
<table><tr><th>순위</th><th>화학식</th><th>구조 경고</th><th>의미</th></tr>{st_rows}</table>
<p class="s">{_e(C.ALERT_CAUTION)}</p>
<h2>7. 한계 및 주의</h2>
<div class="warn"><ul>
<li>이 보고서는 구조 <b>후보</b>를 제시하며 구조를 확정하지 않습니다. 확정에는 표준품 비교, NMR 등 추가 확인이 필요합니다.</li>
<li>점수는 같은 시료의 후보끼리 비교하는 상대값이며 확률이 아닙니다. 신뢰도 등급은 검증용 천연물 분자의 결과로 환산한 참고값입니다.</li>
<li>입체·호변 이성질체는 구분하지 않습니다 (InChIKey 앞 14자리 기준). 위치 이성질체는 스펙트럼만으로 구분이 어려울 수 있습니다.</li>
<li>후보는 검색한 구조 DB와 엔진이 만든 유도체 범위 안에서만 나옵니다. 범위 밖 구조는 순위에 오를 수 없습니다.</li>
<li>엔진은 Kaggle CASMI 2026 천연물 데이터로 개발 중이며, 약물 대사체(MetID)용 질량 이동·대사 반응 규칙은 향후 PoC에서 확장할 예정입니다.</li>
<li>이 예시는 정답을 아는 검증용 분자로 만들었습니다. 실제 미지 시료 보고서에는 '정답 순위' 항목이 없습니다.</li></ul></div>
</div></body></html>"""
