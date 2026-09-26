"""Prepare a title-exact path migration in an isolated draft, never edit Sources.

Does not certify Wiki claims or accept a source manifest. Unknown/ambiguous titles
and unresolved excerpt anchors block integration; document listings are recorded.
"""
from pathlib import Path
import json,re,sys,hashlib,difflib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tech/chatflow/poc'))
from ground import extract_source_refs,extract_heading_path_section
STAGE=Path('/tmp/xiaoan-remediation-stage-20260914')
OUT=ROOT/'evaluation/oracles/minimal32-remediation'
source=ROOT/'content/knowledge/source'
by_title={}
for p in source.glob('*.md'):
    title=re.sub(r'^\d+-','',p.name)
    by_title.setdefault(title,[]).append(p)
changes=[];errors=[];document_refs=[];diff=[]
for p in sorted((ROOT/'content/knowledge/wiki').rglob('*.md')):
    if p.name in {'wiki-update-report.md', 'log.md'}: continue  # Historical records are immutable.
    text=p.read_text();new=text
    for old in sorted(set(re.findall(r'knowledge/source/legal/[^\s"`<>]+?\.md',text))):
        title=re.sub(r'^\d+-','',Path(old).name);matches=by_title.get(title,[])
        if len(matches)!=1:
            errors.append({'page':str(p.relative_to(ROOT)),'ref':old,'reason':'title not uniquely matched'});continue
        replacement='knowledge/source/'+matches[0].name
        new=new.replace(old,replacement)
        changes.append({'page':str(p.relative_to(ROOT)),'old':old,'new':replacement,'source_sha256':hashlib.sha256(matches[0].read_bytes()).hexdigest()})
    # The old heading included the following prose. Confirm its intended source
    # section explicitly, rather than fuzzy matching an arbitrary nearby section.
    old_anchor='knowledge/source/051-关于加强家庭暴力告诫制度贯彻实施的意见.md#一、本意见所称告诫'
    if old_anchor in new:
        excerpt=extract_heading_path_section((source/'051-关于加强家庭暴力告诫制度贯彻实施的意见.md').read_text(),'一、')
        assert '本意见所称告诫，是指' in excerpt
        new=new.replace(old_anchor,'knowledge/source/051-关于加强家庭暴力告诫制度贯彻实施的意见.md#一、')
    if p.parent.name=='nodes':
        for ref in extract_source_refs(new):
            name,sep,anchor=ref.partition('#')
            if not sep:
                document_refs.append({'page':str(p.relative_to(ROOT)),'ref':ref});continue
            try:extract_heading_path_section((ROOT/'content'/name).read_text(),anchor)
            except (OSError,ValueError) as exc:errors.append({'page':str(p.relative_to(ROOT)),'ref':ref,'reason':str(exc)})
    if new!=text:
        target=STAGE/p.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(new)
        diff.extend(difflib.unified_diff(text.splitlines(True),new.splitlines(True),fromfile='a/'+str(p.relative_to(ROOT)),tofile='b/'+str(p.relative_to(ROOT))))
result={'status':'DRAFT','mode':'incremental path/anchor migration; no source or claim edits','changes':changes,'errors':errors,'document_only_refs':document_refs,'accepted_source_manifest_updated':False,'stage':str(STAGE)}
(OUT/'wiki-link-migration.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
(OUT/'wiki-link-migration.diff').write_text(''.join(diff))
print(json.dumps({'page_count':len({c['page'] for c in changes}),'path_replacements':len(changes),'errors':errors,'document_only_refs':document_refs},ensure_ascii=False))
