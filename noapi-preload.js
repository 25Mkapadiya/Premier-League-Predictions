(()=>{
'use strict';
const L=window.LIVE_DATA,M=window.MODEL_DATA;
if(!L||!M)return;

// Never render a legacy forecast that may have used an authenticated API layer.
let removed=0;
for(const f of L.fixtures||[]){
  const p=f.prediction;
  const legacy=p&&Number(String(p.version||'0').split('.')[0])<4;
  if(legacy&&!f.predictionLocked){delete f.prediction;delete f.predictionLockedAt;f.predictionLocked=false;removed++}
  if(f.apiContext)delete f.apiContext;
  if(f.odds&&/Odds API|api/i.test(String(f.odds.source||'')))delete f.odds;
}
L.teamSignals={};L.meta=L.meta||{};
for(const key of ['market','matchStats','enrichment','freeMarket'])delete L.meta[key];
L.meta.noApi=true;

// Temporary browser fallback for the holdout-passed no-market model. The normal
// production path lives in scripts/prediction_runtime.py. This only runs while
// the committed server snapshot is older than v4.1, so weekly retraining remains
// server-authoritative once the next snapshot lands.
const serverVersion=parseFloat(L.meta.predictionEngine?.version||'0');
if(serverVersion<4.1){
  const NM={
    means:{base_home:.46552329241212775,base_draw:.229909646383665,base_away:.3045670612042073,form_ppm_diff:-.0366441160385508,gdpg_diff:-.040166831362360336,sotdiff_diff:-.1527392731573205,rest_diff:.06447368421052632},
    scales:{base_home:.19343374852807266,base_draw:.04873601842645802,base_away:.17169730364904465,form_ppm_diff:.9573289821336679,gdpg_diff:1.450824317938428,sotdiff_diff:3.297948916813579,rest_diff:1.776675400911062},
    W:[[.15809414315503026,-.06229257767410001,-.16042680887847477,.035437113366722214,-.07373826731286516,.3173835182021987,-.033448636510949335],[-.011777187317383416,.049113522632877424,-.0006726492009536566,-.0041709912969635715,.15901183109519623,-.0851850728851842,.024822525817311078],[-.1463169558376467,.013179055041222635,.1610994580794285,-.03126612206975873,-.08527356378233125,-.23219844531701453,.008626110693638294]],
    b:[.2856695902490349,-.24939744858385904,-.03627214166517526],temp:.9
  };
  const names=['base_home','base_draw','base_away','form_ppm_diff','gdpg_diff','sotdiff_diff','rest_diff'];
  const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
  const softmax=a=>{const m=Math.max(...a),e=a.map(x=>Math.exp(x-m)),s=e.reduce((x,y)=>x+y,0);return e.map(x=>x/s)};
  const facts=[1];for(let i=1;i<=8;i++)facts[i]=facts[i-1]*i;
  const pois=(k,l)=>Math.exp(-l)*Math.pow(l,k)/facts[k];
  function grid(hx,ax){
    const rho=M.params?.rho??-.06,max=M.params?.maxGoals??8;let cells=[],tot=0,H=0,D=0,A=0,O=0,B=0;
    for(let x=0;x<=max;x++)for(let y=0;y<=max;y++){
      let q=pois(x,hx)*pois(y,ax);
      if(x===0&&y===0)q*=1-hx*ax*rho;else if(x===0&&y===1)q*=1+hx*rho;else if(x===1&&y===0)q*=1+ax*rho;else if(x===1&&y===1)q*=1-rho;
      q=Math.max(0,q);cells.push([x,y,q]);tot+=q;
    }
    let top=[0,0,-1];for(const c of cells){const q=c[2]/tot;if(c[0]>c[1])H+=q;else if(c[0]===c[1])D+=q;else A+=q;if(c[0]+c[1]>=3)O+=q;if(c[0]>0&&c[1]>0)B+=q;if(q>top[2])top=[c[0],c[1],q]}
    return {home:H,draw:D,away:A,homeXg:hx,awayXg:ax,over25:O,under25:1-O,btts:B,noBtts:1-B,score:[Math.floor(hx+.5),Math.floor(ax+.5)],topScore:[top[0],top[1]],topScoreProb:top[2]};
  }
  function align(hx,ax,target){
    let best=null,total=hx+ax;
    for(let si=0;si<7;si++)for(let ti=0;ti<13;ti++){
      const scale=.88+si*.04,tilt=-.36+ti*.06,h=clamp(hx*scale*Math.exp(tilt),.18,4.5),a=clamp(ax*scale*Math.exp(-tilt),.15,4),g=grid(h,a);
      const err=(g.home-target.home)**2+(g.draw-target.draw)**2+(g.away-target.away)**2+.008*((h+a)-total)**2;
      if(!best||err<best[0])best=[err,g];
    }
    return best[1];
  }
  function learn(p){
    const base=p.components?.structural||{home:p.homeWin,draw:p.draw,away:p.awayWin},rh=p.components?.recent?.home||{},ra=p.components?.recent?.away||{},rest=p.components?.rest?.difference||0;
    const f={base_home:base.home,base_draw:base.draw,base_away:base.away,form_ppm_diff:clamp((rh.ppm??1.35)-(ra.ppm??1.35),-3,3),gdpg_diff:clamp((rh.gdpg||0)-(ra.gdpg||0),-4,4),sotdiff_diff:clamp((rh.sotDiff||0)-(ra.sotDiff||0),-10,10),rest_diff:clamp(rest,-7,7)};
    const z=names.map(n=>(f[n]-NM.means[n])/NM.scales[n]),logits=NM.b.map((b,c)=>(b+NM.W[c].reduce((s,w,j)=>s+w*z[j],0))/NM.temp),q=softmax(logits);return {p:{home:q[0],draw:q[1],away:q[2]},features:f};
  }
  let calibrated=0;
  for(const f of L.fixtures||[]){
    const p=f.prediction;if(!p||f.predictionLocked||f.odds||Number(String(p.version||'0').split('.')[0])<4)continue;
    const learned=learn(p),g=align(Number(p.homeXg)||1.3,Number(p.awayXg)||1.1,learned.p);
    Object.assign(p,{version:'4.1',engine:'trained no-market ensemble',homeWin:g.home,draw:g.draw,awayWin:g.away,homeXg:g.homeXg,awayXg:g.awayXg,over25:g.over25,under25:g.under25,btts:g.btts,noBtts:g.noBtts,score:g.score,topScore:g.topScore,topScoreProb:g.topScoreProb,validatedFeatures:learned.features,learnedEligibility:'validated holdout model active',dataQuality:Math.min(100,(p.dataQuality||45)+8)});
    p.components=p.components||{};p.components.learned=learned.p;calibrated++;
  }
  L.meta.source='Public no-key sources';L.meta.message=`${calibrated} upcoming forecasts calibrated with the holdout-passed no-market model.`;
  L.meta.predictionEngine={...(L.meta.predictionEngine||{}),version:'4.1',mode:'no API / no secrets',noMarketModelEnabled:true,noMarketModelFixtures:calibrated,browserFallback:true,policy:'The browser fallback mirrors the validated no-market model only until the server v4.1 snapshot is committed. Forecasts still freeze at kickoff.'};
}

if(Number(String(L.meta.predictionEngine?.version||'0').split('.')[0])<4){
  L.meta.source='No-key migration fallback';
  L.meta.message=`${removed} legacy upcoming forecasts suppressed.`;
}
})();
