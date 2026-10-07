// Exercise the generated page's actual filter script without a browser or packages.
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const html = fs.readFileSync('output/scenarios/q4-plan-v1/cockpit.html', 'utf8');
const fields = {};
for (const id of ['scenario', 'customer', 'category']) {
  const select = html.match(new RegExp('<select id="'+id+'">([\\s\\S]*?)</select>'))[1];
  const options = [...select.matchAll(/<option value="([^"]+)">([^<]*)<\/option>/g)].map(m=>({value:m[1],textContent:m[2]}));
  fields[id] = {options, value:options[0].value, addEventListener:()=>{},
    get selectedOptions(){return this.options.filter(o=>o.value===this.value);}};
}
fields.scope = {textContent:''};
const tables = {};
for (const id of ['annual', 'monthly', 'orders']) {
  const body = html.match(new RegExp('<table id="'+id+'">[\\s\\S]*?<tbody>([\\s\\S]*?)</tbody>'))[1];
  tables[id] = [...body.matchAll(/<tr([^>]*)>/g)].map(m=>({hidden:false,
    dataset:Object.fromEntries([...m[1].matchAll(/data-(scenario|customer|category)="([^"]*)"/g)].map(a=>[a[1],a[2]]))}));
}
const document = {getElementById:id=>fields[id],
  querySelectorAll:selector=>tables[selector.match(/^#(\w+) tbody tr$/)[1]]};
const context = vm.createContext({document});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)[1], context);
const visible = id=>tables[id].filter(row=>!row.hidden);
assert.equal(fields.scenario.value,'central');
assert.equal(visible('annual').length,1);
assert.equal(visible('monthly').length,36);
assert.equal(visible('orders').length,4);
fields.customer.value='C02';
fields.category.value=tables.orders[0].dataset.category;
vm.runInContext('update()',context);
assert.equal(visible('monthly').length,3);
assert.ok(visible('orders').length>0);
assert.ok(visible('orders').every(r=>r.dataset.customer==='C02'&&r.dataset.category===fields.category.value));
// Annual customer target remains visible regardless of category filter.
assert.equal(visible('annual').length,1);
assert.equal(visible('annual')[0].dataset.customer,'C02');
fields.customer.value='C01';
vm.runInContext('update()',context);
assert.equal(visible('monthly').length,3);
assert.equal(visible('orders').length,0);
assert.match(fields.scope.textContent,/0 order review rows/);
fields.scenario.value='optimistic'; fields.customer.value='ALL'; fields.category.value='ALL';
vm.runInContext('update()',context);
assert.equal(visible('monthly').length,36);
assert.equal(visible('orders').length,4);
assert.ok(visible('monthly').every(r=>r.dataset.scenario==='optimistic'));
console.log('PASS: generated filter script, central default, retailer/category isolation, empty orders and annual scope');
