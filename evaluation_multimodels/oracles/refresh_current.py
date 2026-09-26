"""从当前 content 和测试合同生成离线清单；不改写 gold 或继承历史审核。"""
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import csv
import hashlib
import json
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
DATE = "2026-09-23"
sys.path.insert(0, str(ROOT / "tech/chatflow/poc"))
from capsule_loader import parse_capsule
from capsule_content import parse_ground_branches
from ground import extract_heading_path_section


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def ref_error(ref):
    name, _, anchor = ref.partition("#")
    if name.startswith("knowledge/"):
        name = "content/" + name
    path = ROOT / name
    if not path.is_file():
        return "文件不存在"
    if anchor:
        try:
            extract_heading_path_section(path.read_text(), anchor)
        except ValueError as exc:
            return str(exc)
    return None


def main():
    files = {str(p.relative_to(ROOT)): digest(p)
             for p in sorted((ROOT / "content").rglob("*.md"))}
    snapshot_id = "sha256:" + hashlib.sha256(json.dumps(files, sort_keys=True).encode()).hexdigest()
    write(f"source-snapshot-{DATE}.json", {"snapshot_id": snapshot_id, "files": files,
          "scope": "当前 content Markdown；仅记录版本，不表示法律审核或已绑定测试 gold"})
    capsules = {}
    for p in sorted((ROOT / "content/capsule").glob("*.md")):
        if p.name in {"AGENTS.md", "template.md"}:
            continue
        c = parse_capsule(p)
        branches = parse_ground_branches(c.ground) or []
        name = str(p.relative_to(ROOT))
        capsules[c.id] = {"capsule_ref": name, "ground_ref": name + "#ground",
            "answer_section_refs": [name + "#" + s for s in
                ("applicability", "render_policy", "recognize", "act")
                if not ref_error(name + "#" + s)],
            "configured_ground_node_ids": list(dict.fromkeys(b.node_id for b in branches)),
            "ground_branches": [asdict(b) for b in branches]}
    nodes, content_errors = {}, []
    for p in sorted((ROOT / "content/knowledge/wiki/nodes").glob("*.md")):
        meta = yaml.safe_load(p.read_text().split("---", 2)[1])
        nodes[p.stem] = {"wiki_ref": str(p.relative_to(ROOT)),
                         "source_refs": meta.get("source_refs", []),
                         "source_roles": meta.get("source_roles", {})}
        for ref in meta.get("source_refs", []):
            if error := ref_error(ref):
                content_errors.append({"node": p.stem, "ref": ref, "error": error})
    for cid, c in capsules.items():
        for node in c["configured_ground_node_ids"]:
            if node not in nodes:
                content_errors.append({"capsule": cid, "node": node, "error": "节点不存在"})
    write(f"content-index-{DATE}.json", {"snapshot_id": snapshot_id,
          "capsules": capsules, "nodes": nodes, "reference_errors": content_errors})
    rows, case_files = [], {}
    for p in sorted((ROOT / "evaluation_multimodels/test-cases").rglob("TC-*.yaml")):
        if p.parent.name not in {"test-cases", "proposed"}:
            continue
        case = yaml.safe_load(p.read_text())
        case_files[str(p.relative_to(ROOT))] = digest(p)
        mirror = ROOT / "evaluation" / p.relative_to(ROOT / "evaluation_multimodels")
        other = yaml.safe_load(mirror.read_text()) if mirror.is_file() else None
        mirror_turns = {t["turn"]: t for t in other["turns"]} if other else {}
        for t in case["turns"]:
            e = t["expected"]
            r = e.get("reference_oracle", {})
            g = r.get("ground", {})
            errors, current_contracts = [], {}
            for route in e.get("route_ids", []):
                if route in capsules:
                    current_contracts[route] = capsules[route]
                elif route in {"baseline", "crisis_sop"}:
                    name = "content/sops/" + ("crisis-sop.md" if route == "crisis_sop" else "main-agent-baseline-sop.md")
                    current_contracts[route] = {"capsule_ref": name, "ground_ref": None,
                        "answer_section_refs": [name], "configured_ground_node_ids": []}
                else:
                    errors.append({"route": route, "error": "未注册路由"})
                    continue
                old = r.get("route_contracts", {}).get(route, {})
                new = current_contracts[route]
                for key in ("capsule_ref", "ground_ref", "answer_section_refs", "configured_ground_node_ids"):
                    if old.get(key) != new[key]:
                        errors.append({"route": route, "field": key, "error": "合同与当前内容不一致"})
            refs = e.get("source_refs", []) + e.get("wiki_refs", []) + g.get("background_source_refs", [])
            for contract in r.get("route_contracts", {}).values():
                refs += contract.get("answer_section_refs", [])
            for ref in dict.fromkeys(refs):
                if error := ref_error(ref):
                    errors.append({"ref": ref, "error": error})
            for node in g.get("required_node_ids", []) + g.get("background_node_ids", []):
                if node not in nodes:
                    errors.append({"node": node, "error": "旧节点已不存在；须重新裁定语义映射"})
            if g.get("activation") == "required" and (not e.get("source_refs") or not e.get("wiki_refs")):
                errors.append({"error": "required 缺少 source_refs 或 wiki_refs"})
            runtime_gaps = {route: sorted(set(g.get("required_node_ids", [])) - set(c["configured_ground_node_ids"]))
                            for route, c in current_contracts.items()}
            runtime_gaps = {k: v for k, v in runtime_gaps.items() if v}
            rows.append({"case": case["id"], "turn": t["turn"], "proposal": p.parent.name == "proposed",
                "user": t["user"], "snapshot_id": snapshot_id,
                "recorded_snapshot_id": r.get("snapshot_id"),
                "snapshot_matches": r.get("snapshot_id") == snapshot_id,
                "mirror_matches": mirror_turns.get(t["turn"]) == t,
                "ground": g.get("activation"), "source_gaps": r.get("source_gaps", []),
                "recorded_expected": e, "current_route_contracts": current_contracts,
                "reference_errors": errors, "runtime_ground_gaps": runtime_gaps,
                "refresh_status": "inventory_only_not_semantically_approved"})
    write(f"reference-refresh-{DATE}.json", rows)
    canonical = [r for r in rows if not r["proposal"]]
    summary = {"status": "NEEDS_REMEDIATION" if content_errors or any(r["reference_errors"] or not r["snapshot_matches"] or not r["mirror_matches"] for r in rows) else "PASS",
        "meaning": "当前文件/章节/配置审计，不是法律审核；旧 gold 保持原审核身份，新清单未获语义审核。",
        "snapshot_id": snapshot_id, "case_files": case_files,
        "case_count": len({r["case"] for r in canonical}), "turn_count": len(canonical),
        "proposed_turn_count": len(rows) - len(canonical),
        "ground_counts": dict(Counter(r["ground"] for r in canonical)),
        "content_reference_error_count": len(content_errors),
        "turns_with_reference_errors": sum(bool(r["reference_errors"]) for r in canonical),
        "turns_with_snapshot_mismatch": sum(not r["snapshot_matches"] for r in canonical),
        "turns_with_mirror_difference": sum(not r["mirror_matches"] for r in canonical),
        "turns_with_recorded_source_gaps": sum(bool(r["source_gaps"]) for r in canonical)}
    write(f"reference-integrity-{DATE}.json", summary)
    with (OUT / f"reference-review-{DATE}.csv").open("w", newline="", encoding="utf-8-sig") as f:
        fields = ["case", "turn", "proposal", "user", "ground", "source_gaps", "reference_errors",
                  "runtime_ground_gaps", "snapshot_matches", "mirror_matches", "refresh_status"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(row[k], ensure_ascii=False) if isinstance(row[k], (dict, list)) else row[k] for k in fields})
    print(json.dumps({k: v for k, v in summary.items() if k != "case_files"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
