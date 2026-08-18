(()=>{
const M=window.MODEL_DATA,F=window.FIXTURE_DATA;let L=window.LIVE_DATA||{meta:{},fixtures:[],table:[],teamSignals:{}},C=window.PREDICTION_CONTEXT||{fixtures:{}},week=1,status='all',filter='';
const $=(s,r=document)=>r.querySelector(s),$$=(s,r=document)=>[...r.querySelectorAll(s)],teams=Object.keys(M.teams).sort((a,b)=>M.teams[a].display.localeCompare(M.teams[b].display));
const colors={Arsenal:'#c92f3c','Aston Villa':'#7f2345',Bournemouth:'#c62f39',Brentford:'#c9363d',Brighton:'#1f65b5',Chelsea:'#1954a6',Coventry:'#3aa7df','Crystal Palace':'#3059a9',Everton:'#2858a4',Fulham:'#333842',Hull:'#e2a214',Ipswich:'#3065c7',Leeds:'#d1c73f',Liverpool:'#bd3039','Man City':'#5aa9d5','Man United':'#c93137',Newcastle:'#3d424b',"Nott'm Forest":'#c83636',Sunderland:'#c8323a',Tottenham:'#d6dbe5'};
const meta=k=>M.teams[k],esc=s=>String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c])),pct=n=>`${Math.round(n*100)}%`,clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const fact=n=>{let x=1;for(let i=2;i<=n;i++)x*=i;return x},pois=(k,l)=>Math.exp(-l)*Math.pow(l,k)/fact(k);
const baseCache=new Map(),predictionCache=new Map(),recentCache=new Map();

function gridFromLambdas(homeXg,awayXg){
  const p=M.params,grid=[];let total=0;
  for(let x=0;x<=p.maxGoals;x++)for(let y=0;y<=p.maxGoals;y++){
    let q=pois(x,homeXg)*pois(y,awayXg);
    if(x===0&&y===0)q*=1-homeXg*awayXg*p.rho;
    else if(x===0&&y===1)q*=1+homeXg*p.rho;
    else if(x===1&&y===0)q*=1+awayXg*p.rho;
    else if(x===1&&y===1)q*=1-p.rho;
    grid.push({x,y,p:q});total+=q;
  }
  let homeWin=0,draw=0,awayWin=0,over25=0,btts=0;
  grid.forEach(c=>{c.p/=total;if(c.x>c.y)homeWin+=c.p;else if(c.x===c.y)draw+=c.p;else awayWin+=c.p;if(c.x+c.y>=3)over25+=c.p;if(c.x>0&&c.y>0)btts+=c.p});
  const top=[...grid].sort((a,b)=>b.p-a.p)[0];
  return {homeXg,awayXg,homeWin,draw,awayWin,over25,under25:1-over25,btts,noBtts:1-btts,score:[Math.floor(homeXg+.5),Math.floor(awayXg+.5)],topScore:[top.x,top.y],topScoreProb:top.p};
}

function structural(h,a){
  const key=`${h}__${a}`;if(baseCache.has(key))return baseCache.get(key);
  const H=meta(h),A=meta(a),p=M.params,d=(H.elo+p.eloHomeAdvantage-A.elo)/400;
  let hx=p.homeGoalRate*H.homeAtt*A.awayDef,ax=p.awayGoalRate*A.awayAtt*H.homeDef;
  hx*=Math.exp(p.eloGoalWeight*d);ax*=Math.exp(-p.eloGoalWeight*d);
  const out=gridFromLambdas(hx,ax);baseCache.set(key,out);return out;
}

function allLiveFinalsBefore(cutoff){
  const t=cutoff?new Date(cutoff).getTime():Date.now();
  return (L.fixtures||[]).filter(f=>f.status==='final'&&Number.isFinite(f.homeScore)&&Number.isFinite(f.awayScore)&&new Date(f.kickoff).getTime()<t);
}

