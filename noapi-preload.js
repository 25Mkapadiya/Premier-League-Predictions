(()=>{
'use strict';
// Migration guard: never let the browser consume a legacy pre-v4 prediction
// that may have been influenced by an API-backed availability/lineup layer.
// Once the public-source workflow writes v4 predictions this guard becomes a no-op.
const L=window.LIVE_DATA;
if(!L)return;
let removed=0;
for(const f of L.fixtures||[]){
  const p=f.prediction;
  const legacy=p&&String(p.version||'').split('.')[0]<'4';
  if(legacy&&!f.predictionLocked){
    delete f.prediction;
    delete f.predictionLockedAt;
    f.predictionLocked=false;
    removed++;
  }
  if(f.apiContext)delete f.apiContext;
  if(f.odds&&/Odds API|api/i.test(String(f.odds.source||'')))delete f.odds;
}
L.teamSignals={};
L.meta=L.meta||{};
for(const key of ['market','matchStats','enrichment','freeMarket'])delete L.meta[key];
L.meta.noApi=true;
if(String(L.meta.predictionEngine?.version||'').split('.')[0]<'4'){
  L.meta.source='No-key migration fallback';
  L.meta.message=`${removed} legacy upcoming forecasts suppressed until the public-source v4 snapshot is committed.`;
  L.meta.predictionEngine={version:'4.0',mode:'no API / no secrets',generated:0,legacySuppressed:removed,trainedModelEnabled:false,policy:'Legacy API-influenced forecasts are not rendered. Browser fallback is used until the next public-data refresh.'};
}
})();
