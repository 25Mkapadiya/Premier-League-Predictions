#!/usr/bin/env python3
"""Train a leakage-resistant EPL 1X2 ensemble from Football-Data historical CSVs."""
from __future__ import annotations
import csv,io,json,math,urllib.request
from collections import defaultdict,deque
from dataclasses import dataclass,field
from datetime import datetime,timezone
from prediction_core import ROOT,brier,clamp,log_loss,score_grid,softmax
OUTPUT=ROOT/'data'/'trained_model.json';SEASONS=[('2223','2022/23'),('2324','2023/24'),('2425','2024/25'),('2526','2025/26')];FEATURES=['base_home','base_draw','base_away','market_home','market_draw','market_away','market_available','form_ppm_diff','gdpg_diff','sotdiff_diff','rest_diff','availability_diff']
def download(url):
    req=urllib.request.Request(url,headers={'User-Agent':'PL-Forecast-Trainer/3.0'})
    with urllib.request.urlopen(req,timeout=45) as r:return r.read().decode('utf-8-sig')
def parse_date(v):
    for fmt in ('%d/%m/%Y','%d/%m/%y'):
        try:return datetime.strptime(v,fmt).replace(tzinfo=timezone.utc)
        except ValueError:pass
    raise ValueError(v)
def num(row,k,default=0):
    try:return float(row.get(k,'') or default)
    except ValueError:return default
def market(row):
    for cols in (('AvgH','AvgD','AvgA'),('B365H','B365D','B365A'),('PSH','PSD','PSA')):
        try:h,d,a=[float(row[c]) for c in cols]
        except (KeyError,ValueError,TypeError):continue
        if h>1 and d>1 and a>1:
            raw=[1/h,1/d,1/a];s=sum(raw);return {'home':raw[0]/s,'draw':raw[1]/s,'away':raw[2]/s}
    return None
@dataclass
class VenueState:matches:int=0;gf:float=0;ga:float=0
@dataclass
class TeamState:
    elo:float=1500;home:VenueState=field(default_factory=VenueState);away:VenueState=field(default_factory=VenueState);recent:deque=field(default_factory=lambda:deque(maxlen=8));last_date:datetime|None=None
class RollingState:
    def __init__(self):self.teams=defaultdict(TeamState);self.hg=0.;self.ag=0.;self.matches=0
    @property
    def hr(self):return (self.hg+1.48*80)/(self.matches+80)
    @property
    def ar(self):return (self.ag+1.18*80)/(self.matches+80)
    def structural(self,home,away):
        h,a=self.teams[home],self.teams[away];hr,ar=self.hr,self.ar;prior=7.;hatt=((h.home.gf+prior*hr)/(h.home.matches+prior))/hr;hdef=((h.home.ga+prior*ar)/(h.home.matches+prior))/ar;aatt=((a.away.gf+prior*ar)/(a.away.matches+prior))/ar;adef=((a.away.ga+prior*hr)/(a.away.matches+prior))/hr;d=(h.elo+65-a.elo)/400;hx=hr*hatt*adef*math.exp(.1*d);ax=ar*aatt*hdef*math.exp(-.1*d);return score_grid(clamp(hx,.2,4.2),clamp(ax,.18,3.8),-.06,8)
    def recent_profile(self,team):
        rows=list(self.teams[team].recent)
        if not rows:return {'ppm':1.35,'gdpg':0,'sotDiff':0}
        ws=pts=gd=sot=0
        for i,r in enumerate(reversed(rows)):
            w=.78**i;pts+=r['pts']*w;gd+=r['gd']*w;sot+=r['sot']*w;ws+=w
        return {'ppm':pts/ws,'gdpg':gd/ws,'sotDiff':sot/ws}
    def rest_diff(self,h,a,dt):
        hd=self.teams[h].last_date;ad=self.teams[a].last_date
        if not hd or not ad:return 0
        return clamp((dt-hd).total_seconds()/86400-(dt-ad).total_seconds()/86400,-7,7)
    def update(self,row):
        h,a=row['HomeTeam'],row['AwayTeam'];hs,as_=int(float(row['FTHG'])),int(float(row['FTAG']));H,A=self.teams[h],self.teams[a];exp=1/(1+10**((A.elo-(H.elo+65))/400));actual=1 if hs>as_ else .5 if hs==as_ else 0;k=22*(1+math.log1p(max(1,abs(hs-as_)))/3);delta=k*(actual-exp);H.elo+=delta;A.elo-=delta;H.home.matches+=1;H.home.gf+=hs;H.home.ga+=as_;A.away.matches+=1;A.away.gf+=as_;A.away.ga+=hs;hst,ast=num(row,'HST'),num(row,'AST');H.recent.append({'pts':3 if hs>as_ else 1 if hs==as_ else 0,'gd':hs-as_,'sot':hst-ast});A.recent.append({'pts':3 if as_>hs else 1 if hs==as_ else 0,'gd':as_-hs,'sot':ast-hst});dt=parse_date(row['Date']);H.last_date=dt;A.last_date=dt;self.hg+=hs;self.ag+=as_;self.matches+=1
