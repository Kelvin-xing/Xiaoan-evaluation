"""Offline acceptance checks: no network or paid calls."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import run


class BaselineTests(unittest.TestCase):
    def test_self_judging_can_be_included(self):
        rule = run.load_rating_rule(run.EVALUATION / "ratings rule.yml")
        def judge(*args):
            return {"text": json.dumps({
                "red_lines": [{"id": r.id, "triggered": False, "evidence": []} for r in rule.red_lines],
                "dimensions": {m.name: 2 for m in rule.modules},
            })}
        rows = run.run_matrix(
            [{"id": "TC-01", "turns": [{"turn": 1, "user": "hello"}]}],
            [run.ModelSpec("gpt", "same-model", "latest")],
            [run.ModelSpec("gpt", "same-model", "judge")],
            subject_transport=lambda *_: {"text": "answer"}, judge_transport=judge,
            rating_rule=rule, isolate_self_judging=False,
        )
        self.assertTrue(rows[0]["self_judging"])
        self.assertTrue(rows[0]["primary_eligible"])

    def test_native_history_and_no_instructions_for_both_api_formats(self):
        for provider in ("gpt", "claude"):
            lane = run.BareConversation()
            spec = run.ModelSpec(provider, "test", "latest")
            bodies = []

            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *args):
                    pass

                def read(self):
                    return json.dumps({"text": "answer", "content": [{"type": "text", "text": "answer"}]}).encode()

            def http(request, **kwargs):
                bodies.append(json.loads(request.data))
                return Response()

            lane.transport.__globals__["urlopen"] = http
            with patch.dict(run.providers.os.environ, {f"XIAOAN_{provider.upper()}_API_KEY": "fake-local-test", "XIAOAN_CLAUDE_API_MODE": "auto"}):
                lane.start_case(spec, "TC-01")
                lane(spec, "first")
                lane(spec, "second")
                lane.end_case(spec, "TC-01")
                lane.start_case(spec, "TC-04")
                lane(spec, "new case")
            self.assertEqual(bodies[1]["messages"], [
                {"role": "user", "content": "first"},
                {"role": "assistant", "content": "answer"},
                {"role": "user", "content": "second"},
            ])
            self.assertEqual(bodies[2]["messages"], [{"role": "user", "content": "new case"}])
            self.assertFalse(set(bodies[0]) & {"system", "tools", "response_format"})
            self.assertIsNot(run.providers.multimodel_transport.__globals__["urlopen"], http)

    def test_failure_stops_remaining_turns(self):
        lane = run.BareConversation()
        lane.start_case(None, "case")
        calls = []

        def failed(*args):
            calls.append(1)
            raise RuntimeError("sensitive provider error")

        lane.transport = failed
        for _ in range(2):
            with self.assertRaises(RuntimeError) as error:
                lane(None, "question")
            self.assertNotIn("sensitive", str(error.exception))
        self.assertEqual(len(calls), 1)

    def test_minimal32_matrix_reports_and_resume_offline(self):
        rule = run.load_rating_rule(run.EVALUATION / "ratings rule.yml")
        cases = [run.load_case(run.EVALUATION / "test-cases" / f"TC-{n:02d}.yaml", rule).case for n in run.MINIMAL32]
        self.assertEqual(len(cases), 32)
        self.assertEqual(sum(len(c.turns) for c in cases), 96)
        subjects = [run.ModelSpec("gpt", "mock-subject", "latest")]
        judges = [run.ModelSpec("claude", "mock-judge", "judge")]

        def judge(spec, prompt):
            return {"text": json.dumps({
                "red_lines": [{"id": r.id, "triggered": False, "evidence": []} for r in rule.red_lines],
                "dimensions": {m.name: 2 for m in rule.modules},
            })}

        with tempfile.TemporaryDirectory() as directory:
            out = Path(directory)
            kwargs = dict(subject_transport=lambda *_: {"text": "mock answer"}, judge_transport=judge,
                          rating_rule=rule, checkpoint_path=out / "checkpoint.jsonl")
            rows = run.run_matrix(cases, subjects, judges, **kwargs)
            self.assertEqual(len(rows), 96)
            self.assertTrue(all(r["status"] == "PASS" for r in rows))
            for row in rows:
                self.assertAlmostEqual(row["weighted_score"], 2)
            run.write_matrix_workbook(rows, out / "results.xlsx")
            self.assertTrue((out / "results.xlsx").exists())
            self.assertIn("mock-subject", run.render_matrix_report(rows))
            def no_call(*args):
                self.fail("completed checkpoint should not call provider")
            kwargs.update(subject_transport=no_call, judge_transport=no_call)
            resumed = run.run_matrix(cases, subjects, judges, resume=True, retry_unavailable=True, **kwargs)
            self.assertEqual(len(resumed), 96)


if __name__ == "__main__":
    unittest.main()
