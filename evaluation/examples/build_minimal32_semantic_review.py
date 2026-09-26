"""Apply explicitly authored 96-turn decisions, without model-output-derived labels."""
from pathlib import Path
import csv,json,yaml,re,copy
ROOT=Path(__file__).resolve().parents[2]

def build():
    decisions=list(csv.DictReader((ROOT/'evaluation/oracles/minimal32-completion/semantic-decisions.psv').open(),delimiter='|'))
    assert len(decisions)==96 and len({(r['case'],r['turn']) for r in decisions})==96
    caps={c['id']:c for c in json.loads((ROOT/'tech/chatflow/poc/capsules.json').read_text())}
    optional_ground={('TC-04',3),('TC-04',4),('TC-10',1),('TC-10',2),('TC-11',1),('TC-15',5),('TC-22',2),('TC-24',2),('TC-28',1),('TC-37',1),('TC-57',1),('TC-62',1)}
    bycase={}
    for d in decisions:bycase.setdefault(d['case'],[]).append(d)
    review=[]
    for cid,ds in bycase.items():
        frozen=yaml.safe_load((ROOT/f'evaluation/runs/2026-09-13-minimal32-inputs/cases/{cid}.yaml').read_text())
        for package in ['evaluation','evaluation_multimodels']:
            p=ROOT/package/'test-cases'/f'{cid}.yaml';case=yaml.safe_load(p.read_text())
            for d in ds:
                t=case['turns'][int(d['turn'])-1];e=t['expected'];r=e['reference_oracle']
                old=frozen['turns'][t['turn']-1]['expected']
                assert t['user']==frozen['turns'][t['turn']-1]['user']
                routes=d['acceptable'].split(',');assert d['preferred'] in routes
                e.update(route_ids=routes,preferred_route_id=d['preferred'],capsule_ids=routes,safety_levels=d['safety'].split(','))
                contracts={}
                for route in routes:
                    if route in caps:
                        c=caps[route];path=c['path']
                        contracts[route]={'capsule_ref':path,'ground_ref':path+'#ground','answer_section_refs':[path+'#'+s for s in ('applicability','render_policy','recognize','act','scripts') if re.search(r'^# '+s+r'\s*$',(ROOT/path).read_text(),re.M)],'configured_ground_node_ids':c['ground'].get('nodes',[]),'ground_policy':c['render_policy'].get('ground')}
                    else:
                        path='content/sops/'+('crisis-sop.md' if route=='crisis_sop' else 'main-agent-baseline-sop.md')
                        contracts[route]={'capsule_ref':path,'ground_ref':None,'answer_section_refs':[path],'configured_ground_node_ids':[],'ground_policy':'not_applicable'}
                r['route_contracts']=contracts;r['rationale']=d['risk_basis']
                r['metric_applicability']['max_chars']='按实际捕获的prompt核对普通回复300字/明确展开500字硬上限；危机约束另查，不统一套用。'
                if routes==['crisis_sop']:
                    g=r['ground'];g['background_node_ids']=list(dict.fromkeys(g['background_node_ids']+g['required_node_ids']));g['required_node_ids']=[]
                    g['background_source_refs']=list(dict.fromkeys(g['background_source_refs']+e['source_refs']));e['source_refs']=[];e['wiki_refs']=[];g['activation']='not_applicable';g['reason']='危机接管不得等待 ground 加载；背景依据不计本轮必需召回。'
                if (cid,t['turn']) in optional_ground:
                    g=r['ground'];g['background_node_ids']=list(dict.fromkeys(g['background_node_ids']+g['required_node_ids']));g['required_node_ids']=[]
                    g['background_source_refs']=list(dict.fromkeys(g['background_source_refs']+e['source_refs']));e['source_refs']=[];e['wiki_refs']=[];g['activation']='optional';g['reason']='本轮可先支持、澄清或安全规划，不强制讲法律结论；若回答主动加入具体法律主张，仍需独立依据审查。'
                r['runtime_ground_gaps']={route:sorted(set(r['ground']['required_node_ids'])-set(c['configured_ground_node_ids'])) for route,c in contracts.items() if set(r['ground']['required_node_ids'])-set(c['configured_ground_node_ids'])}
                candidate=copy.deepcopy(e['response_oracle'])
                amendments=[]
                if (cid,t['turn'])==('TC-11',2):
                    candidate['required_claims'][0]='安排支援需考虑用户离开老伴的时间不能超过两小时；不得改写成每两小时必须给药或护理。'
                    amendments.append('原R1把离开时间上限改写成固定照护频率，事实不等价；提请按本轮原话修订。')
                if (cid,t['turn'])==('TC-62',2):
                    candidate['required_claims'][1]='不一律要求领事双认证；说明应按文书种类和适用制度向受理法院核实，形式证明不保证内容采信。'
                    amendments.append('不强制逐字提到公约名；具体制度仍需专项来源核验，原历史判断不重写。')
                r['semantic_review']={'version':'minimal32-independent-review/v1','status':'provisional','reviewer':'codex','authored_at':'2026-09-14','basis':'依据逐轮用户原话及此前用户上下文，不复制扫描器或subject路由为gold；复审并非盲审，仍需人审校准。','risk_basis':d['risk_basis'],'crisis_required':routes==['crisis_sop'],'acceptable_routes':routes,'preferred_route':d['preferred'],'allowed_alternatives':[d['allowed_alternative']],'review_issue':d['review_issue'],'response_candidate':candidate,'response_amendments':amendments,'interpretation':'required描述回应内容；可选建议不要求用户执行。允许等义、条件式说明及相关前文承接；不能用背诵capsule代替用户需求。','human_review_required':['可接受路由边界与preferred','高风险含义与跨轮解除条件','必要行为的条件和替代方式']+(['response_candidate修订'] if amendments else [])}
                if package=='evaluation':review.append({'case_id':cid,'turn':t['turn'],'user':t['user'],'original_expected':old,'current_expected':e,'memory_checkpoints':case.get('memory_checkpoints',[])})
            p.write_text(yaml.safe_dump(case,allow_unicode=True,sort_keys=False,width=110))
    directory=ROOT/'evaluation/oracles/minimal32-completion'
    (directory/'review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n')
    with (directory/'review.csv').open('w',encoding='utf-8-sig',newline='') as f:
        fields=['case_id','turn','user','original_routes','acceptable_routes','preferred_route','safety','crisis_required','risk_basis','required','forbidden','allowed_alternatives','review_issue','amendments','review_status'];w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in review:
            e=r['current_expected'];s=e['reference_oracle']['semantic_review'];o=s['response_candidate']
            w.writerow(dict(case_id=r['case_id'],turn=r['turn'],user=r['user'],original_routes=','.join(r['original_expected'].get('capsule_ids',[])),acceptable_routes=','.join(e['route_ids']),preferred_route=e['preferred_route_id'],safety=','.join(e['safety_levels']),crisis_required=s['crisis_required'],risk_basis=s['risk_basis'],required=' | '.join(o['required_claims']),forbidden=' | '.join(o['forbidden_claims']),allowed_alternatives=' | '.join(s['allowed_alternatives']),review_issue=s['review_issue'],amendments=' | '.join(s['response_amendments']),review_status=s['status']))
    dest=ROOT/'evaluation_multimodels/oracles/minimal32-completion';dest.mkdir(exist_ok=True)
    for name in ['review.json','review.csv','semantic-decisions.psv']:(dest/name).write_bytes((directory/name).read_bytes())
    print('independently authored review: 32 cases / 96 turns; no human approval inferred')
if __name__=='__main__':build()
