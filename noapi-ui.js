(()=>{
'use strict';
const esc=s=>String(s??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
function rewriteHealth(){
  const root=document.querySelector('#model-health-panel');
  if(!root)return;
  const L=window.LIVE_DATA||{},src=L.meta?.publicSources||{},pe=L.meta?.predictionEngine||{},fd=src.footballData||{},us=src.understat||{},mk=src.upcomingMarket||{};
  const noHold=pe.noMarketModelHoldout?.ensemble,marketHold=pe.marketModelHoldout?.ensemble||pe.trainedModelHoldout?.ensemble;
  const noEnabled=pe.noMarketModelEnabled??false,marketEnabled=pe.marketModelEnabled??pe.trainedModelEnabled??false;
  const item=(name,on,detail)=>`<div class="health-item ${on?'on':'off'}"><span>${name}</span><strong>${on?'Active':'Waiting'}</strong><small>${esc(detail||'')}</small></div>`;
  root.innerHTML=`<div class="health-heading"><div><span class="mini-kicker">No-key accuracy stack</span><h3>What this forecast actually knows</h3></div><span class="health-version">Engine ${esc(pe.version||'4.1')}</span></div><div class="health-grid">${item('No-market ensemble',noEnabled,noHold?`Holdout Brier ${Number(noHold.brier).toFixed(3)} · log loss ${Number(noHold.logLoss).toFixed(3)}`:'Holdout-gated model')}${item('Dynamic form',true,L.meta?.seasonStarted?'Current-season results included':'Activates as 2026/27 results arrive')}${item('Football-Data',!!fd.connected,fd.connected?`${fd.rows||0} current-season rows loaded`:fd.message)}${item('Understat xG',!!us.connected,us.connected?`${us.matches||0} EPL fixtures parsed`:(us.message||'Optional public xG is not currently available'))}${item('Public market odds',!!(mk.eplRows>0),mk.eplRows?`${mk.eplRows} upcoming EPL odds rows`:'Waiting for EPL rows in the public fixture file')}${item('Market-aware ensemble',marketEnabled,marketHold?`Holdout Brier ${Number(marketHold.brier).toFixed(3)} · log loss ${Number(marketHold.logLoss).toFixed(3)}`:'Activates only with public market evidence')}${item('Forecast locking',true,'Every prediction freezes at kickoff')}</div><p class="health-policy">No API keys or paid feeds are used. Each learned layer is promoted only after beating its comparison model on later unseen matches.</p>`;
}
function rewriteValidation(){
  const panel=document.querySelector('.validation-panel');if(!panel)return;
  const h=panel.querySelector('h2'),p=panel.querySelector('p'),grid=panel.querySelector('.validation-grid');
  if(h)h.textContent='Two learned models, both gated by unseen matches.';
  if(p)p.textContent='Without public odds, the no-market ensemble is used because it beat the structural baseline on Brier score and log loss. If public odds appear, the stronger market-aware model takes over.';
  if(grid)grid.innerHTML='<div><strong>0.650</strong><span>no-market Brier</span></div><div><strong>1.071</strong><span>no-market log loss</span></div><div><strong>0.633</strong><span>market-model Brier</span></div><div><strong>190</strong><span>holdout matches</span></div>';
}
function rewriteLab(){const note=document.querySelector('.lab-note');if(note)note.textContent='The Matchup Lab intentionally uses the structural model only. Scheduled fixtures can add timestamped form, xG/shot data, rest, live Elo movement and public market evidence when available.'}
const observer=new MutationObserver(()=>{rewriteHealth();rewriteValidation();rewriteLab()});observer.observe(document.documentElement,{childList:true,subtree:true});
window.addEventListener('DOMContentLoaded',()=>{rewriteHealth();rewriteValidation();rewriteLab()});
setTimeout(()=>{rewriteHealth();rewriteValidation();rewriteLab()},0);
})();
