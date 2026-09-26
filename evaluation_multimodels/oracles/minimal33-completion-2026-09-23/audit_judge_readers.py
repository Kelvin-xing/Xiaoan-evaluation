"""无网络审计：捕获真实主Judge请求，检验元数据与硬约束的区别。"""
from pathlib import Path
from dataclasses import replace
from unittest.mock import patch
from types import SimpleNamespace
import copy,importlib.util,json,os,sys
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'evaluation'))
os.chdir(ROOT/'evaluation')
def module(name,path):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m
fixture=module('pipeline_fixture',ROOT/'evaluation/tests/test_pipeline.py')
afixture=module('attribution_fixture',ROOT/'evaluation/tests/test_attribution_client.py')
from xiaoan_eval.oracle_judge import contract
from xiaoan_eval.attribution_client import build_attribution_request
from xiaoan_eval.cases import load_case
import company_eval_plugins as plugin
loaded=load_case(ROOT/'evaluation/test-cases/TC-29.yaml',fixture.RULE).case
semantic=loaded.turns[0].expected.reference_oracle['semantic_alignment']
case=fixture._case();turn=case.turns[0];expected=replace(turn.expected,reference_oracle=loaded.turns[0].expected.reference_oracle)
case=replace(case,turns=(replace(turn,expected=expected),))
requests=[]
pipeline=fixture.EvaluationPipeline(fixture.FakeRunner(),fixture.RULE,fixture.CONFIG,primary_judge=fixture.JudgeClient(lambda r:requests.append(r) or fixture._judge_payload(),fixture.RULE),egress_validator=lambda r:True,authoritative_context_provider=lambda *a:{'refs':[]})
pipeline.evaluate_case(case)
request=requests[0]
assert request['expected']['reference_oracle']['semantic_alignment']==semantic
wire=[]
with patch.object(plugin,'_openai_client',return_value=SimpleNamespace(responses=object())),patch.object(plugin,'_collect_responses_stream',side_effect=lambda c,r:wire.append(r) or '{}'),patch.object(plugin,'_evaluation_value',side_effect=lambda k,d:d):
 plugin._judge_with_model(request,'offline-capture')
text=wire[0]['input'][1]['content'][0]['text'];assert json.loads(text)['expected']['reference_oracle']['semantic_alignment']==semantic
changed=copy.deepcopy(request);changed['expected']['reference_oracle']['semantic_alignment']={'mode':'AUDIT_SENTINEL'}
assert contract(request)==contract(changed)
attribution=build_attribution_request('Synthetic answer.',afixture._snapshot(),judge_version='offline-audit')
assert 'semantic_alignment' not in json.dumps(attribution)
# Multimodel serialization invokes the same nested dataclass representation.
sys.path.insert(0,str(ROOT/'evaluation_multimodels'))
mm=module('xiaoan_eval.matrix_reader_audit',ROOT/'evaluation_multimodels/xiaoan_eval/multimodel.py')
encoded=json.loads(mm._judge_prompt({}, {'expected':mm._json_value(expected)}))
assert encoded['dynamic_input']['expected']['reference_oracle']['semantic_alignment']==semantic
result={'main_pipeline_received_semantic_alignment':True,'main_provider_wire_received_semantic_alignment':True,'multimodel_prompt_received_semantic_alignment':True,'changing_semantic_alignment_changes_oracle_contract':False,'attribution_request_receives_semantic_alignment':False,'attribution_request_keys':sorted(attribution),'network_calls':0,'scope':'合成数据与捕获transport；证明读取路径，不证明模型遵循元数据'}
(OUT/'judge-reader-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
