// Rebuild: npm install pptxgenjs; node build_slides.cjs
const pptxgen = require('pptxgenjs');
const fs = require('fs');
const path = require('path');
const slides = JSON.parse(fs.readFileSync(path.join(__dirname,'slides.json'),'utf8'));
const pptx = new pptxgen();
pptx.layout='LAYOUT_WIDE';
pptx.author='XiaoAn Evaluation';
pptx.subject='Agent evaluation framework design and measurement contract v2';
pptx.title='XiaoAn｜如何設計能指導改進的 Agent 評估框架';
pptx.company='XiaoAn';
pptx.lang='zh-TW';
pptx.theme={headFontFace:'Heiti TC',bodyFontFace:'Heiti TC',lang:'zh-TW'};
const C={paper:'F5F3EE',ink:'142B38',teal:'087F8C',light:'E2EFEB',muted:'61717A',line:'D4DDDB',white:'FFFFFF',orange:'B65B38',pale:'F2E5DB',blue:'DDE8F0'};
const W=13.333333,H=7.5;
const checks=[];
let slide, idx;
function rect(x,y,w,h,fill,line=fill,r=0){slide.addShape(r?pptx.ShapeType.roundRect:pptx.ShapeType.rect,{x,y,w,h,rectRadius:r,fill:{color:fill},line:{color:line,width:0.6},radius:r});}
function text(s,x,y,w,h,size=18,color=C.ink,bold=false,opts={}){slide.addText(String(s),{x,y,w,h,fontFace:'Heiti TC',fontSize:size,color,bold,margin:0,breakLine:false,vertAnchor:'mid',valign:'mid',paraSpaceAfterPt:4,...opts});checks.push({slide:idx+1,text:String(s),x,y,w,h,size});}
function line(x,y,w,color=C.line){slide.addShape(pptx.ShapeType.line,{x,y,w,h:0,line:{color,width:1}});}
function pill(s,x,y,w,fill=C.light,color=C.teal){rect(x,y,w,0.30,fill);text(s,x+.09,y+.025,w-.18,.25,10.5,color,true);}
function base(s,i){idx=i;slide=pptx.addSlide();slide.background={color:C.paper};if(s.layout!=='cover'){rect(0,0,.15,H,C.teal);text(s.section,.55,.28,10,.23,10,C.teal,true,{charSpacing:1.2});text(s.title,.55,.72,12.15,1.05,30,C.ink,true,{valign:'top',breakLine:false});line(.55,1.89,12.15);rect(.55,6.43,.055,.45,C.teal);text(s.takeaway,.74,6.44,11.92,.43,16,C.teal,true);text('XIAOAN  /  EVALUATION DESIGN v2',.55,7.11,7,.16,8.2,C.muted);text(`${String(i+1).padStart(2,'0')} / ${slides.length}`,11.84,7.08,.85,.21,10,C.muted,false,{align:'right'});text(`README § ${s.source}`,8.2,7.11,3.45,.16,8.2,C.muted,false,{align:'right'});}slide.addNotes(`${s.notes}\n\n本頁要傳達：${s.takeaway}\n來源：https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#${s.source}\n所有範例均為合成示例；軟體測試不代表模型品質結果。`);}
function cards(data){const gap=.22,w=(12.15-gap*(data.length-1))/data.length;data.forEach((c,i)=>{let x=.55+i*(w+gap);rect(x,2.20,w,3.66,C.white,C.line);pill(c.tag||'',x+.23,2.45,w-.46);text(c.head,x+.23,3.13,w-.46,.76,23,C.ink,true);text(c.body,x+.23,4.20,w-.46,1.22,17,C.muted,false,{valign:'top',breakLine:false,paraSpaceAfterPt:9});});}
function table(d){let n=d.headers.length;const widths=n===3?[3.05,4.18,4.92]:[6.0,6.15];let rowH=Math.min(.73,3.84/d.rows.length);const y0=2.08;let x=.55;d.headers.forEach((h,i)=>{rect(x,y0,widths[i],.47,C.ink);text(h,x+.15,y0+.07,widths[i]-.30,.34,14,C.white,true);x+=widths[i];});d.rows.forEach((r,j)=>{let y=y0+.47+j*rowH;x=.55;r.forEach((t,i)=>{rect(x,y,widths[i],rowH,j%2?C.paper:C.white,C.line);text(t,x+.15,y+.08,widths[i]-.3,rowH-.13,15.3,i===0?C.teal:C.ink,i===0,{valign:'mid',paraSpaceAfterPt:1});x+=widths[i];});});}
function flow(d){const n=d.steps.length,g=.18,w=(12.15-(n-1)*g)/n;d.steps.forEach((a,i)=>{const x=.55+i*(w+g);pill(String(i+1).padStart(2,'0'),x,2.27,.42);rect(x,2.81,w,2.00,C.white,C.line);rect(x,2.81,w,.055,C.teal);text(a,x+.12,3.04,w-.24,.60,n>5?16:18,C.ink,true,{align:'center'});text(d.details[i],x+.13,3.91,w-.26,.68,n>5?13:15.5,C.muted,false,{align:'center'});if(i<n-1)text('›',x+w,3.40,g,.5,24,C.teal,true,{align:'center'});});rect(.55,5.22,12.15,.73,C.light);text(d.bottom,.78,5.32,11.70,.47,16,C.teal,true,{align:'center'});}
slides.forEach((s,i)=>{base(s,i);const d=s.data;switch(s.layout){
case 'cover':
 slide.background={color:C.ink};rect(0,0,.15,H,C.teal);text('XIAOAN  /  FRAMEWORK DESIGN',.65,.48,10,.35,13,'88C6BC',true,{charSpacing:1});text(s.title,.65,1.52,11.8,2.0,42,C.white,true,{valign:'top',breakLine:false});text(d.line,.67,3.86,11.8,.65,24,'D7E8E3');line(.67,4.91,11.7,'47717B');pill(d.edition,.67,5.27,5.75,'285463','D7E8E3');text(d.meta,.67,5.90,11.8,.46,15,'C2D4D2');text('EVIDENCE → MEASUREMENT → DECISION',.67,6.82,11.8,.26,11,'88C6BC',true,{charSpacing:1});break;
case 'cards': cards(d);break;
case 'table':table(d);break;
case 'layers':d.forEach((r,j)=>{let y=2.12+j*1.32;rect(.55,y,12.15,1.12,j===2?C.light:C.white,C.line);text(r.n,.77,y+.22,.73,.58,29,C.teal,true);text(r.head,1.72,y+.15,4.40,.73,23,C.ink,true);text(r.body,6.38,y+.19,5.91,.65,16,C.muted);});break;
case 'flow':flow(d);break;
case 'timeline':d.lanes.forEach((r,j)=>{const y=2.20+j*1.25;pill(r[0],.55,y,1.25,C.ink,C.white);r.slice(1).forEach((t,k)=>{rect(2.02+k*3.57,y,3.36,.83,C.white,C.line);text(t,2.16+k*3.57,y+.15,3.05,.51,16.5,C.ink,true);});});d.facts.forEach((t,j)=>text('• '+t,.63,4.98+j*.35,12,.29,14.5,C.muted));break;
case 'phases':[d.left,d.right].forEach((a,j)=>{let x=.55+j*6.20;rect(x,2.20,5.95,3.84,j?C.light:C.white,C.line);pill(a[0],x+.25,2.44,5.45,j?C.teal:C.ink,C.white);a.slice(1).forEach((t,k)=>{text(`${k+1}`,x+.25,3.18+k*.76,.33,.37,17,C.teal,true);text(t,x+.84,3.15+k*.76,4.73,.48,18,C.ink,k===0);});});break;
case 'coverage':d.cards.forEach((r,j)=>{let x=.55+j*3.075;rect(x,2.14,2.9,2.26,C.white,C.line);text(r.number,x+.2,2.38,2.5,.80,47,j===1?C.orange:C.teal,true);text(r.label,x+.2,3.27,2.5,.35,17.5,C.ink,true);text(r.small,x+.2,3.78,2.5,.40,11.4,C.muted);});d.rows.forEach((r,j)=>{let y=4.78+j*.42;text(r[0],.75,y,6,.30,15,C.muted);text(r[1],7.65,y,4.8,.30,15,C.ink,true,{align:'right'});});break;
case 'weights':d.weights.forEach((r,j)=>{let y=2.11+j*.54;text(r[0],.55,y,2.53,.32,15.5,C.ink);rect(3.15,y+.04,3.58,.22,C.line);rect(3.15,y+.04,3.58*r[1]/.22,.22,j===1?C.orange:C.teal);text(`${Math.round(r[1]*100)}%`,6.97,y,1,.32,16,C.ink,true);});rect(8.38,2.14,4.32,3.94,C.white,C.line);text('0–3 評分錨點',8.64,2.42,3.79,.50,21,C.teal,true);d.anchors.forEach((t,j)=>text(t,8.64,3.17+j*.48,3.80,.36,16,C.ink));text(d.note,8.64,5.42,3.78,.40,12,C.muted);break;
case 'calculation':rect(.55,2.19,7.35,3.92,C.white,C.line);d.equations.forEach((t,j)=>text(t,.85,2.54+j*.71,6.72,.47,j===3?21:19,j===3?C.teal:C.ink,j===3));text(d.number,8.20,2.60,4.51,1.07,43,C.teal,true);text(d.label,8.27,3.85,4.38,.56,17,C.muted);d.chips.forEach((t,j)=>pill(t,8.23+(j%2)*2.23,4.90+Math.floor(j/2)*.47,2.08));break;
case 'aggregation':[d.left,d.right].forEach((a,j)=>{let x=.55+j*6.2;rect(x,2.11,5.95,1.94,C.white,C.line);pill(a[0],x+.22,2.32,1.19);text(a[1],x+.23,2.89,5.46,.39,21,C.ink,true);text(a[2],x+.23,3.48,5.46,.32,17,C.muted);});text(d.result,.66,4.40,12,.52,28,C.teal,true,{align:'center'});text(d.contrast,.66,5.12,12,.40,19,C.muted,false,{align:'center'});text(d.note,.67,5.77,12,.33,13,C.muted,false,{align:'center'});break;
case 'memory':d.forEach((r,j)=>{let x=.55+(j%4)*3.08,y=2.14+Math.floor(j/4)*2.03;rect(x,y,2.90,1.81,C.white,C.line);text(String(j+1).padStart(2,'0'),x+.18,y+.16,.45,.28,11,C.teal,true);text(r.head,x+.18,y+.55,2.54,.44,21,C.ink,true);text(r.body,x+.18,y+1.15,2.53,.46,14,C.muted);});break;
case 'judgepanel':{let x0=1.08,y0=2.54,cell=.56;d.labels.forEach((x,j)=>text(x,x0+j*cell,y0-.38,cell,.25,12,C.muted,false,{align:'center'}));d.rows.forEach((r,j)=>{text(r,.55,y0+j*cell,.46,.39,12,C.muted);for(let k=0;k<5;k++){rect(x0+k*cell,y0+j*cell,.51,.51,j===k?C.pale:C.light);text(j===k?'S':'•',x0+k*cell,y0+j*cell+.025,.51,.43,19,j===k?C.orange:C.teal,true,{align:'center'});}});text(d.small,.55,5.66,4.01,.58,10,C.muted);d.points.forEach((t,j)=>{pill(String(j+1),5.05,2.39+j*.85,.34);text(t,5.64,2.31+j*.85,6.93,.65,17.5,C.ink);});break;}
case 'reports':d.sequence.forEach((t,j)=>{rect(.55+j*2.44,2.11,2.29,.44,C.light);text(t,.61+j*2.44,2.19,2.17,.25,11.5,C.teal,true,{align:'center'});});[d.left,d.right].forEach((a,j)=>{let x=.55+j*6.20;rect(x,2.91,5.95,3.22,C.white,C.line);text(a[0],x+.23,3.15,5.46,.50,26,C.ink,true);text(a[1],x+.23,3.82,5.46,.36,18,C.teal,true);a.slice(2).forEach((t,k)=>text(t,x+.23,4.42+k*.43,5.47,.34,15,C.muted));});break;
case 'edd':d.steps.forEach((t,j)=>{rect(.55+j*2.04,2.18,1.87,.63,j===5?C.teal:C.ink);text(t,.61+j*2.04,2.34,1.75,.28,13,C.white,true,{align:'center'});});rect(.55,3.16,12.15,2.18,C.white,C.line);d.example.forEach((t,j)=>text((j===0?'':'→ ')+t,.84,3.40+j*.43,11.58,.34,j===0?19:16,j===0?C.teal:C.ink,j===0));text(d.small,.7,5.79,11.9,.32,13,C.muted);break;
case 'commands':d.blocks.forEach((r,j)=>{const y=2.07+j*2.14;rect(.55,y,12.15,1.99,j?C.light:C.white,C.line);pill(r[0],.77,y+.15,1.70,j?C.teal:C.ink,C.white);text(r[1],2.69,y+.18,9.73,1.62,12.5,C.ink,false,{fontFace:'Menlo',valign:'top',paraSpaceAfterPt:0,breakLine:false});});break;
case 'closing':d.numbers.forEach((r,j)=>{const x=.55+j*4.10;text(r[0],x,2.12,3.90,.95,48,C.teal,true,{align:'center'});text(r[1],x,3.16,3.90,.39,16,C.muted,false,{align:'center'});});line(.55,3.94,12.15);d.links.forEach((t,j)=>text(t,.75,4.20+j*.38,11.78,.31,j===0?18:14,j===0?C.ink:C.muted,j===0));text(d.small,.75,5.86,11.78,.31,12,C.muted);break;
default:throw new Error('Unknown layout '+s.layout);
}});
const issues=checks.filter(o=>o.x<0||o.y<0||o.x+o.w>W+.02||o.y+o.h>H+.02);
if(issues.length)throw new Error('Off-slide text bounds: '+JSON.stringify(issues));
fs.writeFileSync(path.join(__dirname,'layout-check.json'),JSON.stringify({slides:slides.length,textboxes:checks.length,off_slide:issues.length},null,2));
pptx.writeFile({fileName:path.join(__dirname,'xiaoan-evaluation-framework.pptx')}).then(()=>console.log(`Wrote ${slides.length}-slide editable PowerPoint`));
