"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const {readCSV, km, logRank, analyze, exportCSV} = require("./app.js");

test("Kaplan–Meier product limit and median", () => {
  const r = km([1,2,3,4].map(time => ({time,event:1})));
  assert.deepEqual(r.points.map(p=>Number(p.survival.toFixed(4))), [.75,.5,.25,0]);
  assert.equal(r.median,2);
  assert.equal(r.points[0].atRisk,4);
  assert.equal(r.points[3].upper,0);
});
test("tied censoring remains in risk set at event time", () => {
  const r=km([{time:1,event:1},{time:1,event:0},{time:2,event:0}]);
  assert.equal(r.points[0].atRisk,3);
  assert.ok(Math.abs(r.points[0].survival-2/3)<1e-12);
});
test("censoring only does not fabricate event times or median", () => {
  const r=km([{time:2,event:0}]);
  assert.equal(r.points.length,0);assert.equal(r.median,null);
});
test("log rank identical groups yields chi square zero",()=>{
  const data=[{time:1,event:1},{time:2,event:0},{time:3,event:1}];
  const result=logRank(data,data);
  assert.equal(result.statistic,0);assert.equal(result.p,1);
});
test("log rank distinguishes sharply different survival",()=>{
  const early=[1,2,3,4,5].map(time=>({time,event:1}));
  const late=[10,11,12,13,14].map(time=>({time,event:1}));
  const r=logRank(early,late);assert.ok(r.p<.05);
});
test("parses quoted group and exports results",()=>{
  const text='time,event,group\n1,1,"Control, standard"\n2,0,"Control, standard"\n3,1,Treatment\n4,0,Treatment\n';
  const a=analyze(text);
  assert.equal(a.groups.length,2);assert.equal(a.groups[0].name,"Control, standard");
  assert.match(exportCSV(a),/"Control, standard"/);
});
test("rejects invalid numeric inputs and missing columns",()=>{
  assert.throws(()=>readCSV("time,event\nNaN,1"),/Invalid time/);
  assert.throws(()=>readCSV("time,event\n1,0.5"),/Event must be/);
  assert.throws(()=>readCSV("time,value\n1,1"),/Missing required/);
  assert.throws(()=>readCSV("time,event\n-1,1"),/Invalid time/);
  assert.throws(()=>readCSV("time,event\n"),/at least one/);
});
