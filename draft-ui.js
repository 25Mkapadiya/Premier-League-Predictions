(()=>{
'use strict';
const D=window.DRAFT_DATA,M=window.MODEL_DATA;
if(!D||!M)return;
const $=s=>document.querySelector(s);
const esc=s=>String(s??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const pct=n=>Number.isFinite(n)?`${Math.round(n*100)}%`:'—';
const team=k=>M.teams[k];
const fdate=i=>{if(!i)return'';const d=new Date(i);return Number.isNaN(d.getTime())?'':new Intl.DateTimeFormat(undefined,{weekday:'short',month:'short',day:'numeric',hour:'numeric',minute:'2-digit'}).format(d)};

const STATUS_LABEL={a:'Available',d:'Doubtful',i:'Injured',s:'Suspended',u:'Unavailable',n:'Not in squad'};

function nextFixtureLine(nf){
  if(!nf)return'<span class="draft-next-empty">No upcoming fixture in the current snapshot</span>';
  const opp=team(nf.opponent),oppName=opp?opp.display:esc(nf.opponent),venue=nf.venue==='home'?'H':'A';
  const prob=Number.isFinite(nf.ourWinProbability)?`<strong>${pct(nf.ourWinProbability)} to win</strong>`:'';
  return `<span>Next: vs ${esc(oppName)} (${venue}) · ${esc(fdate(nf.kickoff))}</span>${prob}`;
}

function card(p){
  const t=team(p.team),abbr=t?t.abbr:(p.team||'?').slice(0,3).toUpperCase(),display=t?t.display:esc(p.team||'Unknown club');
  const flagged=p.status&&p.status!=='a';
  const flagText=p.news||STATUS_LABEL[p.status]||'';
  return `<article class="draft-card">
    <div class="draft-card-main">
      <span class="mini-badge draft-badge">${esc(abbr)}</span>
      <div class="draft-info"><strong>${esc(p.fullName||p.name)}</strong><span>${esc(display)}${p.position?` · ${esc(p.position)}`:''}</span></div>
      <div class="draft-price">£${Number(p.price||0).toFixed(1)}m</div>
    </div>
    <div class="draft-stats">
      <div><span>Points</span><strong>${p.totalPoints ?? '—'}</strong></div>
      <div><span>Form</span><strong>${p.form ?? '—'}</strong></div>
      <div><span>Goals</span><strong>${p.goals ?? '—'}</strong></div>
      <div><span>Assists</span><strong>${p.assists ?? '—'}</strong></div>
      <div><span>Minutes</span><strong>${p.minutes ?? '—'}</strong></div>
      <div><span>Selected by</span><strong>${Number.isFinite(p.selectedByPercent)?`${p.selectedByPercent}%`:'—'}</strong></div>
    </div>
    <div class="draft-next-row">${nextFixtureLine(p.nextFixture)}</div>
    ${flagged?`<div class="draft-flag">${esc(flagText||'Not currently available')}</div>`:''}
  </article>`;
}

function render(){
  const picks=D.picks||[],unmatched=D.unmatched||[];
  const feed=$('#draft-feed'),empty=$('#draft-empty'),unmatchedBox=$('#draft-unmatched');
  if(!feed)return;
  feed.innerHTML=picks.map(card).join('');
  const hasAny=(D.picks&&D.picks.length)||(D.unmatched&&D.unmatched.length);
  if(empty)empty.classList.toggle('hidden',!!hasAny);
  if(unmatchedBox){
    if(unmatched.length){
      unmatchedBox.classList.remove('hidden');
      unmatchedBox.innerHTML=`<strong>${unmatched.length} pick${unmatched.length===1?'':'s'} could not be matched.</strong><span>${unmatched.map(u=>`${esc(u.input?.player||'?')}${u.input?.team?` (${esc(u.input.team)})`:''}: ${esc(u.reason||'no match')}`).join(' · ')}</span>`;
    } else {
      unmatchedBox.classList.add('hidden');
    }
  }
}

if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',render);else render();
})();