function recentProfile(team,cutoff){
  const ck=`${team}__${cutoff||'now'}__${L.meta?.lastUpdated||''}`;if(recentCache.has(ck))return recentCache.get(ck);
  const matches=allLiveFinalsBefore(cutoff).filter(f=>f.home===team||f.away===team).sort((a,b)=>new Date(b.kickoff)-new Date(a.kickoff)).slice(0,8);
  let numAtt=0,numDef=0,den=0;
  matches.forEach((f,i)=>{
    const b=structural(f.home,f.away),home=f.home===team,gf=home?f.homeScore:f.awayScore,ga=home?f.awayScore:f.homeScore,exGF=home?b.homeXg:b.awayXg,exGA=home?b.awayXg:b.homeXg,w=Math.pow(.78,i);
    const att=clamp((gf+.55)/(exGF+.55),.45,1.85),def=clamp((ga+.55)/(exGA+.55),.45,1.85);
    numAtt+=Math.log(att)*w;numDef+=Math.log(def)*w;den+=w;
  });
  const prior=4.5,attack=Math.exp(numAtt/(den+prior)),defense=Math.exp(numDef/(den+prior));
  const out={attack,defense,samples:matches.length};recentCache.set(ck,out);return out;
}

function fixtureContext(h,a){
  const x=(C.fixtures||{})[`${h}__${a}`]||{};
  return {homeAttack:clamp(Number(x.homeAttackMultiplier)||1,.7,1.3),homeDefense:clamp(Number(x.homeDefenseMultiplier)||1,.7,1.3),awayAttack:clamp(Number(x.awayAttackMultiplier)||1,.7,1.3),awayDefense:clamp(Number(x.awayDefenseMultiplier)||1,.7,1.3),note:x.note||'',updated:x.updated||null};
}

function fairMarket(odds){
  if(!odds)return null;
  if(odds.fair&&[odds.fair.home,odds.fair.draw,odds.fair.away].every(Number.isFinite))return odds.fair;
  const h=Number(odds.home),d=Number(odds.draw),a=Number(odds.away);if(!(h>1&&d>1&&a>1))return null;
  const q=[1/h,1/d,1/a],s=q.reduce((x,y)=>x+y,0);return {home:q[0]/s,draw:q[1]/s,away:q[2]/s};
}

function logPool(modelP,marketP,w){
  const arr=['home','draw','away'].map(k=>Math.pow(Math.max(modelP[k],1e-8),1-w)*Math.pow(Math.max(marketP[k],1e-8),w));
  const s=arr.reduce((x,y)=>x+y,0);return {home:arr[0]/s,draw:arr[1]/s,away:arr[2]/s};
}

function argmax3(p){return [['H',p.home],['D',p.draw],['A',p.away]].sort((a,b)=>b[1]-a[1])[0][0]}
function signalStrength(p,market){
  const v=[p.homeWin,p.draw,p.awayWin].sort((a,b)=>b-a),agree=!market||argmax3({home:p.homeWin,draw:p.draw,away:p.awayWin})===argmax3(market);
  if(v[0]>=.62&&v[0]-v[1]>=.18&&agree)return'High signal';
  if(v[0]>=.52&&v[0]-v[1]>=.10&&agree)return'Strong lean';
  if(v[0]>=.44)return agree?'Moderate lean':'Mixed signals';
  return'Tight matchup';
}

