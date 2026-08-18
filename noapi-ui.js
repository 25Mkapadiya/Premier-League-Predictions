(()=>{
'use strict';
const esc=s=>String(s??'').replace(/[&<>\"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','\"':'&quot;',"'":'&#39;'}[c]));
function rewriteHealth(){
  const root=document.querySelector('#model-health-panel');
  if(!root)return;
  const L=window.LIVE_DATA||{},src=L.meta?.publicSources||{},pe=L.meta?.predictionEngine||{},fd=src.footballData||{},us=src.understat||{},mk=src.upcomingMarket||{},hold=pe.trainedModelHoldout?.ensemble;
  const item=(name,on,detail)=>`<div class="health-item ${on?'on':'off'}"><span>${name}</span><strong>${on?'Active':'Waiting'}</strong><small>${esc(detail||'')}</small></div>`;
  root.innerHTML=`<div class="health-heading"><div><span class="mini-kicker">No-key accuracy stack</span><h3>What this forecast actually knows</h3></div><span class="health-version">Engine ${esc(pe.version||'4.0')}</span></div><div class="health-grid">${item('Dynamic form',true,L.meta?.seasonStarted?'Current-season results included':'Activates as 2026/27 results arrive')}${item('Football-Data',!!fd.connected,fd.connected?`${fd.rows||0} current-season rows loaded`:fd.message)}${item('Understat xG',!!us.connected,us.connected?`${us.matches||0} EPL fixtures parsed`:us.message)}${item('Public market odds',!!(mk.eplRows>0),mk.eplRows?`${mk.eplRows} upcoming EPL odds rows`:'Waiting for EPL rows in the public fixture file')}${item('Learned ensemble',!!pe.trainedModelEnabled,hold?`Holdout Brier ${Number(hold.brier).toFixed(3)} · log loss ${Number(hold.logLoss).toFixed(3)}`:'Time-ordered model is available when public market evidence exists')}${item('Forecast locking',true,'Every prediction freezes at kickoff')}</div><p class="health-policy">No API keys or paid feeds are used. Missing public data falls back to the strongest timestamp-safe statistical layer instead of being guessed.</p>`;
}
function rewriteLab(){const note=document.querySelector('.lab-note');if(note)note.textContent='The Matchup Lab intentionally uses the structural model only. Scheduled fixtures can add timestamped form, xG/shot data, rest, live Elo movement and public market evidence when available.'}
const observer=new MutationObserver(()=>{rewriteHealth();rewriteLab()});observer.observe(document.documentElement,{childList:true,subtree:true});
window.addEventListener('DOMContentLoaded',()=>{rewriteHealth();rewriteLab()});
setTimeout(()=>{rewriteHealth();rewriteLab()},0);
})();