def row_features(state,row):
    h,a=row['HomeTeam'],row['AwayTeam'];dt=parse_date(row['Date']);base=state.structural(h,a);m=market(row);hp,ap=state.recent_profile(h),state.recent_profile(a);mm=m or {'home':base['home'],'draw':base['draw'],'away':base['away']};return {'base_home':base['home'],'base_draw':base['draw'],'base_away':base['away'],'market_home':mm['home'],'market_draw':mm['draw'],'market_away':mm['away'],'market_available':1 if m else 0,'form_ppm_diff':clamp(hp['ppm']-ap['ppm'],-3,3),'gdpg_diff':clamp(hp['gdpg']-ap['gdpg'],-4,4),'sotdiff_diff':clamp(hp['sotDiff']-ap['sotDiff'],-10,10),'rest_diff':state.rest_diff(h,a,dt),'availability_diff':0},base
def label(row):return 0 if row.get('FTR')=='H' else 1 if row.get('FTR')=='D' else 2
def load_rows():
    out=[]
    for code,name in SEASONS:
        text=download(f'https://www.football-data.co.uk/mmz4281/{code}/E0.csv');rows=[]
        for row in csv.DictReader(io.StringIO(text)):
            if row.get('FTHG') in ('',None) or row.get('FTAG') in ('',None) or row.get('FTR') not in ('H','D','A'):continue
            try:dt=parse_date(row['Date'])
            except Exception:continue
            row['_season']=name;row['_date']=dt;rows.append(row)
        rows.sort(key=lambda r:r['_date']);out.extend(rows)
    return out
def build_dataset(rows):
    state=RollingState();data=[]
    for row in rows:
        feat,base=row_features(state,row)
        if row['_season']!='2022/23':data.append({'season':row['_season'],'date':row['_date'],'x':feat,'y':label(row),'base':{k:base[k] for k in ('home','draw','away')}})
        state.update(row)
    return data
def standardize(train):
    means={};scales={}
    for n in FEATURES:
        vals=[r['x'][n] for r in train];m=sum(vals)/len(vals);v=sum((x-m)**2 for x in vals)/max(len(vals)-1,1);means[n]=m;scales[n]=max(math.sqrt(v),1e-6)
    return means,scales
def zrow(r,m,s):return [(r['x'][n]-m[n])/s[n] for n in FEATURES]
def fit(train,means,scales,epochs=2200,lr=.075,l2=.025):
    d=len(FEATURES);W=[[0.]*d for _ in range(3)];b=[0.]*3;zs=[zrow(r,means,scales) for r in train];ys=[r['y'] for r in train];N=len(train)
    for epoch in range(epochs):
        gW=[[0.]*d for _ in range(3)];gb=[0.]*3
        for z,y in zip(zs,ys):
            p=softmax([b[c]+sum(W[c][j]*z[j] for j in range(d)) for c in range(3)])
            for c in range(3):
                e=p[c]-(1 if y==c else 0);gb[c]+=e
                for j in range(d):gW[c][j]+=e*z[j]
        rate=lr/(1+epoch/900)
        for c in range(3):
            b[c]-=rate*gb[c]/N
            for j in range(d):W[c][j]-=rate*(gW[c][j]/N+l2*W[c][j])
    return W,b
def probs(r,W,b,m,s,temp=1):
    z=zrow(r,m,s);p=softmax([(b[c]+sum(W[c][j]*z[j] for j in range(len(z))))/temp for c in range(3)]);return {'home':p[0],'draw':p[1],'away':p[2]}
def metrics(rows,fn):
    if not rows:return {'matches':0}
    acc=bs=ll=0
    for r in rows:
        p=fn(r);pred=max(('home','draw','away'),key=lambda k:p[k]);actual=('home','draw','away')[r['y']];acc+=pred==actual;code=('H','D','A')[r['y']];bs+=brier(p,code);ll+=log_loss(p,code)
    n=len(rows);return {'matches':n,'accuracy':acc/n,'brier':bs/n,'logLoss':ll/n}
def temperature(rows,W,b,m,s):
    best=(1e9,1)
    for i in range(61):
        t=.55+i*.02;v=metrics(rows,lambda r:probs(r,W,b,m,s,t))['logLoss']
        if v<best[0]:best=(v,t)
    return best[1]
def main():
    data=build_dataset(load_rows());train=[r for r in data if r['season'] in ('2023/24','2024/25')];s25=[r for r in data if r['season']=='2025/26'];split=len(s25)//2;cal,hold=s25[:split],s25[split:]
    if len(train)<500 or len(hold)<100:raise RuntimeError(f'Insufficient data train={len(train)} holdout={len(hold)}')
    means,scales=standardize(train);W,b=fit(train,means,scales);temp=temperature(cal,W,b,means,scales);ensemble=metrics(hold,lambda r:probs(r,W,b,means,scales,temp));struct=metrics(hold,lambda r:r['base']);market_rows=[r for r in hold if r['x']['market_available']>0];market_m=metrics(market_rows,lambda r:{'home':r['x']['market_home'],'draw':r['x']['market_draw'],'away':r['x']['market_away']});payload={'enabled':True,'version':'3.0','trainedAt':datetime.now(timezone.utc).isoformat().replace('+00:00','Z'),'trainingSeasons':['2023/24','2024/25'],'calibrationWindow':'first half 2025/26','holdoutWindow':'second half 2025/26','trainingSamples':len(train),'calibrationSamples':len(cal),'features':FEATURES,'means':means,'scales':scales,'coefficients':W,'intercepts':b,'temperature':temp,'holdout':{'ensemble':ensemble,'structural':struct,'market':market_m},'notes':'Holdout matches are not used for coefficient fitting or temperature selection.'};OUTPUT.write_text(json.dumps(payload,indent=2),encoding='utf-8');print(json.dumps(payload['holdout'],indent=2));return 0
if __name__=='__main__':raise SystemExit(main())
