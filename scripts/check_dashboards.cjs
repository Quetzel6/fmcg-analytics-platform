// Lightweight offline DOM execution. Does not replace visual browser QA.
const fs=require('fs'),vm=require('vm'),path=require('path');
class Element{constructor(){this.children=[];this.style={};this.textContent='';this._value='';this.handlers={}}append(...n){this.children.push(...n)}appendChild(n){this.append(n)}replaceChildren(){this.children=[]}setAttribute(k,v){this[k]=v}addEventListener(k,v){this.handlers[k]=v}get value(){return this._value||this.children[0]?.value||this.children[0]?.textContent||''}set value(v){this._value=v}}
for(const phase of ['m2','m3','m4','m5']){
 const nodes={},E=id=>nodes[id]??=new Element(),document={getElementById:E,createElement:()=>new Element(),createElementNS:()=>new Element()};
 for(const [id,v]of [['customer','ALL'],['category','ALL'],['kind','SI'],['method','B1'],['cohort','all'],['status','ALL']])E(id).value=v;
 const html=fs.readFileSync(path.join(__dirname,'../output',phase,'dashboard.html'),'utf8');const scripts=[...html.matchAll(/<script([^>]*)>([\s\S]*?)<\/script>/g)];
 for(const s of scripts){if(s[1].includes('application/json'))E('data').textContent=s[2];else vm.runInNewContext(s[2],{document,Date,console})}
 const count=id=>E(id).children[0].children.length-1;
 if(phase==='m3'&&(E('scores').children.length!==6||E('forecast').children.length!==36))throw Error('M3 initial tables');
 if(phase==='m4'&&count('estimates')!==240)throw Error('M4 initial rows');
 if(phase==='m5'&&count('latest')!==150)throw Error('M5 initial rows');
 E('customer').value='C02';(E('customer').onchange||E('customer').handlers.change)();
 if(phase==='m3'&&E('forecast').children.length!==12)throw Error('M3 customer filter');
 if(phase==='m4'&&count('estimates')!==80)throw Error('M4 customer filter');
 if(phase==='m5'&&count('latest')!==50)throw Error('M5 customer filter');
 console.log('PASS: '+phase+' offline JS rendering and customer filter');
}
