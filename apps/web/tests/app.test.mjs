import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,readdirSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {validNext,gpsQuality,queryString,pageOffset,distanceMeters} from '../src/api.js';
import {translator} from '../src/i18n.js';

test('login destinations stay within the application',()=>{
  for(const value of [null,'https://evil.invalid','//evil.invalid','/\\evil.invalid','/\n/evil.invalid','/\t/evil.invalid'])assert.equal(validNext(value),'/cuenta');
  assert.equal(validNext('/contribuir/nueva?step=2'),'/contribuir/nueva?step=2');
});
test('optional map filters never send an invalid empty type',()=>{
  const query=queryString({q:'Café',type:'',territory_id:null,limit:20});
  assert.deepEqual(Object.fromEntries(new URLSearchParams(query)),{q:'Café',limit:'20'});
});
test('list paging rejects malformed offsets',()=>{assert.equal(pageOffset('50'),50);for(const value of ['NaN','Infinity','-1','1.5','100001'])assert.equal(pageOffset(value),0);});
test('GPS quality distinguishes uncertainty and invalid readings',()=>{
  assert.equal(gpsQuality(30),'good');assert.equal(gpsQuality(30.1),'review');assert.equal(gpsQuality(100),'review');assert.equal(gpsQuality(100.1),'poor');
  for(const value of [NaN,Infinity,0,-1])assert.equal(gpsQuality(value),'poor');
});
test('selected access can move while observed GPS stays unchanged',()=>{
  const observation=Object.freeze({latitude:18.54,longitude:-72.3});
  assert.equal(distanceMeters(observation,observation),0);
  const meters=distanceMeters(observation,{latitude:18.54054,longitude:-72.3});
  assert.ok(meters>59&&meters<61);
  assert.deepEqual(observation,{latitude:18.54,longitude:-72.3});
  assert.equal(distanceMeters(observation,{latitude:NaN,longitude:0}),null);
});
test('all literal UI message keys exist in each supported language',()=>{
  const directory=fileURLToPath(new URL('../src/',import.meta.url));
  const sources=readdirSync(directory).filter(n=>/\.(jsx|js)$/.test(n)).map(n=>readFileSync(directory+n,'utf8')).join('\n');
  const keys=new Set([...sources.matchAll(/\bt\(['"]([A-Za-z]+)['"]\)/g)].map(m=>m[1]));
  for(const lang of ['es','fr','ht'])for(const key of keys)assert.notEqual(translator(lang)(key),key,`${lang}: ${key}`);
});
