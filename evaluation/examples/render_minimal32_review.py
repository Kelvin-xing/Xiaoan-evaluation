"""Local, escaped HTML review of the exact frozen answers and audit evidence."""
from pathlib import Path
import json,html
ROOT=Path(__file__).resolve().parents[2]
def esc(s):return html.escape(str(s))
def render():
    out=ROOT/'evaluation/runs/2026-09-13-minimal32-oracle-completion'
    summary=json.loads((out/'summary.json').read_text());details=json.loads((out/'evidence-review.json').read_text());matrix=json.loads((out/'metric-matrix.json').read_text())
    cases=json.loads((ROOT/'evaluation/oracles/minimal32-completion/review.json').read_text());inputs={(r['case_id'],r['turn']):r for r in cases}
    parts=['''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>32案 Oracle 与证据复审</title><style>body{font:15px/1.65 system-ui,sans-serif;max-width:1150px;margin:35px auto;padding:0 20px;background:#f8fafc;color:#18283c}h1{font-size:27px}h2{font-size:19px}.note{padding:14px;border-left:4px solid #b47818;background:#fff9eb}details{background:white;border:1px solid #dbe2ea;border-radius:8px;margin:12px 0;padding:12px}summary{cursor:pointer;font-weight:650}table{border-collapse:collapse;width:100%;font-size:13px}td,th{padding:7px;border-bottom:1px solid #e3e8ee;text-align:left;vertical-align:top}blockquote{margin:8px 0;padding:12px;background:#f1f5f9;white-space:pre-wrap}code{word-break:break-all}li{margin:4px 0}.muted{color:#65748b}</style><h1>32案 × 96轮：Oracle、运行证据与不可用原因</h1>''']
    parts.append(f'<p>有回答 92/96；有效归因 {summary["attribution_available"]}/92；逐指标记录 {summary["row_count"]} 条。</p>')
    parts.append('<p class="note">这是冻结运行的离线复审。新分流/安全标签和回答修订是待人工审核草案；标签命中不表示模型因果依赖 capsule。护栏拒绝、后续未执行、缺证据与质量失败分别记录。</p>')
    parts.append('<h2>按指标的原因分类</h2><table><tr><th>指标</th><th>原因计数</th></tr>')
    for metric,counts in summary['by_metric'].items():parts.append(f'<tr><td>{esc(metric)}</td><td>{esc(json.dumps(counts,ensure_ascii=False))}</td></tr>')
    parts.append('</table><h2>逐轮审核</h2><p>可用浏览器查找搜索 TC 编号、指标或引用文字。</p>')
    for d in details:
        cid=d['case_id'];turn=d['turn'];item=inputs[cid,turn];e=item['current_expected'];s=d['semantic_review'];a=d.get('attribution') or {}
        parts.append(f'<details><summary>{esc(cid)} / T{turn} · 实际 {esc(d["actual_route"])} → preferred {esc(e["preferred_route_id"])} · 归因 {esc(a.get("status","UNAVAILABLE"))}</summary>')
        parts.append(f'<p><b>用户：</b>{esc(item["user"])}</p><p><b>可接受路由：</b>{esc(", ".join(e["route_ids"]))}；<b>安全：</b>{esc(", ".join(e["safety_levels"]))}；<b>须危机接管：</b>{esc(s["crisis_required"])}</p>')
        parts.append(f'<p><b>独立依据：</b>{esc(s["risk_basis"])}</p><p><b>替代做法：</b>{esc("；".join(s["allowed_alternatives"]))}</p><p><b>争议：</b>{esc(s["review_issue"])}</p>')
        if s['response_amendments']:
            parts.append('<p class="note"><b>修订提案，未替换历史 gold：</b>'+esc('；'.join(s['response_amendments']))+'</p>')
            parts.append('<p><b>历史 Judge 对照的原必要要求：</b>'+esc('；'.join(item['original_expected']['response_oracle']['required_claims']))+'</p>')
        for label,key in [('必要回应（候选稿）','required_claims'),('禁止行为','forbidden_claims')]:
            parts.append(f'<p><b>{label}</b></p><ul>'+''.join('<li>'+esc(v)+'</li>' for v in s['response_candidate'][key])+'</ul>')
        parts.append(f'<p><b>原回答</b></p><blockquote>{esc(d["answer"] or "本轮无回答；见执行原因")}</blockquote><p class="muted">snapshot：{esc(d["snapshot_id"])}</p>')
        parts.append('<table><tr><th>检查</th><th>状态 / 阻塞</th><th>描述性结果（非未审核门槛）</th></tr>')
        for r in matrix:
            if (r['case_id'],r['turn'])==(cid,turn):parts.append(f'<tr><td>{esc(r["metric"])}</td><td>{esc(r["status"])} / {esc(", ".join(r["blockers"]))}</td><td>{esc(json.dumps(r["descriptive_value"],ensure_ascii=False))}</td></tr>')
        parts.append('</table>')
        original=d.get('original_response_assessment') or {}
        parts.append('<p><b>原回答 Oracle 的逐项判断</b></p><ul>')
        for j in original.get('items',[]):parts.append(f'<li>{esc(j["id"])}：{esc(j["verdict"])} — {esc(j["reason"])}</li>')
        parts.append('</ul><p><b>独立归因的原回答引文 → 实际注入引文</b></p>')
        for claim in a.get('assessment',{}).get('claims',[]):
            parts.append(f'<blockquote>{esc(claim["answer_span"]["text"])}</blockquote><ul>')
            for rel in claim['relations']:
                q=(rel.get('evidence_span') or {}).get('text','无支持引文')
                parts.append(f'<li>{esc(rel["relation"])} · {esc(rel.get("layer"))} · <code>{esc(rel.get("evidence_ref"))}</code><blockquote>{esc(q)}</blockquote></li>')
            parts.append('</ul>')
        parts.append('</details>')
    parts.append('</html>');(out/'review.html').write_text('\n'.join(parts));print(out/'review.html')
if __name__=='__main__':render()