function predict(h,a,fixture=null){
  const cutoff=fixture?.kickoff||null,market=fairMarket(fixture?.odds),ctx=fixtureContext(h,a),key=`${h}__${a}__${cutoff||'lab'}__${JSON.stringify(market)}__${L.meta?.lastUpdated||''}`;
  if(predictionCache.has(key))return predictionCache.get(key);
  const base=structural(h,a),rh=recentProfile(h,cutoff),ra=recentProfile(a,cutoff);
  let hx=base.homeXg*Math.pow(rh.attack,0.42)*Math.pow(ra.defense,0.34)*ctx.homeAttack*ctx.awayDefense;
  let ax=base.awayXg*Math.pow(ra.attack,0.42)*Math.pow(rh.defense,0.34)*ctx.awayAttack*ctx.homeDefense;
  hx=clamp(hx,.25,4.25);ax=clamp(ax,.2,3.75);
  let dynamic=gridFromLambdas(hx,ax);
  if(market){
    const modelRatio=Math.log((dynamic.homeWin+.02)/(dynamic.awayWin+.02)),marketRatio=Math.log((market.home+.02)/(market.away+.02)),tilt=clamp(marketRatio-modelRatio,-1.2,1.2);
    hx*=Math.exp(.07*tilt);ax*=Math.exp(-.07*tilt);dynamic=gridFromLambdas(hx,ax);
  }
  const marketWeight=market?.home?0.35:0,pooled=market?logPool({home:dynamic.homeWin,draw:dynamic.draw,away:dynamic.awayWin},market,marketWeight):{home:dynamic.homeWin,draw:dynamic.draw,away:dynamic.awayWin};
  const samples=rh.samples+ra.samples,dataQuality=Math.round(clamp(55+Math.min(samples,12)*2+(market?18:0)+(ctx.note?5:0),0,100));
  const modelPick=argmax3({home:dynamic.homeWin,draw:dynamic.draw,away:dynamic.awayWin}),marketPick=market?argmax3(market):null,agreement=market?(modelPick===marketPick?'Model + market agree':'Model + market differ'):(samples>=6?'Structural + recent form':'Structural prior');
  const out={...dynamic,homeWin:pooled.home,draw:pooled.draw,awayWin:pooled.away,components:{structural:{home:base.homeWin,draw:base.draw,away:base.awayWin},dynamic:{home:dynamic.homeWin,draw:dynamic.draw,away:dynamic.awayWin},market,marketWeight,recent:{home:rh,away:ra},context:ctx},dataQuality,agreement};
  out.signal=signalStrength(out,market);predictionCache.set(key,out);return out;
}

function badge(k,large=false){return `<span class="club-badge ${large?'large':''}" style="--club:${colors[k]||'#2c3544'}">${esc(meta(k).abbr)}</span>`}function mini(k){return `<span class="mini-badge" style="--club:${colors[k]||'#2c3544'}">${esc(meta(k).abbr)}</span>`}
function schedule(){const lf=(L.fixtures||[]).filter(f=>f.matchweek&&M.teams[f.home]&&M.teams[f.away]&&f.kickoff);if(lf.length>=300){const g={};lf.forEach(f=>(g[f.matchweek]??=[]).push({home:f.home,away:f.away,kickoff:f.kickoff}));return Object.keys(g).map(Number).sort((a,b)=>a-b).map(n=>({matchweek:n,label:`Matchweek ${n}`,fixtures:g[n].sort((a,b)=>new Date(a.kickoff)-new Date(b.kickoff))}))}return F.matchweeks}
function live(h,a){return(L.fixtures||[]).find(f=>f.home===h&&f.away===a)}
function merge(f,mw){const x=live(f.home,f.away);return{...f,matchweek:mw,status:x?.status||'upcoming',homeScore:Number.isFinite(x?.homeScore)?x.homeScore:null,awayScore:Number.isFinite(x?.awayScore)?x.awayScore:null,minutes:x?.minutes??null,kickoff:x?.kickoff||f.kickoff,odds:x?.odds||null,stats:x?.stats||null}}
const fdate=i=>new Intl.DateTimeFormat(undefined,{weekday:'short',month:'short',day:'numeric'}).format(new Date(i)),ftime=i=>new Intl.DateTimeFormat(undefined,{hour:'numeric',minute:'2-digit'}).format(new Date(i));
function syncDate(v){if(!v)return'Preseason snapshot';const d=new Date(v);return Number.isNaN(d.getTime())?v:new Intl.DateTimeFormat(undefined,{month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}).format(d)}
function lean(h,a,p){return[{key:'H',label:meta(h).display,p:p.homeWin},{key:'D',label:'Draw',p:p.draw},{key:'A',label:meta(a).display,p:p.awayWin}].sort((x,y)=>y.p-x.p)[0]}
function forecast(p){return[{k:'H',p:p.homeWin},{k:'D',p:p.draw},{k:'A',p:p.awayWin}].sort((x,y)=>y.p-x.p)[0].k}
function actual(f){if(f.status!=='final'||f.homeScore==null)return null;return f.homeScore>f.awayScore?'H':f.homeScore<f.awayScore?'A':'D'}
function pill(f){return f.status==='final'?'<span class="status-pill final">Final</span>':f.status==='live'?`<span class="status-pill live">${f.minutes?`${f.minutes}′`:'Live'}</span>`:'<span class="status-pill">Upcoming</span>'}
function prob(label,v,b){return`<div class="outcome-box ${b?'best':''}"><span>${label}</span><strong>${pct(v)}</strong></div>`}
function pickedProb(component,pick){if(!component)return null;return pick==='H'?component.home:pick==='D'?component.draw:component.away}
function modelBreakdown(p){const pick=forecast(p),s=p.components.structural,d=p.components.dynamic,m=p.components.market;return `<div class="model-breakdown"><span class="model-chip"><i>Base</i><b>${pct(pickedProb(s,pick))}</b></span><span class="model-chip"><i>Form</i><b>${pct(pickedProb(d,pick))}</b></span><span class="model-chip ${m?'market-on':'market-off'}"><i>Market</i><b>${m?pct(pickedProb(m,pick)):'not connected'}</b></span><span class="model-chip"><i>Data</i><b>${p.dataQuality}/100</b></span><span class="agreement-chip">${esc(p.agreement)}</span></div>`}

