(function (root) {
  "use strict";
  const LIMIT = 20000;
  const NS = "http://www.w3.org/2000/svg";

  function readCSV(text) {
    if (typeof text !== "string" || !text.trim()) throw new Error("Provide a CSV dataset.");
    if (text.length > 2000000) throw new Error("CSV text is too large (2 MB maximum).");
    const rows = [], current = [];
    let cell = "", quoted = false, ended = false;
    text = text.replace(/^\uFEFF/, "");
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (quoted) {
        if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; }
        else if (c === '"') quoted = false;
        else cell += c;
      } else if (c === '"') {
        if (cell.trim()) throw new Error("Malformed CSV quoting.");
        quoted = true;
      } else if (c === ",") {
        current.push(cell.trim()); cell = "";
      } else if (c === "\n" || c === "\r") {
        if (c === "\r" && text[i + 1] === "\n") i++;
        current.push(cell.trim()); cell = "";
        if (current.some(v => v !== "")) rows.push(current.slice());
        current.length = 0;
        if (rows.length > LIMIT + 1) throw new Error("Maximum 20,000 observations.");
      } else { cell += c; }
    }
    if (quoted) throw new Error("Unclosed CSV quoted field.");
    current.push(cell.trim());
    if (current.some(v => v !== "")) rows.push(current);
    if (rows.length < 2) throw new Error("CSV requires a header and at least one observation.");
    const header = rows.shift().map(s => s.toLowerCase());
    function index(names, optional) {
      const i = header.findIndex(h => names.includes(h));
      if (i < 0 && !optional) throw new Error("Missing required CSV column: " + names[0]);
      return i;
    }
    const ti = index(["time", "survival_time", "days", "months", "t"], false);
    const ei = index(["event", "status", "dead", "e"], false);
    const gi = index(["group", "treatment", "arm", "cohort"], true);
    const data = rows.map((r, i) => {
      if (r.length !== header.length) throw new Error("Incorrect number of CSV columns at data row " + (i + 2));
      const time = Number(r[ti]), event = Number(r[ei]);
      if (!r[ti] || !Number.isFinite(time) || time < 0) throw new Error("Invalid time at row " + (i + 2));
      if (r[ei] !== "0" && r[ei] !== "1") throw new Error("Event must be 0 or 1 at row " + (i + 2));
      const group = gi < 0 ? "All participants" : (r[gi] || "Unlabelled");
      return {time, event, group};
    });
    if (data.length > LIMIT) throw new Error("Maximum 20,000 observations.");
    if (new Set(data.map(r => r.group)).size > 2) throw new Error("This interface supports up to two groups.");
    return data;
  }

  function km(data) {
    if (!data.length) throw new Error("At least one observation is required.");
    const bins = new Map();
    for (const r of data) {
      if (!Number.isFinite(r.time) || r.time < 0 || (r.event !== 0 && r.event !== 1))
        throw new Error("Invalid time or event indicator.");
      const b = bins.get(r.time) || {d: 0, c: 0};
      if (r.event === 1) b.d++; else b.c++;
      bins.set(r.time, b);
    }
    let n = data.length, s = 1, greenwood = 0, hazard = 0, median = null;
    const points = [];
    const counts = [...bins.entries()].sort((a, b) => a[0] - b[0]);
    for (const [time, b] of counts) {
      if (b.d) {
        s *= 1 - b.d / n;
        hazard += b.d / n;
        if (n > b.d) greenwood += b.d / (n * (n - b.d));
        let lower, upper;
        if (s === 0) { lower = 0; upper = 0; }
        else if (s === 1) { lower = 1; upper = 1; }
        else {
          const g = Math.log(-Math.log(s));
          const se = Math.sqrt(greenwood) / Math.abs(Math.log(s));
          lower = Math.exp(-Math.exp(g + 1.959963984540054 * se));
          upper = Math.exp(-Math.exp(g - 1.959963984540054 * se));
        }
        points.push({time, survival: s, atRisk: n, deaths: b.d, censored: b.c,
          lower, upper, cumulativeHazard: hazard});
        if (median === null && s <= .5) median = time;
      }
      n -= b.d + b.c;
    }
    return {n: data.length, events: data.filter(r => r.event === 1).length,
      censored: data.filter(r => r.event === 0).length, median, points};
  }

  function erfc(x) {
    const z = Math.abs(x), t = 1 / (1 + .5 * z);
    const ans = t * Math.exp(-z*z - 1.26551223 + t*(1.00002368 + t*(.37409196 +
      t*(.09678418 + t*(-.18628806 + t*(.27886807 + t*(-1.13520398 +
      t*(1.48851587 + t*(-.82215223 + t*.17087277)))))))));
    return x >= 0 ? ans : 2 - ans;
  }

  function logRank(a, b) {
    if (!a.length || !b.length) throw new Error("Both groups need observations.");
    const bins = new Map();
    for (const [index, data] of [a, b].entries()) for (const r of data) {
      const x = bins.get(r.time) || {d:[0,0], c:[0,0]};
      x[r.event ? "d" : "c"][index]++; bins.set(r.time, x);
    }
    let n1=a.length, n2=b.length, difference=0, variance=0;
    for (const [, x] of [...bins.entries()].sort((a,b) => a[0]-b[0])) {
      const n=n1+n2, d=x.d[0]+x.d[1];
      if (d && n > 1) {
        difference += x.d[0] - n1*d/n;
        variance += n1*n2*d*(n-d)/(n*n*(n-1));
      }
      n1 -= x.d[0]+x.c[0]; n2 -= x.d[1]+x.c[1];
    }
    if (!variance) return {statistic:0, z:0, p:1};
    const z = difference / Math.sqrt(variance);
    return {statistic:z*z, z, p:Math.max(0, Math.min(1, erfc(Math.abs(z)/Math.SQRT2)))};
  }

  function analyze(text) {
    const data = readCSV(text), names = [...new Set(data.map(r => r.group))];
    const groups = names.map(name => ({name, rows:data.filter(r => r.group===name)}));
    for (const g of groups) g.km = km(g.rows);
    const comparison = groups.length === 2 ? logRank(groups[0].rows, groups[1].rows) : null;
    return {data, groups, comparison};
  }

  function number(x, digits) { return Number(x).toFixed(digits); }
  function svgEl(name, attrs, parent, text) {
    const el = document.createElementNS(NS, name);
    for (const [k,v] of Object.entries(attrs || {})) el.setAttribute(k, String(v));
    if (text !== undefined) el.textContent = String(text);
    parent.appendChild(el); return el;
  }
  function plot(analysis) {
    const svg = document.getElementById("plot"); svg.replaceChildren();
    const W=900, H=375, pad={l:64,r:24,t:24,b:55}, width=W-pad.l-pad.r, height=H-pad.t-pad.b;
    const maxTime = Math.max(1, ...analysis.data.map(r => r.time));
    const X=t => pad.l + width*t/maxTime, Y=s => pad.t + height*(1-s);
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svgEl("title", {}, svg, "Kaplan–Meier survival probability against observed time");
    for (let i=0; i<=4; i++) {
      const y=Y(i/4);
      svgEl("line", {x1:pad.l,y1:y,x2:W-pad.r,y2:y,stroke:"#dce4ed"}, svg);
      svgEl("text", {x:pad.l-12,y:y+5,"text-anchor":"end",fill:"#526276","font-size":13}, svg, number(i/4,2));
    }
    for (let i=0; i<=5; i++) {
      const t=maxTime*i/5, x=X(t);
      svgEl("text", {x,y:H-pad.b+24,"text-anchor":"middle",fill:"#526276","font-size":13}, svg, number(t,1));
    }
    svgEl("line", {x1:pad.l,y1:pad.t,x2:pad.l,y2:H-pad.b,stroke:"#64748b"}, svg);
    svgEl("line", {x1:pad.l,y1:H-pad.b,x2:W-pad.r,y2:H-pad.b,stroke:"#64748b"}, svg);
    svgEl("text", {x:pad.l+width/2,y:H-7,"text-anchor":"middle",fill:"#34465a","font-size":15}, svg, "Observed time (dataset units)");
    const palette = ["#2457b2", "#ce593d"];
    analysis.groups.forEach((g,j) => {
      let d="M"+X(0)+" "+Y(1),last=1;
      for(const p of g.km.points) { d+=" H"+X(p.time)+" V"+Y(p.survival);last=p.survival; }
      d+=" H"+X(maxTime);
      svgEl("path",{d,fill:"none",stroke:palette[j],"stroke-width":3.5,
        "stroke-linejoin":"round"},svg);
      // Tick marks for censored observations, at the survival level just before/at censoring.
      for(const r of g.rows) if(r.event===0) {
        let at=1;
        for(const p of g.km.points) if(p.time<=r.time) at=p.survival; else break;
        const x=X(r.time),y=Y(at);
        svgEl("line",{x1:x,y1:y-5,x2:x,y2:y+5,stroke:palette[j],"stroke-width":1.6},svg);
      }
    });
    const legend=document.getElementById("legend"); legend.replaceChildren();
    analysis.groups.forEach((g,j) => {
      const el=document.createElement("span");
      const mark=document.createElement("span");mark.className="legend-mark";
      mark.style.background=palette[j];el.append(mark, document.createTextNode(" "+g.name));legend.append(el);
    });
  }
  function setText(id, value) { document.getElementById(id).textContent = String(value); }
  function show(analysis) {
    setText("total",analysis.data.length);
    setText("events",analysis.data.filter(r=>r.event===1).length);
    setText("censored",analysis.data.filter(r=>r.event===0).length);
    setText("groups",analysis.groups.length);
    setText("comparison", analysis.comparison ?
      "Two-sided log-rank χ²(1) = "+number(analysis.comparison.statistic,3)+
      "; p = "+(analysis.comparison.p<.0001?analysis.comparison.p.toExponential(2):number(analysis.comparison.p,4)) :
      "Log-rank comparison requires two groups.");
    const tbody=document.getElementById("results");tbody.replaceChildren();
    for(const g of analysis.groups) {
      if (!g.km.points.length) {
        const row=document.createElement("tr");
        [g.name,"—","1.000","—","—","—","—","Not reached"].forEach(v=>{
          const td=document.createElement("td");td.textContent=String(v);row.append(td);});
        tbody.append(row);
      }
      for(const p of g.km.points) {
        const row=document.createElement("tr");
        [g.name,p.time,number(p.survival,4),p.atRisk,p.deaths,
          number(p.lower,4),number(p.upper,4),g.km.median===null?"Not reached":g.km.median].forEach(v=>{
          const td=document.createElement("td");td.textContent=String(v);row.append(td);});
        tbody.append(row);
      }
    }
    plot(analysis);
  }
  function csvValue(v) {
    const raw=String(v);
    const s=/^\s*[=+\-@]/.test(raw) ? "'" + raw : raw;
    return /[",\r\n]/.test(s) ? '"'+s.replace(/"/g,'""')+'"' : s;
  }
  function exportCSV(analysis) {
    const rows=[["group","time","survival","at_risk","deaths","censored_at_event_time",
      "ci_lower_95","ci_upper_95","nelson_aalen","median"]];
    for(const g of analysis.groups) for(const p of g.km.points)
      rows.push([g.name,p.time,p.survival,p.atRisk,p.deaths,p.censored,p.lower,p.upper,
        p.cumulativeHazard,g.km.median===null?"NR":g.km.median]);
    return rows.map(row=>row.map(csvValue).join(",")).join("\r\n")+"\r\n";
  }
  function download(text) {
    const blob=new Blob([text],{type:"text/csv;charset=utf-8"});
    const url=URL.createObjectURL(blob),a=document.createElement("a");
    a.href=url;a.download="kaplan-meier-results.csv";a.click();
    setTimeout(()=>URL.revokeObjectURL(url),1000);
  }
  function init() {
    const input=document.getElementById("dataset"), status=document.getElementById("status");
    let current=null;
    document.getElementById("calculate").addEventListener("click", () => {
      try {
        current=analyze(input.value);
        show(current);
        status.textContent="Calculated locally; no dataset uploaded.";
        status.className="status ok";
        document.getElementById("export").disabled=false;
      } catch(e) {
        current=null;document.getElementById("export").disabled=true;
        status.textContent=e.message;status.className="status error";
        document.getElementById("plot").replaceChildren();
        document.getElementById("results").replaceChildren();
        document.getElementById("legend").replaceChildren();
        for(const id of ["total","events","censored","groups"]) setText(id,"—");
        setText("comparison","No valid analysis.");
      }
    });
    document.getElementById("export").addEventListener("click",()=>{if(current)download(exportCSV(current));});
    document.getElementById("import-button").addEventListener("click",()=>document.getElementById("upload").click());
    document.getElementById("upload").addEventListener("change",async e=>{
      const file=e.target.files[0];if(!file)return;
      try {
        if(file.size>2000000)throw new Error("CSV file is too large (2 MB maximum).");
        input.value=await file.text();document.getElementById("calculate").click();
      } catch(err){status.textContent=err.message;status.className="status error";}
      e.target.value="";
    });
    document.getElementById("sample").addEventListener("click",()=>{
      input.value="time,event,group\n1,1,Treatment\n2,0,Treatment\n3,1,Treatment\n4,0,Treatment\n5,1,Treatment\n2,0,Control\n3,1,Control\n4,1,Control\n5,0,Control\n6,1,Control";
      document.getElementById("calculate").click();
    });
    document.getElementById("calculate").click();
  }
  const API={readCSV,km,logRank,analyze,exportCSV};
  if(typeof module!=="undefined" && module.exports)module.exports=API;
  if(typeof document!=="undefined")document.addEventListener("DOMContentLoaded",init);
})(typeof window!=="undefined"?window:globalThis);
