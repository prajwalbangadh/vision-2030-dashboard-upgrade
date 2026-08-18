(function(){
  'use strict';
  const D=VD;
  const page=document.body.dataset.page;
  const root=document.getElementById('main');
  const $=(selector,context=document)=>context.querySelector(selector);
  const $$=(selector,context=document)=>Array.from(context.querySelectorAll(selector));
  const esc=value=>String(value??'').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const uniq=values=>[...new Set(values.filter(v=>v!==null&&v!==undefined&&v!==''))];
  const sortText=values=>uniq(values).sort((a,b)=>String(a).localeCompare(String(b),undefined,{numeric:true}));
  const fmtInt=value=>Number(value||0).toLocaleString();
  const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));
  const statusLabel={met:'Met goal',missed:'Missed goal',unavailable:'Status unavailable'};
  const areaColor={Learning:'#00bfb3',Team:'#f59b16',Consumer:'#da291c',Clinical:'#6e2b62',Financial:'#00a3e0',Risk:'#00635b',WPC:'#006298'};

  function statusPill(status){
    const safe=status in statusLabel?status:'unavailable';
    return `<span class="status-pill ${safe}">${statusLabel[safe]}</span>`;
  }
  function counts(records){
    const result={met:0,missed:0,unavailable:0};
    records.forEach(r=>result[r.goalStatus in result?r.goalStatus:'unavailable']++);
    result.eligible=result.met+result.missed;
    result.rate=result.eligible?Math.round(result.met/result.eligible*100):null;
    return result;
  }
  function validValue(record){return record&&record.valueNumber!==null&&Number.isFinite(record.valueNumber)}
  function median(numbers){
    const values=numbers.filter(Number.isFinite).sort((a,b)=>a-b);
    if(!values.length)return null;
    const middle=Math.floor(values.length/2);
    return values.length%2?values[middle]:(values[middle-1]+values[middle])/2;
  }
  function quantile(numbers,p){
    const values=numbers.filter(Number.isFinite).sort((a,b)=>a-b);
    if(!values.length)return null;
    const index=(values.length-1)*p,lower=Math.floor(index),fraction=index-lower;
    return values[lower+1]===undefined?values[lower]:values[lower]+fraction*(values[lower+1]-values[lower]);
  }
  function formatNumeric(value,unit){
    if(value===null||!Number.isFinite(value))return '—';
    if(unit==='currency'){
      if(Math.abs(value)>=1e9)return '$'+(value/1e9).toFixed(1)+'B';
      if(Math.abs(value)>=1e6)return '$'+(value/1e6).toFixed(1)+'M';
      return '$'+Math.round(value).toLocaleString();
    }
    if(unit==='count')return Math.abs(value)>=1e6?(value/1e6).toFixed(1)+'M':Math.round(value).toLocaleString();
    if(unit==='percent')return value.toFixed(1)+'%';
    if(unit==='rating')return value.toFixed(value%1?1:0);
    return value.toLocaleString(undefined,{maximumFractionDigits:1});
  }
  function dateValue(label){
    if(!label||label==='N/A')return -Infinity;
    const match=String(label).match(/^([A-Za-z]{3})\s+(\d{4})$/);
    if(match){const months={Jan:0,Feb:1,Mar:2,Apr:3,May:4,Jun:5,Jul:6,Aug:7,Sep:8,Oct:9,Nov:10,Dec:11};return +match[2]*12+(months[match[1]]??0)}
    const year=String(label).match(/\d{4}/);return year?+year[0]*12:-Infinity;
  }
  function dateRange(records){
    const dates=sortText(records.map(r=>r.dataAsOf).filter(d=>d!=='N/A')).sort((a,b)=>dateValue(a)-dateValue(b));
    return dates.length?(dates.length===1?dates[0]:`${dates[0]} – ${dates[dates.length-1]}`):'No reporting date';
  }
  function sourceChip(){
    return `<div class="source-chip"><strong>Certified workbook batch</strong>${esc(D._source.outputBatch)}<br>${fmtInt(D.quality.detailRows)} detail rows · ${fmtInt(D.quality.uniqueScopes)} scopes</div>`;
  }
  function hero(kicker,title,dek){
    return `<div class="page-hero"><div><p class="eyebrow">${esc(kicker)}</p><h1>${title}</h1><p class="hero-dek">${esc(dek)}</p></div>${sourceChip()}</div>`;
  }
  function kpi(label,value,note,kind=''){
    return `<article class="kpi ${kind}"><div class="kpi-label">${esc(label)}</div><div class="kpi-value">${esc(value)}</div><div class="kpi-note">${note}</div></article>`;
  }
  function sectionHead(kicker,title,sub,meta=''){
    return `<div class="section-head"><div><span class="section-kicker">${esc(kicker)}</span><h2>${esc(title)}</h2><p class="section-sub">${esc(sub)}</p></div>${meta?`<div class="section-meta">${meta}</div>`:''}</div>`;
  }
  function option(value,label=value,selected=false){return `<option value="${esc(value)}"${selected?' selected':''}>${esc(label)}</option>`}
  function optionLabel(label,count){return `${label} · ${fmtInt(count)}`}
  function divisionLabel(value){return String(value).includes('(Unresolved)')?`${value} · mapping unresolved`:value}
  function tooltipBind(){
    let tip=$('.tooltip');
    if(!tip){tip=document.createElement('div');tip.className='tooltip';tip.hidden=true;document.body.appendChild(tip)}
    $$('[data-tip]').forEach(el=>{
      el.addEventListener('mouseenter',event=>{tip.innerHTML=event.currentTarget.dataset.tip;tip.hidden=false});
      el.addEventListener('mousemove',event=>{tip.style.left=Math.min(innerWidth-300,event.clientX+14)+'px';tip.style.top=Math.min(innerHeight-90,event.clientY+14)+'px'});
      el.addEventListener('mouseleave',()=>tip.hidden=true);
    });
  }
  function safeStorageGet(key,fallback){try{return sessionStorage.getItem(key)||fallback}catch(_){return fallback}}
  function safeStorageSet(key,value){try{sessionStorage.setItem(key,value)}catch(_){}}

  document.getElementById('print-page')?.addEventListener('click',()=>window.print());
  const sourceFooter=document.getElementById('footer-source');
  if(sourceFooter)sourceFooter.textContent=`Batch ${D._source.outputBatch} · built ${D._source.builtAt}`;

  // ---------- Briefing ----------
  const briefingState={level:safeStorageGet('v30-brief-level','System'),division:safeStorageGet('v30-brief-division','CFD')};
  function directBriefingDivisions(){
    const preferred=['CFD','EFD','WFD','PHD','MSD','MSD 1','MSD 2','Corporate Services'];
    const available=sortText(D.records.filter(r=>r.businessArea!=='WPC'&&r.locationType==='Division'&&r.divisionKey!=='SYS'&&r.divisionKey!=='Unclassified'&&!r.divisionKey.includes('(Unresolved)')).map(r=>r.divisionKey));
    return available.sort((a,b)=>{const ai=preferred.indexOf(a),bi=preferred.indexOf(b);return (ai<0?999:ai)-(bi<0?999:bi)||a.localeCompare(b)});
  }
  function ensureBriefingState(){
    if(!['System','Division'].includes(briefingState.level))briefingState.level='System';
    const divisions=directBriefingDivisions();
    if(!divisions.includes(briefingState.division))briefingState.division=divisions[0]||'';
  }
  function briefingRecords(){
    if(briefingState.level==='System')return D.summary.filter(r=>r.businessArea!=='WPC');
    return D.records.filter(r=>r.locationType==='Division'&&r.divisionKey===briefingState.division);
  }
  function metricCard(record,metric){
    if(!record)return `<article class="metric-card unavailable"><div><h3>${esc(metric.metric)}</h3><div class="metric-meta">No ${esc(briefingState.level.toLowerCase())}-level record in this workbook</div></div><div class="metric-value"><strong>—</strong>${statusPill('unavailable')}</div></article>`;
    return `<article class="metric-card ${record.goalStatus}"><div><h3>${esc(record.metric)}</h3><div class="metric-meta">${esc(record.businessArea)} · ${esc(record.dataAsOf)}<br>${esc(record.statusBasis)}</div></div><div class="metric-value"><strong>${esc(record.valueDisplay)}</strong><small>Local goal ${esc(record.goalDisplay)}</small>${statusPill(record.goalStatus)}</div></article>`;
  }
  function briefingHeatmap(){
    const divisions=directBriefingDivisions();
    const metrics=D.metrics.filter(m=>m.businessArea!=='WPC'&&D.records.some(r=>r.metric===m.metric&&r.locationType==='Division'));
    let html='<div class="heatmap-wrap"><table class="heatmap"><thead><tr><th>Metric</th>'+divisions.map(d=>`<th>${esc(d)}</th>`).join('')+'</tr></thead><tbody>';
    metrics.forEach(metric=>{
      html+=`<tr><th>${esc(metric.metric)}</th>`;
      divisions.forEach(division=>{
        const row=D.records.find(r=>r.locationType==='Division'&&r.divisionKey===division&&r.metric===metric.metric);
        const cls=row?row.goalStatus:'na';
        const label=row?(row.goalStatus==='met'?'Met':row.goalStatus==='missed'?'Missed':'N/A'):'—';
        const tip=row?`<strong>${esc(row.location)}</strong><br>${esc(row.valueDisplay)} · goal ${esc(row.goalDisplay)}<br>${esc(row.dataAsOf)}`:'No comparable division-level record';
        html+=`<td class="${cls}" data-tip="${esc(tip)}">${label}</td>`;
      });
      html+='</tr>';
    });
    return html+'</tbody></table></div><div class="legend"><span><i class="met"></i>Met local goal</span><span><i class="missed"></i>Missed local goal</span><span><i></i>Status unavailable or no record</span></div>';
  }
  function freshnessBars(records){
    const groups=new Map();records.forEach(r=>groups.set(r.dataAsOf,(groups.get(r.dataAsOf)||0)+1));
    const items=[...groups].sort((a,b)=>dateValue(b[0])-dateValue(a[0]));const max=Math.max(1,...items.map(i=>i[1]));
    if(!items.length)return '<div class="table-empty">No reporting dates are available for this scope.</div>';
    return `<div class="bar-list">${items.map(([date,count])=>`<div class="bar-row"><div class="bar-label">${esc(date)}<small>${count===1?'1 metric':`${count} metrics`}</small></div><div class="bar-track"><div class="bar-fill" style="width:${count/max*100}%"></div></div><div class="bar-value">${count}</div></div>`).join('')}</div>`;
  }
  function directDivisionBars(){
    const items=directBriefingDivisions().map(division=>{const records=D.records.filter(r=>r.businessArea!=='WPC'&&r.locationType==='Division'&&r.divisionKey===division);return {division,records,c:counts(records)}}).filter(item=>item.records.length).sort((a,b)=>(b.c.rate??-1)-(a.c.rate??-1)||b.c.eligible-a.c.eligible);
    if(!items.length)return '<div class="table-empty">No direct Division rows are available.</div>';
    return `<div class="bar-list">${items.map(item=>{const total=item.records.length;return `<div class="bar-row"><div class="bar-label">${esc(item.division)}<small>${item.c.met} met · ${item.c.missed} missed · ${item.c.unavailable} unavailable</small></div><div class="stack division-stack" aria-label="${item.c.met} met, ${item.c.missed} missed, ${item.c.unavailable} unavailable"><span class="met" style="width:${item.c.met/total*100}%"></span><span class="missed" style="width:${item.c.missed/total*100}%"></span><span class="unavailable" style="width:${item.c.unavailable/total*100}%"></span></div><div class="bar-value">${item.c.rate===null?'—':item.c.rate+'%'}<small>${item.c.met}/${item.c.eligible} eligible</small></div></div>`}).join('')}</div><div class="legend"><span><i class="met"></i>Met</span><span><i class="missed"></i>Missed</span><span><i></i>Status unavailable</span></div>`;
  }
  function readoutItem(kind,label,record,emptyText){
    if(!record)return `<article class="readout-item unavailable"><span>${esc(label)}</span><h3>${esc(emptyText)}</h3><strong>—</strong><p>No defensible record qualifies in this scope.</p></article>`;
    const value=kind==='missed'?`${record.gap.toFixed(1)}%`:kind==='met'?`+${record.gap.toFixed(1)}%`:record.valueDisplay;
    return `<article class="readout-item ${kind}"><span>${esc(label)}</span><h3>${esc(record.metric)}</h3><strong>${esc(value)}</strong><p>${esc(record.valueDisplay)} · local goal ${esc(record.goalDisplay)} · ${esc(record.dataAsOf)}</p></article>`;
  }
  function executiveReadout(records,gaps,wins){
    const c=counts(records),withoutDate=records.filter(r=>r.dataAsOf==='N/A').length,dates=sortText(records.map(r=>r.dataAsOf).filter(d=>d!=='N/A')).sort((a,b)=>dateValue(a)-dateValue(b));
    const dataTitle=c.unavailable?`${c.unavailable} status${c.unavailable===1?' is':'es are'} unavailable`:'All reported statuses are comparable';
    const dataValue=c.unavailable?`${c.unavailable}/${records.length}`:'0 unavailable';
    const dataDetail=`${withoutDate} without a reporting date · ${dateRange(records)}`;
    return `<section class="section">${sectionHead('01 · Executive readout','Three evidence-backed takeaways','A deterministic summary of the largest defensible gap, strongest goal margin, and most important comparability signal. No promotional language is generated.',`${records.length} metric records`)}<div class="readout-card"><div class="readout-lead"><strong>${gaps.length?`${esc(gaps[0].metric)} has the largest normalized missed-goal gap in this scope.`:'No defensible missed-goal gap exists in this scope.'}</strong><span>Use the supporting rankings below for the wider evidence set.</span></div><div class="grid-3">${readoutItem('missed','Attention',gaps[0],'No calculable priority gap')}${readoutItem('met','Protect',wins[0],'No calculable positive margin')}<article class="readout-item unavailable"><span>Data confidence</span><h3>${esc(dataTitle)}</h3><strong>${esc(dataValue)}</strong><p>${esc(dataDetail)}</p></article></div></div></section>`;
  }
  function renderBriefing(){
    ensureBriefingState();
    const records=briefingRecords();
    const c=counts(records);
    const scope=briefingState.level==='System'?'AdventHealth System':briefingState.division;
    const reported=records.filter(r=>r.valueRaw!=='N/A'&&r.valueRaw!=='Coming Soon').length;
    const dates=sortText(records.map(r=>r.dataAsOf).filter(d=>d!=='N/A')).sort((a,b)=>dateValue(a)-dateValue(b));
    const gaps=records.filter(r=>r.goalStatus==='missed'&&Number.isFinite(r.gap)).sort((a,b)=>a.gap-b.gap);
    const wins=records.filter(r=>r.goalStatus==='met'&&Number.isFinite(r.gap)).sort((a,b)=>b.gap-a.gap);
    let html=hero('Executive briefing',`Useful performance for <span>${esc(scope)}</span>`,`A decision-oriented read of values, local goals, reporting coverage, and freshness. Goal attainment is calculated conservatively and source variance remains separate.`);
    const briefingDivisions=directBriefingDivisions();
    html+=`<div class="control-bar"><div class="field"><label for="brief-level">View level</label><select id="brief-level">${option('System','AdventHealth System',briefingState.level==='System')}${option('Division','Division summary',briefingState.level==='Division')}</select></div><div class="field grow"><label for="brief-division">Division with direct records</label><select id="brief-division" ${briefingState.level==='System'?'disabled':''}>${briefingDivisions.map(d=>option(d,optionLabel(d,uniq(D.records.filter(r=>r.locationType==='Division'&&r.divisionKey===d).map(r=>r.metric)).length),d===briefingState.division)).join('')}</select></div><button class="button" id="brief-reset">Reset view</button></div>`;
    if(dates.length>1)html+=`<div class="notice warn"><strong>Mixed-date snapshot.</strong><span>This scope contains ${dates.length} reporting labels from ${esc(dates[0])} through ${esc(dates[dates.length-1])}. Each metric keeps its own date; no trend is inferred.</span></div>`;
    if(briefingState.level==='Division'&&records.length<10)html+=`<div class="notice"><strong>Partial division scorecard.</strong><span>${esc(scope)} has ${records.length} direct Division rows. Metrics reported only through a different hierarchy remain unavailable rather than being reassigned.</span></div>`;
    html+='<div class="kpi-grid">';
    html+=kpi('Goal attainment',c.rate===null?'—':c.rate+'%',c.eligible?`<strong>${c.met} of ${c.eligible}</strong> directly comparable metrics meet local goal.`:'No directly comparable goal records.','met');
    html+=kpi('Missed goal',fmtInt(c.missed),`${gaps.length?`Largest defensible gap: <strong>${esc(gaps[0].metric)}</strong>.`:'No calculable missed-goal rows.'}`,'missed');
    html+=kpi('Status unavailable',fmtInt(c.unavailable),`Values may still exist; unavailable means <strong>goal status cannot be defended</strong>.`,'unavailable');
    html+=kpi('Reported values',`${reported}/${records.length}`,`Metric dates span <strong>${esc(dateRange(records))}</strong>.`,'fresh');
    html+='</div>';

    html+=executiveReadout(records,gaps,wins);

    html+=`<section class="section">${sectionHead('02 · Decision context','Comparability and reporting freshness','Division composition uses only direct Division records. Reporting-date bars count metrics; they do not imply a time series.')}<div class="grid-2"><div class="card"><h3 class="card-title">Direct division status composition</h3><p class="card-sub">Green, red, and gray show all direct Division records; the percentage at right uses met plus missed as the eligible denominator. No lower-level rollups are used.</p>${directDivisionBars()}</div><div class="card"><h3 class="card-title">Metrics by reporting date</h3><p class="card-sub">A freshness inventory for the selected executive scope. Longer bars mean more metrics share that reporting label.</p>${freshnessBars(records)}</div></div></section>`;

    html+=`<section class="section">${sectionHead('03 · Portfolio','Performance by strategic aspiration','Equal-weight metric attainment within each aspiration; only records with a comparable local goal enter the denominator.',`${c.eligible} eligible metrics`)}<div class="aspiration-grid">`;
    const pillars=uniq(D.metrics.filter(m=>m.businessArea!=='WPC').map(m=>m.pillar));
    pillars.forEach(pillar=>{
      const prs=records.filter(r=>r.pillar===pillar);const pc=counts(prs);const area=D.metrics.find(m=>m.pillar===pillar)?.businessArea||'';
      html+=`<article class="aspiration-card" data-area="${esc(area)}"><h3>${esc(pillar)}</h3><div class="aspiration-score"><strong>${pc.rate===null?'—':pc.rate+'%'}</strong><span>${pc.eligible?`${pc.met} of ${pc.eligible} met`:'No eligible goals'}</span></div><div class="stack"><span class="met" style="width:${prs.length?pc.met/prs.length*100:0}%"></span><span class="missed" style="width:${prs.length?pc.missed/prs.length*100:0}%"></span><span class="unavailable" style="width:${prs.length?pc.unavailable/prs.length*100:100}%"></span></div><div class="aspiration-meta"><span>${pc.missed} missed</span><span>${pc.unavailable} unavailable</span></div></article>`;
    });
    html+='</div></section>';

    html+=`<section class="section">${sectionHead('04 · Supporting rankings','Where attention is most useful','Ranked only where a numeric local goal and direction are known. Gaps are normalized to the local goal.',`${gaps.length} missed · ${wins.length} met`)}<div class="grid-2"><div class="card"><h3 class="card-title">Priority gaps</h3><p class="card-sub">Largest negative goal gaps in this scope.</p><div class="insight-list">`;
    html+=(gaps.length?gaps.slice(0,5).map((r,i)=>`<div class="insight-item"><span class="insight-rank">${i+1}</span><div><h4>${esc(r.metric)}</h4><p>${esc(r.valueDisplay)} · local goal ${esc(r.goalDisplay)} · ${esc(r.dataAsOf)}</p></div><div class="insight-number negative">${Number.isFinite(r.gap)?r.gap.toFixed(1)+'%':'—'}</div></div>`).join(''):'<div class="table-empty">No defensible missed-goal gaps for this scope.</div>');
    html+=`</div></div><div class="card"><h3 class="card-title">Strengths to protect</h3><p class="card-sub">Largest positive margins against known local goals.</p><div class="insight-list">`;
    html+=(wins.length?wins.slice(0,5).map((r,i)=>`<div class="insight-item"><span class="insight-rank">${i+1}</span><div><h4>${esc(r.metric)}</h4><p>${esc(r.valueDisplay)} · local goal ${esc(r.goalDisplay)} · ${esc(r.dataAsOf)}</p></div><div class="insight-number positive">+${r.gap.toFixed(1)}%</div></div>`).join(''):'<div class="table-empty">No defensible positive goal margins for this scope.</div>');
    html+='</div></div></div></section>';

    html+=`<section class="section">${sectionHead('05 · Grouped scorecard',`${scope} metric record by aspiration`,'The former board’s useful grouping is retained without its fixed-height blanks, global date, or ambiguous not-reported label.',`${reported} values reported`)}<div class="aspiration-board">`;
    pillars.forEach(pillar=>{const metrics=D.metrics.filter(m=>m.businessArea!=='WPC'&&m.pillar===pillar);const area=metrics[0]?.businessArea||'';const groupRows=records.filter(r=>r.pillar===pillar);const gc=counts(groupRows);html+=`<section class="aspiration-group" data-area="${esc(area)}"><header><div><span>${esc(area)}</span><h3>${esc(pillar)}</h3></div><small>${gc.met} met · ${gc.missed} missed · ${gc.unavailable} unavailable</small></header><div class="aspiration-group-body">${metrics.map(metric=>metricCard(records.find(r=>r.metric===metric.metric),metric)).join('')}</div></section>`});
    html+='</div></section>';
    if(briefingState.level==='System')html+=`<section class="section">${sectionHead('06 · Division view','Direct division-level goal status','This matrix does not roll up lower-level rows or force unlike hierarchies together. Hover for value, local goal, and date.')}<div class="card">${briefingHeatmap()}</div></section>`;
    root.innerHTML=html;
    $('#brief-level').addEventListener('change',event=>{briefingState.level=event.target.value;safeStorageSet('v30-brief-level',briefingState.level);renderBriefing()});
    $('#brief-division').addEventListener('change',event=>{briefingState.division=event.target.value;safeStorageSet('v30-brief-division',briefingState.division);renderBriefing()});
    $('#brief-reset').addEventListener('click',()=>{briefingState.level='System';renderBriefing()});
    tooltipBind();
  }

  // ---------- Insights ----------
  const preferredType={
    'Internal Leader Fill Rate':'Region','Leader Effectiveness (Facility Leadership)':'FRL','Opportunity to Learn and Grow':'FRL',
    'Forecast and Hire':'FRL','Team Member Engagement':'FRL','Total Turnover':'Costing Company','Physician Engagement':'Hospital',
    'Digital Tool Utilization':'Market','Patient Experience – ED LTR':'Facility','Patient Experience – Inpatient LTR':'Facility','Patient Experience – Med Practice LTR':'Facility',
    'CMS Overall Hospital Star Rating':'Facility','Leapfrog Hospital Safety Grade':'Campus','EBITDA $':'Facility','TOR $':'Facility','TOR Growth Rate':'Facility','Domestic Spend':'Division'
  };
  const insightState={area:safeStorageGet('v30-insight-area','Team'),metric:safeStorageGet('v30-insight-metric','Team Member Engagement'),type:safeStorageGet('v30-insight-type','FRL'),division:safeStorageGet('v30-insight-division','All'),date:'All',secondary:''};
  function nonCorporateRows(metric){return D.records.filter(r=>r.metric===metric&&r.locationType!=='Corporate')}
  function metricsForArea(area){return D.metrics.filter(m=>m.businessArea===area&&nonCorporateRows(m.metric).length>0)}
  function defaultType(metric,rows){
    const types=sortText(rows.map(r=>r.locationType));
    if(types.includes(preferredType[metric]))return preferredType[metric];
    return types.sort((a,b)=>rows.filter(r=>r.locationType===b).length-rows.filter(r=>r.locationType===a).length)[0]||'';
  }
  function insightRows(){return D.records.filter(r=>r.businessArea===insightState.area&&r.metric===insightState.metric&&r.locationType===insightState.type&&(insightState.division==='All'||r.divisionKey===insightState.division)&&(insightState.date==='All'||r.dataAsOf===insightState.date))}
  function ensureInsightState(){
    const metrics=metricsForArea(insightState.area);
    if(!metrics.some(m=>m.metric===insightState.metric))insightState.metric=metrics[0]?.metric||'';
    const rows=nonCorporateRows(insightState.metric);
    const types=sortText(rows.map(r=>r.locationType));
    if(!types.includes(insightState.type))insightState.type=defaultType(insightState.metric,rows);
    const divisions=sortText(rows.filter(r=>r.locationType===insightState.type).map(r=>r.divisionKey));
    if(divisions.length===1)insightState.division=divisions[0];
    else if(insightState.division!=='All'&&!divisions.includes(insightState.division))insightState.division='All';
    const divisionRows=rows.filter(r=>r.locationType===insightState.type&&(insightState.division==='All'||r.divisionKey===insightState.division));
    const dates=sortText(divisionRows.map(r=>r.dataAsOf));
    if(dates.length===1)insightState.date=dates[0];
    else if(insightState.date!=='All'&&!dates.includes(insightState.date))insightState.date='All';
  }
  function rankedBars(records,limit=14){
    const usable=records.filter(validValue).sort((a,b)=>b.valueNumber-a.valueNumber).slice(0,limit);
    if(!usable.length)return '<div class="table-empty">No numeric peer values for this selection.</div>';
    const values=usable.map(r=>r.valueNumber);const min=Math.min(...values),max=Math.max(...values);const span=max-min||1;
    return `<div class="bar-list">${usable.map(r=>`<div class="bar-row"><div class="bar-label">${esc(r.location)}<small>${esc(r.divisionKey)} · ${esc(r.dataAsOf)}</small></div><div class="bar-track"><div class="bar-fill ${r.goalStatus}" style="width:${8+(r.valueNumber-min)/span*92}%"></div></div><div class="bar-value">${esc(r.valueDisplay)}</div></div>`).join('')}</div>`;
  }
  function histogramChart(records,metricMeta){
    const values=records.filter(validValue).map(r=>r.valueNumber).sort((a,b)=>a-b);
    if(values.length<5)return '<div class="table-empty">At least five numeric peer values are required for a distribution.</div>';
    const min=values[0],max=values[values.length-1],distinct=uniq(values);let bins=[];
    if(distinct.length<=10){
      bins=distinct.map(value=>({label:formatNumeric(value,metricMeta.unit),count:values.filter(v=>v===value).length}));
    }else{
      const n=Math.min(10,Math.max(5,Math.ceil(Math.sqrt(values.length))));const width=(max-min)/n||1;
      bins=Array.from({length:n},(_,i)=>{const low=min+i*width,high=i===n-1?max:min+(i+1)*width;return {label:`${formatNumeric(low,metricMeta.unit)}–${formatNumeric(high,metricMeta.unit)}`,count:0}});
      values.forEach(value=>bins[Math.min(n-1,Math.floor((value-min)/width))].count++);
    }
    const peak=Math.max(1,...bins.map(b=>b.count)),q1=quantile(values,.25),q3=quantile(values,.75);
    return `<p class="chart-finding">The middle 50% of reported values spans <strong>${esc(formatNumeric(q1,metricMeta.unit))}</strong> to <strong>${esc(formatNumeric(q3,metricMeta.unit))}</strong>; observed range ${esc(formatNumeric(min,metricMeta.unit))} to ${esc(formatNumeric(max,metricMeta.unit))}.</p><div class="histogram" style="--bins:${bins.length}" role="img" aria-label="Distribution of ${esc(insightState.metric)} across ${values.length} peer records">${bins.map(bin=>`<div class="hist-column"><strong>${bin.count}</strong><div class="hist-track"><span style="height:${bin.count/peak*100}%"></span></div><small>${esc(bin.label)}</small></div>`).join('')}</div>`;
  }
  function goalGapBars(records,limit=12){
    const gaps=records.filter(r=>r.goalStatus==='missed'&&Number.isFinite(r.gap)).sort((a,b)=>a.gap-b.gap).slice(0,limit);
    if(!gaps.length)return '<div class="table-empty">No defensible missed-goal gaps exist for this cohort.</div>';
    const max=Math.max(1,...gaps.map(r=>Math.abs(r.gap)));
    return `<div class="bar-list">${gaps.map(r=>`<div class="bar-row"><div class="bar-label">${esc(r.location)}<small>${esc(r.valueDisplay)} · local goal ${esc(r.goalDisplay)}</small></div><div class="bar-track"><div class="bar-fill missed" style="width:${Math.abs(r.gap)/max*100}%"></div></div><div class="bar-value negative">${r.gap.toFixed(1)}%</div></div>`).join('')}</div>`;
  }
  function divisionGoalBars(records){
    const grouped=new Map();records.forEach(r=>{if(!grouped.has(r.divisionKey))grouped.set(r.divisionKey,[]);grouped.get(r.divisionKey).push(r)});
    const items=[...grouped].map(([division,rows])=>({division,rows,c:counts(rows)})).filter(item=>item.c.eligible).sort((a,b)=>b.c.rate-a.c.rate||b.c.eligible-a.c.eligible);
    if(!items.length)return '<div class="table-empty">No division in this cohort has a defensible local-goal denominator.</div>';
    return `<div class="bar-list">${items.map(item=>`<div class="bar-row"><div class="bar-label">${esc(divisionLabel(item.division))}<small>${item.c.met} met · ${item.c.missed} missed · ${item.c.unavailable} unavailable</small></div><div class="bar-track"><div class="bar-fill met" style="width:${item.c.rate}%"></div></div><div class="bar-value">${item.c.rate}%<small>N=${item.c.eligible}</small></div></div>`).join('')}</div>`;
  }
  function ytdView(records){
    const rows=records.filter(r=>Number.isFinite(r.ytdNumber)&&Number.isFinite(r.valueNumber)).sort((a,b)=>Math.abs(b.valueNumber-b.ytdNumber)-Math.abs(a.valueNumber-a.ytdNumber)).slice(0,12);
    if(!rows.length)return '';
    return `<section class="section">${sectionHead('03 · Current vs YTD','Where the current reading differs from YTD','Shown only because this metric carries both fields in the workbook. This is not a monthly trend.',`${rows.length} largest changes shown`)}<div class="card"><div class="bar-list">${rows.map(r=>{const delta=r.valueNumber-r.ytdNumber;return `<div class="bar-row"><div class="bar-label">${esc(r.location)}<small>Current ${esc(r.valueDisplay)} · YTD ${esc(r.ytdDisplay)}</small></div><div class="bar-track"><div class="bar-fill ${delta>=0?'met':'missed'}" style="width:${clamp(50+delta*3,8,100)}%"></div></div><div class="bar-value">${delta>0?'+':''}${delta.toFixed(1)}</div></div>`}).join('')}</div></div></section>`;
  }
  function correlationData(primaryRows,secondaryMetric){
    const second=D.records.filter(r=>r.metric===secondaryMetric&&r.locationType===insightState.type&&(insightState.division==='All'||r.divisionKey===insightState.division)&&(insightState.date==='All'||r.dataAsOf===insightState.date)&&validValue(r));
    const map=new Map(second.map(r=>[r.scopeId,r]));
    const pairs=primaryRows.filter(validValue).map(a=>({a,b:map.get(a.scopeId)})).filter(p=>p.b&&validValue(p.b));
    if(pairs.length<5)return {pairs,r:null};
    const xs=pairs.map(p=>p.a.valueNumber),ys=pairs.map(p=>p.b.valueNumber),n=pairs.length;
    const mx=xs.reduce((a,b)=>a+b,0)/n,my=ys.reduce((a,b)=>a+b,0)/n;
    let num=0,dx=0,dy=0;for(let i=0;i<n;i++){const x=xs[i]-mx,y=ys[i]-my;num+=x*y;dx+=x*x;dy+=y*y}
    return {pairs,r:dx&&dy?num/Math.sqrt(dx*dy):null};
  }
  function scatterSvg(data,secondaryMetric){
    if(data.pairs.length<5||data.r===null)return '<div class="table-empty">At least five matched, varying peer records are required. No relationship is estimated for this selection.</div>';
    const width=680,height=330,pad=44;const xs=data.pairs.map(p=>p.a.valueNumber),ys=data.pairs.map(p=>p.b.valueNumber);
    let xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);if(xmin===xmax)xmax=xmin+1;if(ymin===ymax)ymax=ymin+1;
    const sx=x=>pad+(x-xmin)/(xmax-xmin)*(width-pad*2),sy=y=>height-pad-(y-ymin)/(ymax-ymin)*(height-pad*2);
    const points=data.pairs.map(p=>`<circle class="point" cx="${sx(p.a.valueNumber).toFixed(1)}" cy="${sy(p.b.valueNumber).toFixed(1)}" r="4.5"><title>${esc(p.a.location)}: ${esc(p.a.valueDisplay)} / ${esc(p.b.valueDisplay)}</title></circle>`).join('');
    return `<svg class="svg-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Scatterplot of ${esc(insightState.metric)} and ${esc(secondaryMetric)}"><line class="axis" x1="${pad}" y1="${height-pad}" x2="${width-pad}" y2="${height-pad}"/><line class="axis" x1="${pad}" y1="${pad}" x2="${pad}" y2="${height-pad}"/>${points}<text x="${width/2}" y="${height-8}" text-anchor="middle">${esc(insightState.metric)}</text><text transform="translate(12 ${height/2}) rotate(-90)" text-anchor="middle">${esc(secondaryMetric)}</text></svg>`;
  }
  function renderInsights(){
    ensureInsightState();const rows=insightRows();const c=counts(rows);const numeric=rows.filter(validValue);const med=median(numeric.map(r=>r.valueNumber));const metricMeta=D.metrics.find(m=>m.metric===insightState.metric)||{};
    const areas=['Learning','Team','Consumer','Clinical','Financial','Risk'].filter(area=>metricsForArea(area).length);
    const areaMetrics=metricsForArea(insightState.area);const metricRows=nonCorporateRows(insightState.metric);const types=sortText(metricRows.map(r=>r.locationType));
    const typeRows=metricRows.filter(r=>r.locationType===insightState.type);const divisions=sortText(typeRows.map(r=>r.divisionKey));
    const divisionRows=typeRows.filter(r=>insightState.division==='All'||r.divisionKey===insightState.division);
    const dates=sortText(divisionRows.map(r=>r.dataAsOf)).sort((a,b)=>dateValue(b)-dateValue(a));
    const secondaryCandidates=D.metrics.filter(m=>m.metric!==insightState.metric&&D.records.some(r=>r.metric===m.metric&&r.locationType===insightState.type&&(insightState.division==='All'||r.divisionKey===insightState.division)&&(insightState.date==='All'||r.dataAsOf===insightState.date))).map(m=>m.metric);
    let best={metric:'',n:0};secondaryCandidates.forEach(metric=>{const n=correlationData(rows,metric).pairs.length;if(n>best.n)best={metric,n}});
    if(!secondaryCandidates.includes(insightState.secondary))insightState.secondary=best.metric||secondaryCandidates[0]||'';
    const relationship=insightState.secondary?correlationData(rows,insightState.secondary):{pairs:[],r:null};
    let html=hero('Comparable peer insights','Ask a <span>specific question</span>','Choose a metric and one valid hierarchy level. Every peer statistic below compares like-for-like records and shows its sample size.');
    html+=`<div class="control-bar"><div class="field"><label for="in-area">Business area</label><select id="in-area">${areas.map(a=>option(a,optionLabel(a,metricsForArea(a).length),a===insightState.area)).join('')}</select></div><div class="field grow"><label for="in-metric">Metric</label><select id="in-metric" ${areaMetrics.length===1?'disabled':''}>${areaMetrics.map(m=>option(m.metric,optionLabel(m.metric,nonCorporateRows(m.metric).length),m.metric===insightState.metric)).join('')}</select></div><div class="field"><label for="in-type">Compare as</label><select id="in-type" ${types.length===1?'disabled':''}>${types.map(t=>option(t,optionLabel(t,metricRows.filter(r=>r.locationType===t).length),t===insightState.type)).join('')}</select></div><div class="field"><label for="in-division">Division</label><select id="in-division" ${divisions.length===1?'disabled':''}>${divisions.length>1?option('All',optionLabel('All divisions',typeRows.length),insightState.division==='All'):''}${divisions.map(d=>option(d,optionLabel(divisionLabel(d),typeRows.filter(r=>r.divisionKey===d).length),d===insightState.division)).join('')}</select></div><div class="field"><label for="in-date">Data as of</label><select id="in-date" ${dates.length===1?'disabled':''}>${dates.length>1?option('All',optionLabel('All reporting dates',divisionRows.length),insightState.date==='All'):''}${dates.map(d=>option(d,optionLabel(d,divisionRows.filter(r=>r.dataAsOf===d).length),d===insightState.date)).join('')}</select></div></div>`;
    html+=`<div class="notice"><strong>Comparable cohort.</strong><span>${fmtInt(rows.length)} ${esc(insightState.type)} records for ${esc(insightState.metric)}${insightState.division==='All'?' across all available division labels':` in ${esc(divisionLabel(insightState.division))}`}. Reporting selection: ${esc(insightState.date==='All'?dateRange(rows):insightState.date)}.</span></div>`;
    html+='<div class="kpi-grid">';
    html+=kpi('Peer records',fmtInt(rows.length),`<strong>${numeric.length}</strong> carry a numeric value.`,'fresh');
    html+=kpi('Meet local goal',c.rate===null?'—':c.rate+'%',c.eligible?`${c.met} of ${c.eligible} eligible peers.`:'No directly comparable local goals.','met');
    html+=kpi('Miss local goal',fmtInt(c.missed),`${c.unavailable} status-unavailable records are excluded.`,'missed');
    html+=kpi('Peer median',formatNumeric(med,metricMeta.unit),`Median of <strong>${numeric.length}</strong> numeric peer values.`,'');
    html+='</div>';
    html+=`<section class="section">${sectionHead('01 · Distribution','Peer value distribution','Ranks reported values within the selected, like-for-like cohort. Bar color uses derived local-goal status.',`${numeric.length} numeric values`)}<div class="grid-2"><div class="card"><h3 class="card-title">Highest reported values</h3><p class="card-sub">Directionality depends on the metric; highest is not automatically best.</p>${rankedBars(rows)}</div><div class="card"><h3 class="card-title">Goal-status composition</h3><p class="card-sub">Unavailable records remain visible in the denominator but not the attainment rate.</p><div class="donut-wrap"><div class="donut" style="--met:${rows.length?c.met/rows.length*100:0}%;--eligible:${rows.length?c.eligible/rows.length*100:0}%"><div class="donut-center"><strong>${c.rate===null?'—':c.rate+'%'}</strong><span>of eligible</span></div></div><div><div class="insight-list"><div class="insight-item"><span class="status-pill met">Met</span><div><h4>${c.met} peer records</h4><p>At or above/below the local goal as appropriate.</p></div></div><div class="insight-item"><span class="status-pill missed">Missed</span><div><h4>${c.missed} peer records</h4><p>Defensible negative gap to local goal.</p></div></div><div class="insight-item"><span class="status-pill unavailable">Unavailable</span><div><h4>${c.unavailable} peer records</h4><p>Value may exist, but goal logic is not defensible.</p></div></div></div></div></div></div></div></section>`;
    html+=`<section class="section">${sectionHead('02 · Cohort diagnostics','Shape, gaps, and division comparison','Each visual stays within the selected metric, hierarchy, date, and division cohort. No hierarchy levels are combined.',`${numeric.length} numeric peers`)}<div class="grid-2"><div class="card"><h3 class="card-title">Value distribution</h3><p class="card-sub">Frequency by observed value range; this exposes concentration and spread that a median alone can hide.</p>${histogramChart(rows,metricMeta)}</div><div class="card"><h3 class="card-title">Largest local-goal gaps</h3><p class="card-sub">Only missed records with a comparable numeric local goal. Bar length is the normalized percentage gap.</p>${goalGapBars(rows)}</div></div><div class="card chart-card"><h3 class="card-title">Goal attainment by division</h3><p class="card-sub">Like-for-like ${esc(insightState.type)} records only. Percentages use each division’s eligible local-goal denominator; unavailable rows are reported separately.</p>${divisionGoalBars(rows)}</div></section>`;
    html+=ytdView(rows);
    const hasYtd=rows.some(r=>Number.isFinite(r.ytdNumber)&&Number.isFinite(r.valueNumber));
    html+=`<section class="section">${sectionHead(`${hasYtd?'04':'03'} · Relationship explorer`,'Matched-scope relationship','Pearson correlation is calculated only where both metrics exist for the exact same scope and location type. It is descriptive, not causal.',relationship.r===null?`${relationship.pairs.length} matches`:`r = ${relationship.r.toFixed(2)} · N = ${relationship.pairs.length}`)}<div class="card"><div class="control-bar"><div class="field grow"><label for="in-secondary">Compare with</label><select id="in-secondary">${secondaryCandidates.map(m=>option(m,m,m===insightState.secondary)).join('')}</select></div></div>${insightState.secondary?scatterSvg(relationship,insightState.secondary):'<div class="table-empty">No second metric shares this hierarchy level.</div>'}${relationship.r!==null?`<div class="notice"><strong>${Math.abs(relationship.r)>=.7?'Strong':Math.abs(relationship.r)>=.5?'Moderate':'Modest'} ${relationship.r>=0?'positive':'negative'} relationship.</strong><span>Across ${relationship.pairs.length} matched ${esc(insightState.type)} records, r = ${relationship.r.toFixed(2)}. This is a prompt for investigation, not evidence of a driver.</span></div>`:''}</div></section>`;
    root.innerHTML=html;
    $('#in-area').addEventListener('change',e=>{insightState.area=e.target.value;insightState.metric='';insightState.type='';insightState.division='All';insightState.date='All';insightState.secondary='';safeStorageSet('v30-insight-area',insightState.area);renderInsights()});
    $('#in-metric').addEventListener('change',e=>{insightState.metric=e.target.value;insightState.type='';insightState.division='All';insightState.date='All';insightState.secondary='';safeStorageSet('v30-insight-metric',insightState.metric);renderInsights()});
    $('#in-type').addEventListener('change',e=>{insightState.type=e.target.value;insightState.division='All';insightState.date='All';insightState.secondary='';safeStorageSet('v30-insight-type',insightState.type);renderInsights()});
    $('#in-division').addEventListener('change',e=>{insightState.division=e.target.value;insightState.date='All';safeStorageSet('v30-insight-division',insightState.division);renderInsights()});
    $('#in-date').addEventListener('change',e=>{insightState.date=e.target.value;insightState.secondary='';renderInsights()});
    $('#in-secondary')?.addEventListener('change',e=>{insightState.secondary=e.target.value;renderInsights()});
  }

  // ---------- Data Explorer ----------
  const explorerState={area:safeStorageGet('v30-ex-area','Vision 2030'),view:safeStorageGet('v30-ex-view','scorecard'),metric:'All',division:'All',type:'All',status:'All',date:'All',search:'',sort:'metric',direction:1};
  function baseExplorerRows(){return explorerState.area==='Vision 2030'?D.summary:D.records.filter(r=>r.businessArea===explorerState.area)}
  function ensureExplorerState(){
    const base=baseExplorerRows();
    const metrics=sortText(base.map(r=>r.metric));
    if(explorerState.metric!=='All'&&!metrics.includes(explorerState.metric))explorerState.metric='All';
    const metricRows=base.filter(r=>explorerState.metric==='All'||r.metric===explorerState.metric);
    const types=sortText(metricRows.map(r=>r.locationType));
    if(explorerState.view==='scorecard'&&explorerState.area!=='Vision 2030'&&explorerState.metric!=='All'&&explorerState.type==='All'){
      const peerRows=metricRows.filter(r=>r.locationType!=='Corporate');
      explorerState.type=defaultType(explorerState.metric,peerRows.length?peerRows:metricRows);
    }
    if(explorerState.type!=='All'&&!types.includes(explorerState.type))explorerState.type='All';
    const typeRows=metricRows.filter(r=>explorerState.type==='All'||r.locationType===explorerState.type);
    const divisions=sortText(typeRows.map(r=>r.divisionKey));
    if(divisions.length===1)explorerState.division=divisions[0];
    else if(explorerState.division!=='All'&&!divisions.includes(explorerState.division))explorerState.division='All';
    const divisionRows=typeRows.filter(r=>explorerState.division==='All'||r.divisionKey===explorerState.division);
    const dates=sortText(divisionRows.map(r=>r.dataAsOf));
    if(explorerState.date!=='All'&&!dates.includes(explorerState.date))explorerState.date='All';
    if(dates.length===1)explorerState.date=dates[0];
  }
  function filteredExplorerRows(){
    const query=explorerState.search.trim().toLowerCase();
    return baseExplorerRows().filter(r=>(explorerState.metric==='All'||r.metric===explorerState.metric)&&(explorerState.division==='All'||r.divisionKey===explorerState.division)&&(explorerState.type==='All'||r.locationType===explorerState.type)&&(explorerState.status==='All'||r.goalStatus===explorerState.status)&&(explorerState.date==='All'||r.dataAsOf===explorerState.date)&&(!query||[r.metric,r.location,r.divisionKey,r.locationType,r.valueDisplay,r.goalDisplay].some(v=>String(v).toLowerCase().includes(query)))).sort((a,b)=>{
      const av=a[explorerState.sort],bv=b[explorerState.sort];
      if(typeof av==='number'&&typeof bv==='number')return (av-bv)*explorerState.direction;
      return String(av??'').localeCompare(String(bv??''),undefined,{numeric:true})*explorerState.direction;
    });
  }
  function explorerControls(){
    const base=baseExplorerRows();
    const metrics=sortText(base.map(r=>r.metric));
    const metricRows=base.filter(r=>explorerState.metric==='All'||r.metric===explorerState.metric);
    const types=sortText(metricRows.map(r=>r.locationType));
    const typeRows=metricRows.filter(r=>explorerState.type==='All'||r.locationType===explorerState.type);
    const divisions=sortText(typeRows.map(r=>r.divisionKey));
    const divisionRows=typeRows.filter(r=>explorerState.division==='All'||r.divisionKey===explorerState.division);
    const dates=sortText(divisionRows.map(r=>r.dataAsOf)).sort((a,b)=>dateValue(b)-dateValue(a));
    const statusRows=divisionRows.filter(r=>explorerState.date==='All'||r.dataAsOf===explorerState.date);
    const allowAllTypes=explorerState.view==='table'||explorerState.metric==='All'||explorerState.area==='Vision 2030';
    const typeOptions=(allowAllTypes?option('All',optionLabel('All types',metricRows.length),explorerState.type==='All'):'')+types.map(t=>option(t,optionLabel(t,metricRows.filter(r=>r.locationType===t).length),t===explorerState.type)).join('');
    const divisionOptions=(divisions.length>1?option('All',optionLabel('All divisions',typeRows.length),explorerState.division==='All'):'')+divisions.map(d=>option(d,optionLabel(divisionLabel(d),typeRows.filter(r=>r.divisionKey===d).length),d===explorerState.division)).join('');
    const dateOptions=(dates.length>1?option('All',optionLabel('All reporting dates',divisionRows.length),explorerState.date==='All'):'')+dates.map(d=>option(d,optionLabel(d,divisionRows.filter(r=>r.dataAsOf===d).length),d===explorerState.date)).join('');
    return `<div class="control-bar"><div class="field grow"><label for="ex-metric">Metric</label><select id="ex-metric">${option('All',optionLabel('All metrics',base.length),explorerState.metric==='All')}${metrics.map(m=>option(m,optionLabel(m,base.filter(r=>r.metric===m).length),m===explorerState.metric)).join('')}</select></div><div class="field"><label for="ex-type">Compare as</label><select id="ex-type" ${types.length===1&&!allowAllTypes?'disabled':''}>${typeOptions}</select></div><div class="field"><label for="ex-division">Division</label><select id="ex-division" ${divisions.length===1?'disabled':''}>${divisionOptions}</select></div><div class="field"><label for="ex-date">Data as of</label><select id="ex-date" ${dates.length===1?'disabled':''}>${dateOptions}</select></div><div class="field"><label for="ex-status">Goal status</label><select id="ex-status">${option('All',optionLabel('All statuses',statusRows.length),explorerState.status==='All')}${option('met',optionLabel('Met goal',statusRows.filter(r=>r.goalStatus==='met').length),explorerState.status==='met')}${option('missed',optionLabel('Missed goal',statusRows.filter(r=>r.goalStatus==='missed').length),explorerState.status==='missed')}${option('unavailable',optionLabel('Unavailable',statusRows.filter(r=>r.goalStatus==='unavailable').length),explorerState.status==='unavailable')}</select></div><div class="field grow"><label for="ex-search">Search records</label><input id="ex-search" type="search" value="${esc(explorerState.search)}" placeholder="Location, metric, division…"></div></div>`;
  }
  function overviewCards(rows){
    const groups=new Map();rows.forEach(r=>{if(!groups.has(r.metric))groups.set(r.metric,[]);groups.get(r.metric).push(r)});
    if(!groups.size)return '<div class="table-empty">No records match the current filters.</div>';
    const indexMode=explorerState.area!=='Vision 2030'&&explorerState.metric==='All'&&explorerState.type==='All';
    return `<div class="scorecard">${[...groups].map(([metric,items])=>{
      if(indexMode){
        const peers=items.filter(r=>r.locationType!=='Corporate');const type=defaultType(metric,peers.length?peers:items);const cohort=items.filter(r=>r.locationType===type);
        return `<article class="metric-card unavailable" data-filter-metric="${esc(metric)}"><div><h3>${esc(metric)}</h3><div class="metric-meta">Available as ${sortText(items.map(r=>r.locationType)).map(esc).join(' · ')}<br>Default peer level: ${esc(type)}</div></div><div class="metric-value"><strong>${fmtInt(cohort.length)}</strong><small>${esc(type)} records · select to inspect</small><span class="status-pill unavailable">Choose metric</span></div></article>`;
      }
      const c=counts(items);const sample=items.length===1?items[0]:null;
      return `<article class="metric-card ${sample?sample.goalStatus:'unavailable'}" data-filter-metric="${esc(metric)}"><div><h3>${esc(metric)}</h3><div class="metric-meta">${fmtInt(items.length)} record${items.length===1?'':'s'} · ${esc(dateRange(items))}<br>${sortText(items.map(r=>r.locationType)).slice(0,4).map(esc).join(' · ')}</div></div><div class="metric-value"><strong>${sample?esc(sample.valueDisplay):(c.rate===null?'—':c.rate+'%')}</strong><small>${sample?'Local goal '+esc(sample.goalDisplay):`${c.met} of ${c.eligible} eligible met`}</small>${statusPill(sample?sample.goalStatus:(c.eligible&&c.met===c.eligible?'met':c.missed?'missed':'unavailable'))}</div></article>`;
    }).join('')}</div>`;
  }
  function explorerComposition(rows){
    let key,title,sub;
    if(explorerState.area==='Vision 2030'){key=r=>r.businessArea;title='Executive metrics by business area';sub='Counts of metric records in the enterprise sheet, not performance weights.'}
    else if(explorerState.type==='All'){key=r=>r.locationType;title='Rows by hierarchy level';sub='Shows how the filtered audit rows are distributed across overlapping reporting levels.'}
    else if(explorerState.division==='All'){key=r=>r.divisionKey;title='Available records by division';sub=`Counts of filtered ${explorerState.type} records. These are available rows, not a completeness rate.`}
    else{key=r=>r.goalStatus;title='Goal-status record mix';sub='Counts within the selected metric, hierarchy, division, date, and search result.'}
    const grouped=new Map();rows.forEach(r=>{const label=key(r);grouped.set(label,(grouped.get(label)||0)+1)});
    const items=[...grouped].sort((a,b)=>b[1]-a[1]);if(items.length<2)return '';
    const max=Math.max(...items.map(i=>i[1]));
    const color=label=>label==='met'?'var(--green)':label==='missed'?'var(--red)':label==='unavailable'?'var(--gray)':areaColor[label]||'var(--blue)';
    return `<section class="section compact-section">${sectionHead('Filtered composition',title,sub,`${items.length} groups`)}<div class="card"><div class="bar-list">${items.slice(0,14).map(([label,count])=>`<div class="bar-row"><div class="bar-label">${esc(label==='met'?'Met goal':label==='missed'?'Missed goal':label==='unavailable'?'Status unavailable':divisionLabel(label))}</div><div class="bar-track"><div class="bar-fill" style="width:${count/max*100}%;background:${color(label)}"></div></div><div class="bar-value">${fmtInt(count)}</div></div>`).join('')}</div>${items.length>14?`<p class="card-sub composition-note">Showing the 14 largest groups; the table and CSV retain all ${items.length}.</p>`:''}</div></section>`;
  }
  const columns=[['metric','Metric'],['divisionKey','Division'],['locationType','Location type'],['location','Location'],['valueDisplay','Value'],['goalDisplay','Local goal'],['goalStatus','Goal status'],['varianceDisplay','Source variance'],['sourceStatus','Source color'],['ytdDisplay','YTD'],['dataAsOf','Data as of']];
  function dataTable(rows){
    if(!rows.length)return '<div class="table-empty">No workbook rows match these filters.</div>';
    const shown=rows.slice(0,500);
    return `<div class="table-scroll"><table class="data-table"><thead><tr>${columns.map(([key,label])=>{const sortKey=key==='valueDisplay'?'valueNumber':key;return `<th data-sort="${sortKey}">${esc(label)}${explorerState.sort===sortKey?(explorerState.direction===1?' ↑':' ↓'):''}</th>`}).join('')}</tr></thead><tbody>${shown.map(r=>`<tr><td class="metric-col">${esc(r.metric)}<small>${esc(r.businessArea)}</small></td><td>${esc(r.divisionKey)}</td><td>${esc(r.locationType)}</td><td class="location-col">${esc(r.location)}</td><td><strong>${esc(r.valueDisplay)}</strong></td><td>${esc(r.goalDisplay)}</td><td>${statusPill(r.goalStatus)}<small>${esc(r.statusBasis)}</small></td><td>${esc(r.varianceDirection)} ${esc(r.varianceDisplay)}</td><td>${esc(r.sourceStatus)}</td><td>${esc(r.ytdDisplay)}</td><td>${esc(r.dataAsOf)}</td></tr>`).join('')}</tbody></table></div>${rows.length>500?`<div class="notice warn"><strong>500-row display limit.</strong><span>All ${fmtInt(rows.length)} filtered records remain available through Export CSV.</span></div>`:''}`;
  }
  function bindExplorer(){
    $('#ex-search').addEventListener('input',e=>{explorerState.search=e.target.value;const position=e.target.selectionStart;renderExplorer();const input=$('#ex-search');input.focus();input.setSelectionRange(position,position)});
    $('#ex-metric').addEventListener('change',e=>{explorerState.metric=e.target.value;const metricRows=baseExplorerRows().filter(r=>r.metric===explorerState.metric&&r.locationType!=='Corporate');explorerState.type=explorerState.metric==='All'?'All':defaultType(explorerState.metric,metricRows);explorerState.division='All';explorerState.date='All';renderExplorer()});
    $('#ex-type').addEventListener('change',e=>{explorerState.type=e.target.value;explorerState.division='All';explorerState.date='All';renderExplorer()});
    $('#ex-division').addEventListener('change',e=>{explorerState.division=e.target.value;explorerState.date='All';renderExplorer()});
    $('#ex-date').addEventListener('change',e=>{explorerState.date=e.target.value;renderExplorer()});
    $('#ex-status').addEventListener('change',e=>{explorerState.status=e.target.value;renderExplorer()});
    $$('[data-view]').forEach(button=>button.addEventListener('click',()=>{explorerState.view=button.dataset.view;safeStorageSet('v30-ex-view',explorerState.view);renderExplorer()}));
    $$('[data-filter-metric]').forEach(card=>card.addEventListener('click',()=>{explorerState.metric=card.dataset.filterMetric;const metricRows=baseExplorerRows().filter(r=>r.metric===explorerState.metric&&r.locationType!=='Corporate');explorerState.type=defaultType(explorerState.metric,metricRows);explorerState.division='All';explorerState.date='All';explorerState.view='table';renderExplorer()}));
    $$('[data-sort]').forEach(th=>th.addEventListener('click',()=>{if(explorerState.sort===th.dataset.sort)explorerState.direction*=-1;else{explorerState.sort=th.dataset.sort;explorerState.direction=1}renderExplorer()}));
    $('#export-csv').addEventListener('click',exportCsv);
  }
  function exportCsv(){
    const rows=filteredExplorerRows();const headers=columns.map(c=>c[1]);
    const csv=[headers,...rows.map(r=>columns.map(c=>r[c[0]]??''))].map(row=>row.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(',')).join('\r\n');
    const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=`vision2030_${explorerState.area.replace(/\s+/g,'_').toLowerCase()}_filtered.csv`;link.click();URL.revokeObjectURL(url);
  }
  function renderExplorer(){
    ensureExplorerState();
    const rows=filteredExplorerRows();const c=counts(rows);
    const analyticalRate=explorerState.area==='Vision 2030'||(explorerState.metric!=='All'&&explorerState.type!=='All');
    let html=hero('Record-level transparency','Explore the <span>workbook</span>','Use Scorecard for a business-friendly overview or Workbook for sortable, filterable source records. Local goals, source variance, YTD, dates, and hierarchy remain visible.');
    html+=`<div class="workbook-tabs" role="tablist">${D.businessAreas.map(area=>`<button type="button" class="${area===explorerState.area?'active':''}" data-area="${esc(area)}">${esc(area)}</button>`).join('')}</div>`;
    html+=`<div class="section-head"><div class="segmented" aria-label="Explorer view"><button class="${explorerState.view==='scorecard'?'active':''}" data-view="scorecard">Scorecard</button><button class="${explorerState.view==='table'?'active':''}" data-view="table">Workbook table</button></div><button class="button primary" id="export-csv">Export filtered CSV</button></div>`;
    html+=explorerControls();
    if(explorerState.area!=='Vision 2030'&&explorerState.type==='All')html+=`<div class="notice warn"><strong>Mixed hierarchy audit view.</strong><span>These rows can include overlapping Corporate, Division, Region, and local scopes. Browse or export them, but select one metric and “Compare as” level before interpreting attainment.</span></div>`;
    else if(explorerState.area!=='Vision 2030')html+=`<div class="notice"><strong>Selected cohort.</strong><span>${fmtInt(rows.length)} ${esc(explorerState.type)} records${explorerState.metric==='All'?' across the available metrics':` for ${esc(explorerState.metric)}`}${explorerState.division==='All'?' across all mapped divisions':` in ${esc(divisionLabel(explorerState.division))}`}. Reporting selection: ${esc(explorerState.date==='All'?dateRange(rows):explorerState.date)}.</span></div>`;
    html+=`<div class="quality-strip"><div><strong>${fmtInt(rows.length)}</strong><span>Filtered rows</span></div><div><strong>${fmtInt(uniq(rows.map(r=>r.scopeId)).length)}</strong><span>Unique scopes</span></div><div><strong>${analyticalRate&&c.eligible?c.rate+'%':'—'}</strong><span>${analyticalRate?'Eligible meeting goal':'Select metric and level'}</span></div><div><strong>${esc(dateRange(rows))}</strong><span>Reporting range</span></div></div>`;
    html+=explorerComposition(rows);
    html+=`<section class="section">${sectionHead(explorerState.view==='scorecard'?'Business view':'Source-aligned view',explorerState.area==='Vision 2030'?'Enterprise summary':`${explorerState.area} records`,explorerState.view==='scorecard'?'Cards summarize only the currently filtered records. Select a metric card to inspect its rows.':'Columns align to workbook meaning while keeping derived goal status separate from source variance.',`${fmtInt(rows.length)} rows`)}${explorerState.view==='scorecard'?overviewCards(rows):dataTable(rows)}</section>`;
    html+=`<div class="notice"><strong>Methodology.</strong><span>${esc(D.methodology.goalStatus)} ${esc(D.methodology.gray)}</span></div>`;
    root.innerHTML=html;
    $$('[data-area]').forEach(button=>button.addEventListener('click',()=>{explorerState.area=button.dataset.area;explorerState.metric='All';explorerState.division='All';explorerState.type='All';explorerState.status='All';explorerState.date='All';safeStorageSet('v30-ex-area',explorerState.area);renderExplorer()}));
    bindExplorer();
  }

  try{
    if(page==='briefing')renderBriefing();
    else if(page==='insights')renderInsights();
    else renderExplorer();
  }catch(error){
    console.error(error);
    root.innerHTML=`${hero('Build error','Unable to render this <span>view</span>','The normalized data loaded, but the page encountered a rendering error.')}<div class="notice warn"><strong>${esc(error.name)}</strong><span>${esc(error.message)}</span></div>`;
  }
})();