function card(f){const p=predict(f.home,f.away,f),l=lean(f.home,f.away,p),a=actual(f),hit=a?a===forecast(p):null,max=Math.max(p.homeWin,p.draw,p.awayWin),g=p.over25>=.5?`Over 2.5 ${pct(p.over25)}`:`Under 2.5 ${pct(p.under25)}`,b=p.btts>=.5?`BTTS Yes ${pct(p.btts)}`:`BTTS No ${pct(p.noBtts)}`;return`<article class="match-card"><div class="match-main"><div class="match-time"><strong>${fdate(f.kickoff)}</strong>${ftime(f.kickoff)}${pill(f)}</div><div class="match-teams"><div class="match-team-row">${mini(f.home)}<span class="match-team-name">${esc(meta(f.home).display)}</span>${f.homeScore==null?'':`<strong class="actual-score">${f.homeScore}</strong>`}</div><div class="match-team-row">${mini(f.away)}<span class="match-team-name">${esc(meta(f.away).display)}</span>${f.awayScore==null?'':`<strong class="actual-score">${f.awayScore}</strong>`}</div></div><div class="predicted-score"><span>Forecast</span><strong>${p.score[0]} : ${p.score[1]}</strong><small>${p.signal}</small></div><div class="outcome-probs">${prob('1',p.homeWin,p.homeWin===max)}${prob('X',p.draw,p.draw===max)}${prob('2',p.awayWin,p.awayWin===max)}</div></div><div class="market-row"><span class="market-chip accent"><span>1X2</span><strong>${esc(l.label)} ${pct(l.p)}</strong></span><span class="market-chip"><span>Goals</span><strong>${g}</strong></span><span class="market-chip"><span>BTTS</span><strong>${b}</strong></span><span class="market-chip"><span>Correct score</span><strong>${p.topScore[0]}:${p.topScore[1]} · ${pct(p.topScoreProb)}</strong></span>${a?`<span class="market-chip prediction-result ${hit?'hit':'miss'}">${hit?'Outcome pick hit':'Outcome pick missed'}</span>`:''}</div>${modelBreakdown(p)}</article>`}
function passes(f){if(status!=='all'&&f.status!==status)return false;if(filter){const q=filter.toLowerCase();if(!meta(f.home).display.toLowerCase().includes(q)&&!meta(f.away).display.toLowerCase().includes(q))return false}return true}

