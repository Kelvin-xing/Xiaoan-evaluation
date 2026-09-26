"""Read-only, paged access to one complete frozen result generation."""
from pathlib import Path
import hashlib
import json


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(dumps(value).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class EvidenceStore:
    def __init__(self, results):
        from xiaoan_eval_core.results import validate_complete_results
        self.path = Path(results).resolve()
        self.file_sha256 = file_hash(self.path)
        self.result = validate_complete_results(json.loads(self.path.read_text()))
        self.generation = self.result["result_generation"]
        self.sources = {}
        self.exposed = {}
        self.journal = []
        for section in ("manifest", "plan", "aggregates", "answers", "inventories", "envelopes", "stages", "provenance"):
            data = self.result[section]
            items = list(enumerate(data)) if isinstance(data, list) else [(None, data)]
            for key, value in items:
                pointer = "/" + section + ("/" + str(key) if key is not None else "")
                self.sources[pointer] = {"ref": pointer, "digest": digest(value), "data": value}

    def catalog(self):
        from .presentation import source_label
        return {"generation": self.generation, "core_digest": self.result["core_digest"],
                "source_index": [{"ref": k, "label":source_label(self.result,k), "digest": v["digest"]} for k, v in self.sources.items()],
                "tools": "read_evidence(ref,offset=0,limit=12000); get_case(case_id); read_artifact(path,offset=0,limit=12000)",
                "notice": "Index is not read evidence. Read pages before citing. Numbers use /aggregates facts only."}

    def query(self, name, args):
        if name == "get_case":
            ids = {a["answer_id"] for a in self.result["answers"] if a["case_id"] == args["case_id"]}
            value = {"refs": [r for r, s in self.sources.items() if isinstance(s["data"], dict) and s["data"].get("answer_id") in ids]}
        elif name in {"read_evidence", "read_artifact"}:
            if name == "read_artifact":
                rel = args["path"]
                artifact = next((a for a in self.result["artifacts"] if a.get("path") == rel), None)
                if artifact is None:
                    raise ValueError("artifact not in frozen index")
                path = (self.path.parent / rel).resolve()
                if not path.is_relative_to(self.path.parent):
                    raise ValueError("artifact escapes result directory")
                if file_hash(path) != artifact["sha256"]:
                    raise ValueError("artifact digest mismatch")
                ref = "/artifacts/" + rel
                source = {"ref": ref, "digest": artifact["sha256"], "data": path.read_text()}
                self.sources[ref] = source
            else:
                ref = args["ref"]
                source = self.sources[ref]
            text = dumps(source["data"])
            offset = int(args.get("offset", 0))
            limit = min(12000, int(args.get("limit", 12000)))
            if offset < 0 or limit < 1:
                raise ValueError("invalid page bounds")
            chunk = text[offset:offset + limit]
            self.exposed.setdefault(ref, []).append((offset, offset + len(chunk)))
            value = {"ref": ref, "digest": source["digest"], "generation": self.generation, "text": chunk,
                     "offset": offset, "next_offset": offset + limit if offset + limit < len(text) else None, "total_characters": len(text)}
        else:
            raise ValueError("unsupported read-only tool")
        self.journal.append({"tool": name, "args": args, "result": value})
        return value

    def was_exposed(self, ref, text):
        if ref not in self.sources:
            return False
        raw = dumps(self.sources[ref]["data"])
        # Text must be in a delivered page, not just in an indexed source.
        encoded = json.dumps(text, ensure_ascii=False)[1:-1]
        return any(encoded in raw[start:end] for start, end in self.exposed.get(ref, []))

    def unchanged(self):
        return file_hash(self.path) == self.file_sha256
