/* Atlas Loan Lab UI, served by site/serve.py.
   The host (window.AtlasHost) supplies: post(msg), onMessage(cb), caps, load(), save(obj). */
(function () {
  const host = window.AtlasHost;
  const app = document.getElementById('app');
  let model = null, progress = null, running = [], toast = null, quiz = {}, outputOpen = {};
  const saved = host.load() || {};
  quiz = saved.quiz || {};

  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const attr = esc;
  const label = { done: 'Done', progress: 'In progress', todo: 'Not started' };
  const icon = { done: '✓', progress: '◐', todo: '○' };

  const labInfo = (n) => (progress && progress.labs && progress.labs[n]) || { passed: 0, total: 0, status: 'todo', lessons: {} };
  const lessonInfo = (n, id) => labInfo(n).lessons[id] || { passed: 0, total: 0, failed: 0, status: 'todo', failures: [], unlocked: true };
  const totals = () => (progress && progress.total) || { passed: 0, total: model.labs.reduce((a, l) => a + l.tests, 0) };
  const findLab = (n) => model.labs.find((l) => l.n === Number(n));
  const pct = (a, b) => (b ? Math.round((a / b) * 100) : 0);

  function route() {
    const parts = (location.hash || '#/').slice(2).split('/').filter(Boolean).map(decodeURIComponent);
    return parts;
  }
  function go(path) { location.hash = '#/' + path; }

  const logo = '<svg width="26" height="26" viewBox="0 0 28 28" aria-hidden="true"><rect x="1" y="1" width="26" height="26" rx="7" fill="var(--accent)"/><path d="M8 20 L14 7 L20 20 M10.5 15.5 H17.5" fill="none" stroke="var(--accent-fg)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>';

  function topbar(crumbs) {
    const t = totals();
    const busy = running.length > 0;
    return `<header class="top"><a class="brand" href="#/">${logo}<span>Atlas Loan Lab</span></a>
      <div class="crumbs">${crumbs || ''}</div>
      <div class="live" role="status"><span class="dot ${busy ? 'run' : ''}"></span>${busy ? 'Running tests…' : `${t.passed} / ${t.total} tests green`}
      <button class="btn" data-act="run" data-scope="all" ${busy ? 'disabled' : ''}>Re-check all</button></div></header>`;
  }

  function ring(p, size) {
    const r = 62, c = 2 * Math.PI * r, d = (c * p) / 100;
    return `<div class="ring" style="width:${size}px;height:${size}px"><svg width="${size}" height="${size}" viewBox="0 0 148 148" role="img" aria-label="${p}% of tests passing">
      <circle cx="74" cy="74" r="${r}" fill="none" stroke="var(--border)" stroke-width="12"/>
      <circle cx="74" cy="74" r="${r}" fill="none" stroke="var(--accent)" stroke-width="12" stroke-linecap="round" stroke-dasharray="${d.toFixed(1)} ${c.toFixed(1)}" transform="rotate(-90 74 74)" style="transition:stroke-dasharray .6s"/></svg>
      <div class="num">${p}%<small>of tests green</small></div></div>`;
  }

  function home() {
    const t = totals();
    const doneLabs = model.labs.filter((l) => labInfo(l.n).status === 'done').length;
    const nxt = (progress && progress.next) || {};
    const nl = nxt.lab ? findLab(nxt.lab) : null;
    const nlesson = nl ? nl.lessons.find((x) => x.id === nxt.lesson) : null;
    const everything = progress && t.total && t.passed === t.total;
    const hours = model.labs.filter((l) => labInfo(l.n).status !== 'done').reduce((a, l) => a + (parseFloat(l.time) || 0), 0);
    return topbar() + `<main class="page">
      <section class="hero"><div class="copy"><div class="eyebrow">Companion labs · Claude Certified Architect Professional</div>
        <h1>Build the Atlas case-file assistant, one passing test at a time.</h1>
        <p>${model.labs.length} labs take a vague lending mandate to a governed, evaluated, documented system. Save a file and this page updates by itself.</p></div>
        <div class="card ringcard">${ring(pct(t.passed, t.total), 132)}<div><div class="muted small">Your progress</div>
        <div class="mono" style="font-size:28px">${t.passed}<span class="muted"> / ${t.total}</span></div>
        <div class="muted small" style="margin-top:8px">${doneLabs} of ${model.labs.length} labs done${hours ? ` · about ${hours} h left` : ''}</div></div></div></section>
      ${everything ? `<div class="win"><div><strong>All ${t.total} tests are green.</strong><div>You finished the course labs. Run the evals and the incident drill for a final look.</div></div></div>` : nlesson ? `
      <section class="card continue"><div><div class="eyebrow">Continue where you left off</div>
        <h2 style="font-size:22px;margin:6px 0 2px">Lab ${nl.n} · Lesson ${esc(nlesson.id.replace(/^c/, 'Case '))}: ${esc(nlesson.title)}</h2>
        <div class="muted small">${lessonInfo(nl.n, nlesson.id).passed} of ${lessonInfo(nl.n, nlesson.id).total} tests passing in this lesson</div></div>
        <a class="btn primary" href="#/lesson/${nl.n}/${encodeURIComponent(nlesson.id)}">Continue</a></section>` : ''}
      ${model.labs.map((l) => setupError(l.n)).join('')}
      <section class="section"><h2>The roadmap</h2><div class="grid4">${model.labs.map(labTile).join('')}</div></section>
      <section class="section"><h2>Meet the people in the room</h2><div class="people">${model.people.map((p) =>
        `<div class="person"><div class="avatar">${esc(p.name.split(' ').map((w) => w[0]).join(''))}</div><strong>${esc(p.name)}</strong><span class="muted small">${esc(p.role)}</span></div>`).join('')}</div>
        <p class="muted small" style="margin:0">From docs/discovery_notes.md. Every lab solves a problem someone here described.</p></section></main>`;
  }

  // Shown when pytest could not grade a lab at all (setup problem or broken code), as opposed to tests failing.
  function setupError(n) {
    const e = labInfo(n).error;
    return e ? `<div class="fail" role="alert"><div class="n">Lab ${n} could not be checked</div><div>${esc(e)}</div>
      <div class="muted small" style="margin-top:6px">Fix this, save, and the lab re-checks by itself. The full output is below.</div></div>` : '';
  }

  function outputPanel(n) {
    const i = labInfo(n);
    if (!i.output && !running.includes(n)) return '';
    const when = i.ranAt ? new Date(i.ranAt * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '';
    return `<details class="card output" data-output="${n}" ${outputOpen[n] ? 'open' : ''}>
      <summary><h3 style="display:inline">Test output</h3> <span class="muted small">${running.includes(n) ? 'running…' : `Lab ${n} · last run ${when}`}</span></summary>
      <pre>${esc(i.output || '')}</pre></details>`;
  }

  function labTile(l) {
    const i = labInfo(l.n);
    return `<a class="lab ${i.status}" href="#/lab/${l.n}"><div class="row"><span class="mono">LAB ${l.n} · ${esc(l.time)}</span><span class="pill ${i.status}">${label[i.status]}</span></div>
      <div class="t">${esc(l.title)}</div><div class="bar ${i.status === 'done' ? 'done' : ''}"><i style="width:${pct(i.passed, i.total || l.tests)}%"></i></div>
      <div class="row"><span>${i.passed} / ${i.total || l.tests} tests</span><span>${l.needs ? 'Needs ' + esc(l.needs) : 'Start here'}</span></div></a>`;
  }

  function labView(n) {
    const lab = findLab(n);
    if (!lab) return home();
    const i = labInfo(lab.n);
    const quizItems = lab.say.map((q, k) => {
      const key = `${lab.n}:${k}`;
      return `<label class="q"><input type="checkbox" data-quiz="${key}" ${quiz[key] ? 'checked' : ''}><span>${esc(q)}</span></label>`;
    }).join('');
    return topbar(`<a href="#/">Roadmap</a><span>/</span><span>Lab ${lab.n}</span>`) + `<main class="page"><div class="cols">
      <div class="main" style="max-width:820px">
        <div class="mono muted small">LAB ${lab.n} · CHAPTER ${esc(lab.chapter)}</div><h1 style="font-size:40px">${esc(lab.title)}</h1>
        <div class="chips"><span class="pill">About ${esc(lab.time)}</span><span class="pill">${lab.tests} tests</span><span class="pill">${lab.needs ? 'Needs ' + esc(lab.needs) : 'No prerequisites'}</span><span class="pill ${i.status}">${i.passed} / ${i.total || lab.tests} · ${label[i.status]}</span></div>
        <div class="prose">${lab.intro}</div>
        ${setupError(lab.n)}
        <div class="card cmd"><div><h3>Run this lab</h3><code>pytest tests/test_lab${lab.n}.py</code></div>
          <button class="btn primary" data-act="run" data-scope="lab" data-lab="${lab.n}" ${running.includes(lab.n) ? 'disabled' : ''}>${host.caps.terminal ? 'Run in terminal' : 'Check lab'}</button></div>
        ${outputPanel(lab.n)}
        <h2 style="font-size:22px">Lessons</h2>
        <div class="card" style="padding:0;overflow:hidden">${lab.lessons.map((l, k) => {
          const li = lessonInfo(lab.n, l.id);
          return `<a href="#/lesson/${lab.n}/${encodeURIComponent(l.id)}" class="nav" style="padding:16px 22px;border-radius:0;${k ? 'border-top:1px solid var(--border);' : ''}align-items:flex-start">
            <span class="mono small" style="width:38px;color:var(--accent-text)">${esc(l.id.replace(/^c/, 'C'))}</span>
            <span style="flex:1;color:var(--text);font-weight:600">${esc(l.title)}${li.unlocked === false ? ' <span class="muted small">(finish earlier lessons first)</span>' : ''}</span>
            <span class="muted small mono">${li.passed}/${li.total}</span><span class="pill ${li.status}">${label[li.status]}</span></a>`;
        }).join('')}</div>
        ${lab.say.length ? `<div class="card"><h3>Say it out loud · self-check</h3><p class="muted small" style="margin-top:0">Tick each one when you can answer it without looking.</p>${quizItems}</div>` : ''}
        ${lab.see ? `<div class="card"><h3>See it work</h3><div class="prose">${lab.see}</div></div>` : ''}
      </div></div></main>`;
  }

  function lessonView(n, id) {
    const lab = findLab(n);
    const idx = lab ? lab.lessons.findIndex((l) => l.id === id) : -1;
    if (idx < 0) return labView(n);
    const l = lab.lessons[idx], li = lessonInfo(lab.n, l.id);
    const prev = lab.lessons[idx - 1], next = lab.lessons[idx + 1];
    const nextLab = !next ? findLab(lab.n + 1) : null;
    const h = l.html;
    const display = (x) => esc(x.id.replace(/^c/, 'Case '));
    const justDone = li.status === 'done';
    const stepFiles = l.files.length ? `<div class="chips" style="margin-top:6px">${l.files.map((f) =>
      `<button class="chip" data-act="open" data-file="${attr(f)}" title="Open in the editor">${esc(f)}</button>`).join('')}</div>` : '';
    const fails = li.failures.map((f, k) => `<div class="fail"><div class="n">${esc(f.name)}</div><div>${esc(f.message)}</div>${f.detail ? `<details><summary class="muted small" style="cursor:pointer;margin-top:6px">Show trace</summary><pre>${esc(f.detail)}</pre></details>` : ''}</div>`).join('');
    const refFile = l.files.find((f) => f.startsWith('atlas/') || f.startsWith('prompts/') || f.startsWith('docs/'));
    return topbar(`<a href="#/">Roadmap</a><span>/</span><a href="#/lab/${lab.n}">Lab ${lab.n}</a><span>/</span><span>${display(l)}</span>`) + `<main class="page"><div class="cols">
      <nav class="side" aria-label="Lessons"><div class="eyebrow" style="padding:0 12px 8px">Lab ${lab.n} · ${esc(lab.title)}</div>${lab.lessons.map((x) => {
        const xi = lessonInfo(lab.n, x.id);
        return `<a class="nav ${x.id === l.id ? 'cur' : ''}" href="#/lesson/${lab.n}/${encodeURIComponent(x.id)}"><span class="id mono">${esc(x.id.replace(/^c/, 'C'))}</span><span>${esc(x.title.length > 34 ? x.title.slice(0, 33) + '…' : x.title)}</span><span class="st" style="color:${xi.status === 'done' ? 'var(--done-fg)' : 'var(--muted)'}">${icon[xi.status]}</span></a>`;
      }).join('')}</nav>
      <div class="main"><div><div class="mono small" style="color:var(--accent-text)">${esc(l.kind.toUpperCase())} ${display(l)}</div><h1 style="font-size:34px;margin-top:6px">${esc(l.title)}</h1></div>
        ${justDone ? `<div class="win"><div><strong>Lesson complete ✓</strong><div>${li.passed} of ${li.total} tests passing.</div></div>${next ? `<a class="btn primary" href="#/lesson/${lab.n}/${encodeURIComponent(next.id)}">Next: ${esc(next.id)} →</a>` : nextLab ? `<a class="btn primary" href="#/lab/${nextLab.n}">Lab ${lab.n} done. Start Lab ${nextLab.n} →</a>` : `<a class="btn primary" href="#/">Course complete →</a>`}</div>` : ''}
        ${h.lead ? `<div class="card"><div class="prose">${h.lead}</div></div>` : ''}
        ${h.idea ? `<section class="card"><h3>The idea</h3><div class="prose">${h.idea}</div></section>` : ''}
        ${h.practical ? `<section class="card"><h3>Practical</h3><div class="prose">${h.practical}</div>${stepFiles}</section>` : ''}
        <section class="card cmd"><div><h3>Check</h3><code>${esc(l.check || `pytest tests/test_lab${lab.n}.py`)}</code></div>
          <button class="btn primary" data-act="run" data-scope="lesson" data-lab="${lab.n}" data-lesson="${attr(l.id)}" ${running.includes(lab.n) ? 'disabled' : ''}>${running.includes(lab.n) ? 'Running…' : host.caps.terminal ? 'Run in terminal' : 'Run check'}</button></section>
        ${setupError(lab.n)}
        ${outputPanel(lab.n)}
        ${h.trap ? `<section class="card trap"><h3>Exam trap</h3><div class="prose">${h.trap}</div></section>` : ''}
        <div class="nextrow">${prev ? `<a class="btn" href="#/lesson/${lab.n}/${encodeURIComponent(prev.id)}">← ${esc(prev.id)} ${esc(prev.title.slice(0, 28))}</a>` : '<span></span>'}
          ${next ? `<a class="btn ${justDone ? 'primary' : ''}" href="#/lesson/${lab.n}/${encodeURIComponent(next.id)}">${esc(next.id)} ${esc(next.title.slice(0, 28))} →</a>` : `<a class="btn" href="#/lab/${lab.n}">Back to the lab</a>`}</div></div>
      <aside class="rail"><div class="card"><h3>Test status</h3>
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:10px"><span class="pill ${li.status}">${label[li.status]}</span><span class="mono">${li.passed} / ${li.total}</span></div>
        <div class="bar ${justDone ? 'done' : ''}"><i style="width:${pct(li.passed, li.total)}%"></i></div>
        ${li.failed ? `<div class="muted small" style="margin-top:10px">Next failing test:</div>${fails}` : li.total ? '<div class="muted small" style="margin-top:10px">Every test in this lesson passes.</div>' : '<div class="muted small" style="margin-top:10px">Run the check to see results.</div>'}
        ${host.caps.diff && refFile && li.failed ? `<button class="btn" style="margin-top:12px;width:100%" data-act="diff" data-file="${attr(refFile)}">Compare with reference solution</button><div class="muted small" style="margin-top:6px">Spoiler: try a few more runs first.</div>` : ''}</div>
        ${l.files.length ? `<div class="card"><h3>In the code</h3><div class="chips" style="flex-direction:column;align-items:flex-start">${l.files.map((f) => `<button class="chip" data-act="open" data-file="${attr(f)}">${esc(f)}</button>`).join('')}</div></div>` : ''}
      </aside></div></main>`;
  }

  function render() {
    if (!model) { app.innerHTML = '<main class="page"><p class="muted">Loading the labs…</p></main>'; return; }
    const r = route();
    const scroll = window.scrollY;
    app.innerHTML = (r[0] === 'lab' ? labView(r[1]) : r[0] === 'lesson' ? lessonView(r[1], r[2]) : home())
      + (toast ? `<div class="toast" role="status">${esc(toast)}</div>` : '');
    window.scrollTo(0, scroll);
  }

  document.addEventListener('click', (e) => {
    const b = e.target.closest('[data-act]');
    if (!b || b.disabled) return;
    const a = b.dataset.act;
    if (a === 'run') host.post({ type: 'run', scope: b.dataset.scope, lab: Number(b.dataset.lab) || undefined, lesson: b.dataset.lesson, command: commandFor(b.dataset) });
    if (a === 'open') host.post({ type: 'open', file: b.dataset.file, line: Number(b.dataset.line) || 0 });
    if (a === 'diff') host.post({ type: 'diff', file: b.dataset.file });
  });
  // <details> toggles don't bubble; remember which output panels are open so live re-renders keep them open.
  document.addEventListener('toggle', (e) => {
    const n = e.target.dataset && e.target.dataset.output;
    if (n) outputOpen[n] = e.target.open;
  }, true);
  document.addEventListener('change', (e) => {
    const q = e.target.dataset && e.target.dataset.quiz;
    if (!q) return;
    quiz[q] = e.target.checked;
    host.save({ quiz });
  });
  function commandFor(d) {
    if (d.scope === 'lesson') { const l = findLab(d.lab).lessons.find((x) => x.id === d.lesson); return l && l.check; }
    if (d.scope === 'lab') return `pytest tests/test_lab${d.lab}.py`;
    return 'python site/progress.py --print';
  }

  function flash(text) { toast = text; render(); clearTimeout(flash.t); flash.t = setTimeout(() => { toast = null; render(); }, 5000); }

  host.onMessage((m) => {
    if (m.type === 'init') { model = m.model; progress = m.progress; render(); }
    if (m.type === 'opened') flash(m.error || `Opened ${m.opened} in ${m.app}${m.hint ? ` (${m.hint})` : ''}`);
    if (m.type === 'running') { running = m.labs || []; render(); }
    if (m.type === 'progress') {
      progress = m.progress;
      const wins = (m.changed || []).filter((c) => c.to === 'done');
      if (wins.length) { const w = wins[wins.length - 1]; flash(w.lesson ? `Lesson ${w.lesson.replace(/^c/, 'Case ')} complete` : `Lab ${w.lab} complete`); }
      render();
    }
  });
  window.addEventListener('hashchange', () => { render(); window.scrollTo(0, 0); });
  host.post({ type: 'ready' });
})();
