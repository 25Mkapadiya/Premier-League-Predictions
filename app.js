(() => {
  const model = window.MODEL_DATA;
  const fixtureData = window.FIXTURE_DATA;
  const teams = Object.keys(model.teams).sort((a,b) => model.teams[a].display.localeCompare(model.teams[b].display));
  let activeWeek = 1;

  const $ = (sel, root=document) => root.querySelector(sel);
  const $$ = (sel, root=document) => [...root.querySelectorAll(sel)];
  const pct = n => `${Math.round(n * 100)}%`;
  const teamMeta = key => model.teams[key];
  const predictionCache = new Map();
  const factorial = n => { let x = 1; for (let i = 2; i <= n; i++) x *= i; return x; };
  const poisson = (k, lambda) => Math.exp(-lambda) * Math.pow(lambda, k) / factorial(k);

  function prediction(home, away) {
    const cacheKey = `${home}__${away}`;
    if (predictionCache.has(cacheKey)) return predictionCache.get(cacheKey);

    const h = teamMeta(home);
    const a = teamMeta(away);
    const params = model.params;
    const eloDelta = (h.elo + params.eloHomeAdvantage - a.elo) / 400;
    let homeXg = params.homeGoalRate * h.homeAtt * a.awayDef;
    let awayXg = params.awayGoalRate * a.awayAtt * h.homeDef;
    homeXg *= Math.exp(params.eloGoalWeight * eloDelta);
    awayXg *= Math.exp(-params.eloGoalWeight * eloDelta);

    const grid = [];
    let total = 0;
    for (let x = 0; x <= params.maxGoals; x++) {
      for (let y = 0; y <= params.maxGoals; y++) {
        let p = poisson(x, homeXg) * poisson(y, awayXg);
        if (x === 0 && y === 0) p *= 1 - homeXg * awayXg * params.rho;
        else if (x === 0 && y === 1) p *= 1 + homeXg * params.rho;
        else if (x === 1 && y === 0) p *= 1 + awayXg * params.rho;
        else if (x === 1 && y === 1) p *= 1 - params.rho;
        grid.push({x, y, p});
        total += p;
      }
    }

    let homeWin = 0, draw = 0, awayWin = 0;
    const topScore = grid.reduce((best, cell) => cell.p > best.p ? cell : best, grid[0]);
    for (const cell of grid) {
      cell.p /= total;
      if (cell.x > cell.y) homeWin += cell.p;
      else if (cell.x === cell.y) draw += cell.p;
      else awayWin += cell.p;
    }

    const result = {
      homeXg, awayXg, homeWin, draw, awayWin,
      score: [Math.floor(homeXg + 0.5), Math.floor(awayXg + 0.5)],
      topScore: [topScore.x, topScore.y]
    };
    predictionCache.set(cacheKey, result);
    return result;
  }

  function teamBadge(key) {
    const t = teamMeta(key);
    return `<span class="badge" aria-hidden="true">${t.abbr}</span>`;
  }

  function teamBlock(key, side='home') {
    const t = teamMeta(key);
    return `<div class="team ${side === 'away' ? 'away' : ''}">
      ${teamBadge(key)}
      <div><div class="team-name">${t.display}</div><small>Power ${t.power.toFixed(1)}</small></div>
    </div>`;
  }

  function getLean(home, away, p) {
    const values = [p.homeWin, p.draw, p.awayWin];
    const max = Math.max(...values);
    if (max === p.draw) return 'Draw lean';
    return max === p.homeWin ? `${teamMeta(home).display} lean` : `${teamMeta(away).display} lean`;
  }

  function formatKickoff(iso) {
    const date = new Date(iso);
    const datePart = new Intl.DateTimeFormat(undefined, {weekday:'short', month:'short', day:'numeric'}).format(date);
    const timePart = new Intl.DateTimeFormat(undefined, {hour:'numeric', minute:'2-digit'}).format(date);
    return `${datePart} · ${timePart}`;
  }

  function probabilityBlocks(home, away, p) {
    const vals = [
      {label: teamMeta(home).abbr, value:p.homeWin},
      {label:'DRAW', value:p.draw},
      {label:teamMeta(away).abbr, value:p.awayWin}
    ];
    const max = Math.max(...vals.map(v => v.value));
    return `<div class="prob-bars">${vals.map(v => `<div class="prob ${v.value === max ? 'favorite' : ''}">
      <div class="prob-top"><span>${v.label}</span><strong>${pct(v.value)}</strong></div>
      <b><i style="--w:${pct(v.value)}"></i></b>
    </div>`).join('')}</div>`;
  }

  function renderWeekTabs() {
    const root = $('#week-tabs');
    root.innerHTML = fixtureData.matchweeks.map(w => `<button class="week-tab ${w.matchweek===activeWeek?'active':''}" data-week="${w.matchweek}">MW ${w.matchweek}</button>`).join('');
    $$('.week-tab', root).forEach(btn => btn.addEventListener('click', () => {
      activeWeek = Number(btn.dataset.week);
      renderWeekTabs();
      renderFixtures();
    }));
  }

  function renderFixtures() {
    const week = fixtureData.matchweeks.find(w => w.matchweek === activeWeek);
    $('#fixture-grid').innerHTML = week.fixtures.map((f, idx) => {
      const p = prediction(f.home, f.away);
      return `<article class="fixture-card">
        <div class="fixture-meta"><span>${formatKickoff(f.kickoff)}</span><span class="fixture-lean">${getLean(f.home,f.away,p)}</span></div>
        <div class="teams-row">
          ${teamBlock(f.home,'home')}
          <div class="score-prediction" aria-label="rounded expected score ${p.score[0]} to ${p.score[1]}"><strong>${p.score[0]}</strong><span>:</span><strong>${p.score[1]}</strong></div>
          ${teamBlock(f.away,'away')}
        </div>
        ${probabilityBlocks(f.home,f.away,p)}
      </article>`;
    }).join('');
  }

  function renderSelects() {
    const options = teams.map(k => `<option value="${k}">${teamMeta(k).display}</option>`).join('');
    $('#home-select').innerHTML = options;
    $('#away-select').innerHTML = options;
    $('#home-select').value = 'Arsenal';
    $('#away-select').value = 'Man City';
    $('#home-select').addEventListener('change', ensureDistinctAndRender);
    $('#away-select').addEventListener('change', ensureDistinctAndRender);
    $('#swap-teams').addEventListener('click', () => {
      const h = $('#home-select').value;
      $('#home-select').value = $('#away-select').value;
      $('#away-select').value = h;
      renderLab();
    });
  }

  function ensureDistinctAndRender(event) {
    const h = $('#home-select').value;
    const a = $('#away-select').value;
    if (h === a) {
      const other = teams.find(t => t !== h);
      if (event.target.id === 'home-select') $('#away-select').value = other;
      else $('#home-select').value = other;
    }
    renderLab();
  }

  function renderLab() {
    const home = $('#home-select').value;
    const away = $('#away-select').value;
    const p = prediction(home, away);
    const max = Math.max(p.homeWin,p.draw,p.awayWin);
    const confidence = max >= .60 ? 'Strong lean' : max >= .48 ? 'Moderate lean' : 'Tight matchup';
    $('#lab-result').innerHTML = `
      <div class="fixture-meta"><span>${confidence}</span><span class="fixture-lean">${getLean(home,away,p)}</span></div>
      <div class="teams-row">
        ${teamBlock(home,'home')}
        <div class="score-prediction"><strong>${p.score[0]}</strong><span>:</span><strong>${p.score[1]}</strong></div>
        ${teamBlock(away,'away')}
      </div>
      <div class="lab-xg"><span>${teamMeta(home).abbr} xG <strong>${p.homeXg.toFixed(2)}</strong></span><span>${teamMeta(away).abbr} xG <strong>${p.awayXg.toFixed(2)}</strong></span></div>
      ${probabilityBlocks(home,away,p)}
    `;
  }

  function renderRankings() {
    const ranked = [...teams].sort((a,b) => model.teams[b].power - model.teams[a].power);
    $('#ranking-list').innerHTML = ranked.map((key, i) => {
      const t = teamMeta(key);
      return `<div class="ranking-row">
        <div class="rank-team"><span class="rank-number">${i+1}</span>${teamBadge(key)}<strong>${t.display}${t.promoted?'<span class="promo-pill">PROMOTED</span>':''}</strong></div>
        <div class="power-score">${t.power.toFixed(1)}</div>
        <div class="attack-cell"><div class="stat-bar"><i style="--w:${t.attack}%"></i></div></div>
        <div class="defense-cell"><div class="stat-bar def"><i style="--w:${t.defense}%"></i></div></div>
        <div class="finish">${t.sourceFinish}</div>
      </div>`;
    }).join('');
  }

  function setView(name) {
    $$('[data-view-panel]').forEach(el => el.classList.toggle('active', el.dataset.viewPanel === name));
    $$('[data-view]').forEach(el => el.classList.toggle('active', el.dataset.view === name));
    window.scrollTo({top: 80, behavior:'smooth'});
  }

  function bindNavigation() {
    $$('[data-view]').forEach(btn => btn.addEventListener('click', () => setView(btn.dataset.view)));
    $$('[data-view-target]').forEach(btn => btn.addEventListener('click', () => setView(btn.dataset.viewTarget)));
    $$('[data-jump]').forEach(btn => btn.addEventListener('click', () => document.getElementById(btn.dataset.jump).scrollIntoView({behavior:'smooth'})));
  }

  function renderHero() {
    const top = Object.keys(model.teams).sort((a,b) => model.teams[b].power - model.teams[a].power)[0];
    const t = teamMeta(top);
    $('#hero-signal').textContent = t.display;
    $('#hero-score').textContent = t.power.toFixed(1);
    $('#hero-attack').style.setProperty('--bar', `${t.attack}%`);
    $('#hero-defense').style.setProperty('--bar', `${t.defense}%`);
  }

  renderHero();
  renderWeekTabs();
  renderFixtures();
  renderSelects();
  renderLab();
  renderRankings();
  bindNavigation();
})();