function featured(){const ws=schedule(),w=ws.find(x=>x.matchweek===week)||ws[0],list=w.fixtures.map(f=>merge(f,w.matchweek)).filter(passes),f=list[0]||merge(w.fixtures[0],w.matchweek),p=predict(f.home,f.away,f),max=Math.max(p.homeWin,p.draw,p.awayWin),score=f.status!=='upcoming'&&f.homeScore!=null?`${f.homeScore}<i>:</i>${f.awayScore}`:`${p.score[0]}<i>:</i>${p.score[1]}`;$('#featured-match').innerHTML=`<div class="featured-kicker"><strong>${f.status==='final'?'Prediction review':'Featured ensemble prediction'}</strong><span>MW ${w.matchweek} · ${fdate(f.kickoff)} · ${ftime(f.kickoff)}</span></div><div class="featured-matchup"><div class="featured-team">${badge(f.home,true)}<div><h2>${esc(meta(f.home).display)}</h2><span>Power ${meta(f.home).power.toFixed(1)}</span></div></div><div class="featured-score"><div class="score">${score}</div><small>${f.status==='upcoming'?'dynamic score forecast':f.status==='final'?'final score':'current score'}</small></div><div class="featured-team away">${badge(f.away,true)}<div><h2>${esc(meta(f.away).display)}</h2><span>Power ${meta(f.away).power.toFixed(1)}</span></div></div></div><div class="featured-probs"><div class="featured-prob ${p.homeWin===max?'best':''}"><span>Home</span><strong>${pct(p.homeWin)}</strong></div><div class="featured-prob ${p.draw===max?'best':''}"><span>Draw</span><strong>${pct(p.draw)}</strong></div><div class="featured-prob ${p.awayWin===max?'best':''}"><span>Away</span><strong>${pct(p.awayWin)}</strong></div></div>${modelBreakdown(p)}`}
function weekTabs(){$('#week-tabs').innerHTML=schedule().map(w=>`<button class="week-tab ${w.matchweek===week?'active':''}" data-week="${w.matchweek}">MW ${w.matchweek}</button>`).join('');$$('.week-tab').forEach(b=>b.onclick=()=>{week=+b.dataset.week;predictions()})}
function predictions(){weekTabs();const ws=schedule(),w=ws.find(x=>x.matchweek===week)||ws[0],fs=w.fixtures.map(f=>merge(f,w.matchweek)).filter(passes);$('#fixture-feed').innerHTML=fs.map(card).join('');$('#fixture-empty').classList.toggle('hidden',!!fs.length);$('#match-count').textContent=`${fs.length} ${fs.length===1?'match':'matches'}`;featured()}
function all(){return schedule().flatMap(w=>w.fixtures.map(f=>merge(f,w.matchweek)))}
function results(){const fs=all().filter(f=>f.status==='final').sort((a,b)=>new Date(b.kickoff)-new Date(a.kickoff));$('#results-feed').innerHTML=fs.map(card).join('');$('#results-empty').classList.toggle('hidden',!!fs.length);let hits=0,exact=0,brier=0;fs.forEach(f=>{const p=predict(f.home,f.away,f),act=actual(f);if(act===forecast(p))hits++;if(p.score[0]===f.homeScore&&p.score[1]===f.awayScore)exact++;const y=[act==='H'?1:0,act==='D'?1:0,act==='A'?1:0],q=[p.homeWin,p.draw,p.awayWin];brier+=q.reduce((s,v,i)=>s+(v-y[i])**2,0)});$('#result-summary').innerHTML=`<div class="summary-tile"><span>Matches reviewed</span><strong>${fs.length}</strong></div><div class="summary-tile"><span>Outcome hit rate</span><strong class="acid">${fs.length?pct(hits/fs.length):'—'}</strong></div><div class="summary-tile"><span>Rounded score hits</span><strong>${fs.length?`${exact}/${fs.length}`:'—'}</strong></div><div class="summary-tile"><span>Live Brier</span><strong>${fs.length?(brier/fs.length).toFixed(3):'—'}</strong></div>`}
function blank(){return teams.map(team=>({team,played:0,w:0,d:0,l:0,gf:0,ga:0,gd:0,pts:0,form:[]}))}function rows(){if(!L.table?.length)return blank().sort((a,b)=>meta(b.team).power-meta(a.team).power);const s=new Set(L.table.map(x=>x.team));return[...L.table,...blank().filter(x=>!s.has(x.team))]}
function form(x){return x?.length?`<div class="form-dots">${x.slice(-5).map(v=>`<span class="form-dot ${v}">${v}</span>`).join('')}</div>`:'<span class="form-empty">—</span>'}
function table(){const r=rows(),played=r.some(x=>x.played>0);$('.table-card').classList.toggle('season-not-started',!played);$('#league-table').innerHTML=r.map((x,i)=>`<div class="league-table-row"><span class="table-num">${i+1}</span><div class="table-club">${mini(x.team)}<strong>${esc(meta(x.team).display)}</strong></div><span class="table-num">${x.played}</span><span class="table-num">${x.w}</span><span class="table-num">${x.d}</span><span class="table-num">${x.l}</span><span class="table-num">${x.gd>0?'+':''}${x.gd}</span><span class="table-num table-points">${x.pts}</span>${form(x.form)}</div>`).join('');$('#quick-table').innerHTML=r.slice(0,5).map((x,i)=>`<div class="quick-row"><span>${i+1}</span><div class="quick-club">${mini(x.team)}<strong>${esc(meta(x.team).display)}</strong></div><strong>${x.pts}</strong></div>`).join('')}
function lab(){const h=$('#home-select').value,a=$('#away-select').value,p=predict(h,a,null),l=lean(h,a,p);$('#lab-result').innerHTML=`<div class="lab-hero"><div class="lab-team">${badge(h,true)}<div><h3>${esc(meta(h).display)}</h3><span>${p.homeXg.toFixed(2)} dynamic expected goals</span></div></div><div class="lab-score"><strong>${p.score[0]} : ${p.score[1]}</strong><span>${p.signal}</span></div><div class="lab-team away">${badge(a,true)}<div><h3>${esc(meta(a).display)}</h3><span>${p.awayXg.toFixed(2)} dynamic expected goals</span></div></div></div><div class="lab-probability"><div><span>Home win</span><strong>${pct(p.homeWin)}</strong></div><div><span>Draw</span><strong>${pct(p.draw)}</strong></div><div><span>Away win</span><strong>${pct(p.awayWin)}</strong></div></div><div class="lab-markets"><div class="lab-market"><span>Model lean</span><strong>${esc(l.label)} · ${pct(l.p)}</strong></div><div class="lab-market"><span>Goals 2.5</span><strong>${p.over25>=.5?'Over':'Under'} · ${pct(Math.max(p.over25,p.under25))}</strong></div><div class="lab-market"><span>Both score</span><strong>${p.btts>=.5?'Yes':'No'} · ${pct(Math.max(p.btts,p.noBtts))}</strong></div><div class="lab-market"><span>Top exact score</span><strong>${p.topScore[0]}:${p.topScore[1]} · ${pct(p.topScoreProb)}</strong></div></div>${modelBreakdown(p)}`}
function insights(){const top=[...teams].sort((a,b)=>meta(b).power-meta(a).power)[0],t=meta(top);$('#signal-team').innerHTML=`${mini(top)}<span>${esc(t.display)}</span>`;$('#signal-power').textContent=t.power.toFixed(1);$('#signal-attack').style.width=`${t.attack}%`;$('#signal-defense').style.width=`${t.defense}%`;const n=all().filter(f=>f.status!=='final'&&new Date(f.kickoff)>=new Date()).sort((a,b)=>new Date(a.kickoff)-new Date(b.kickoff))[0]||all()[0];$('#next-kickoff').innerHTML=n?`<div class="next-teams">${mini(n.home)}<span>${esc(meta(n.home).display)} vs ${esc(meta(n.away).display)}</span></div><div class="next-meta">${fdate(n.kickoff)} · ${ftime(n.kickoff)}</div>`:'<span class="form-empty">No upcoming fixture</span>';const s=syncDate(L.meta?.lastUpdated);$('#last-sync').textContent=s;$('#sync-label').textContent=`Updated ${s}`;const hasMarket=(L.fixtures||[]).some(f=>fairMarket(f.odds));$('#ensemble-market-status').textContent=hasMarket?'Connected':'Optional';$('#ensemble-form-status').textContent=allLiveFinalsBefore().length?'Active':'Waiting for results';$('#ensemble-context-status').textContent=Object.keys(C.fixtures||{}).length?'Configured':'Optional'}
function clubs(){$('#club-shortcuts').innerHTML=teams.map(k=>`<button class="club-shortcut" data-club="${esc(meta(k).display)}">${mini(k)}<span>${esc(meta(k).display)}</span></button>`).join('');$$('.club-shortcut').forEach(b=>b.onclick=()=>{const on=b.classList.contains('active');filter=on?'':b.dataset.club;$('#team-search').value=filter;$$('.club-shortcut').forEach(x=>x.classList.toggle('active',x===b&&!on));predictions()})}
function selects(){const o=teams.map(k=>`<option value="${esc(k)}">${esc(meta(k).display)}</option>`).join('');$('#home-select').innerHTML=o;$('#away-select').innerHTML=o;$('#home-select').value='Arsenal';$('#away-select').value='Man City'}
function render(){predictionCache.clear();recentCache.clear();predictions();results();table();lab();insights()}
function view(n){$$('[data-view-panel]').forEach(x=>x.classList.toggle('active',x.dataset.viewPanel===n));$$('[data-view]').forEach(x=>x.classList.toggle('active',x.dataset.view===n));window.scrollTo({top:0,behavior:'smooth'})}
function toast(m){const e=$('#toast');e.textContent=m;e.classList.add('show');clearTimeout(toast.t);toast.t=setTimeout(()=>e.classList.remove('show'),2500)}
function refresh(){const bs=[$('#refresh-data'),$('#refresh-data-secondary')];bs.forEach(b=>{b.disabled=true;b.classList.add('loading')});document.querySelector('script[data-live-refresh]')?.remove();const s=document.createElement('script');s.dataset.liveRefresh='1';s.src=`data/live.js?v=${Date.now()}`;s.onload=()=>{L=window.LIVE_DATA||L;bs.forEach(b=>{b.disabled=false;b.classList.remove('loading')});render();toast(`Loaded snapshot from ${syncDate(L.meta?.lastUpdated)}`)};s.onerror=()=>{bs.forEach(b=>{b.disabled=false;b.classList.remove('loading')});toast('Could not reload the results snapshot.')};document.body.appendChild(s)}
selects();clubs();$$('[data-view]').forEach(b=>b.onclick=()=>view(b.dataset.view));$$('[data-view-target]').forEach(b=>b.onclick=e=>{e.preventDefault();view(b.dataset.viewTarget)});$$('#prediction-status-tabs [data-filter]').forEach(b=>b.onclick=()=>{status=b.dataset.filter;$$('#prediction-status-tabs [data-filter]').forEach(x=>x.classList.toggle('active',x===b));predictions()});$('#team-search').oninput=e=>{filter=e.target.value.trim();$$('.club-shortcut').forEach(x=>x.classList.remove('active'));predictions()};$('#home-select').onchange=()=>{if($('#home-select').value===$('#away-select').value)$('#away-select').value=teams.find(t=>t!==$('#home-select').value);lab()};$('#away-select').onchange=()=>{if($('#home-select').value===$('#away-select').value)$('#home-select').value=teams.find(t=>t!==$('#away-select').value);lab()};$('#swap-teams').onclick=()=>{const h=$('#home-select').value;$('#home-select').value=$('#away-select').value;$('#away-select').value=h;lab()};$('#refresh-data').onclick=refresh;$('#refresh-data-secondary').onclick=refresh;render();
})();
