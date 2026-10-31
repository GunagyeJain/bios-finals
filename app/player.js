// Synced player: everything below follows video.currentTime on every animation frame.
// DATA comes from player.py. All text from the data goes through esc() before it reaches innerHTML.
(() => {
  const D = DATA;
  const C = { green: "#44a282", yellow: "#d9a441", red: "#e5566f", none: "#2c2c30", left: "#4a8ad6",
              right: "#f2f2f3", step: "#3a3a3e", accent: "#4a8ad6", grid: "#2b2b2e", muted: "#8a8c92" };
  const WORD = { green: "Usable", yellow: "Check", red: "Unusable" };
  const ALERT = { safety: C.red, step_missing: C.yellow, step_order: C.yellow, step_extra: C.muted };
  const GRIP = { "2f": "pinch (2f)", "5f": "wrap (5f)", generic: "press (generic)", unsure: "unsure" };
  const $ = (id) => document.getElementById(id);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const mmss = (s, tenths) => {
    s = Math.max(0, s);
    const m = Math.floor(s / 60), r = s - m * 60;
    return tenths ? `${m}:${r.toFixed(1).padStart(4, "0")}` : `${m}:${String(Math.round(r) % 60).padStart(2, "0")}`;
  };
  const at = (rows, t) => rows.filter((r) => r[0] <= t && t < r[1]);
  const video = $("v");
  let lastT = -1, lastNow = -1;          // last drawn time and list row; -1 forces a redraw
  const dur = D.duration;

  // ---------- views: Ours / Baseline / 2-finger robot / 5-finger robot ----------
  const views = $("views") || document.querySelector(".views");
  let current = null;
  function setView(v) {
    if (!v || !v.url || (current && current.key === v.key)) return;
    const t = video.currentTime || 0, playing = !video.paused;
    current = v;
    video.src = v.url;
    video.addEventListener("loadedmetadata", () => { video.currentTime = t; if (playing) video.play(); }, { once: true });
    views.querySelectorAll("button").forEach((b) => b.setAttribute("aria-selected", b.dataset.key === v.key));
  }
  D.views.forEach((v, i) => {
    const b = document.createElement("button");
    b.textContent = v.label; b.dataset.key = v.key; b.setAttribute("role", "tab");
    b.disabled = !v.url;
    b.title = v.url ? `View ${i + 1}` : v.key.endsWith("f") ? "Robot overlay not rendered yet" : "Not rendered yet";
    b.onclick = () => setView(v);
    views.appendChild(b);
  });
  const first = D.views.find((v) => v.url);
  if (first) setView(first);
  else if (D.source) { video.src = D.source; current = { key: "source" }; }
  else { video.hidden = true; document.querySelector(".novideo").hidden = false; }

  // ---------- quality strip under the video ----------
  const strip = $("strip");
  let last = 0;
  [...D.segments].sort((a, b) => a[0] - b[0]).forEach(([a, b, light]) => {
    if (a > last) strip.insertAdjacentHTML("beforeend", `<span style="flex:${a - last}"></span>`);
    strip.insertAdjacentHTML("beforeend", `<span style="flex:${b - a};background:${C[light] || C.none}"></span>`);
    last = b;
  });
  if (dur > last) strip.insertAdjacentHTML("beforeend", `<span style="flex:${dur - last}"></span>`);
  const head = document.createElement("div"); head.className = "head"; strip.appendChild(head);
  strip.onclick = (e) => seek((e.offsetX / strip.clientWidth) * dur);

  function seek(t) { video.currentTime = Math.max(0, Math.min(dur - 0.05, t)); }

  // ---------- lists: unusable stretches / steps / alerts ----------
  const stretches = [];
  [...D.segments].filter((s) => s[2] === "red").sort((a, b) => a[0] - b[0]).forEach(([a, b, , why]) => {
    const prev = stretches[stretches.length - 1];
    if (prev && Math.abs(prev[1] - a) < 1e-6) { prev[1] = b; if (why) prev[2].add(why); }
    else stretches.push([a, b, new Set(why ? [why] : [])]);
  });
  const LISTS = {
    stretches: { label: `Unusable ${stretches.length}`, rows: stretches.map(([a, b, w]) => [a, b, `${(b - a).toFixed(0)} s · ${[...w].join(", ").replaceAll(";", ", ") || "no reason"}`]),
                 empty: D.segments.length ? "No unusable seconds in this clip." : "Not graded yet." },
    steps: { label: `Steps ${D.steps.length}`, rows: D.steps.map(([a, b, verb, obj, hand, cap]) => [a, b, cap || `${verb} ${obj || ""} (${hand || "?"})`]),
             empty: "Steps are not processed for this clip yet." },
    alerts: { label: `Alerts ${D.alerts.length}`, rows: D.alerts.map(([a, b, kind, detail]) => [a, b, `${kind.replace("_", " ")}: ${detail}`]),
              empty: "No alerts for this clip." },
  };
  let listKey = stretches.length ? "stretches" : "steps";
  const tabs = document.querySelector(".ltabs"), list = $("list");
  function drawList() {
    tabs.querySelectorAll("button").forEach((b) => b.setAttribute("aria-selected", b.dataset.key === listKey));
    const L = LISTS[listKey];
    list.innerHTML = L.rows.length ? L.rows.map(([a, b, text], i) =>
      `<li data-i="${i}" data-t="${a}"><span class="t">${mmss(a)}–${mmss(b)}</span><span>${esc(text)}</span></li>`).join("")
      : `<li class="empty">${esc(L.empty)}</li>`;
    list.querySelectorAll("li[data-t]").forEach((li) => (li.onclick = () => seek(+li.dataset.t + 0.01)));
    lastNow = -1;
  }
  Object.entries(LISTS).forEach(([k, L]) => {
    const b = document.createElement("button");
    b.textContent = L.label; b.dataset.key = k; b.setAttribute("role", "tab");
    b.onclick = () => { listKey = k; drawList(); };
    tabs.appendChild(b);
  });
  drawList();

  // ---------- timeline ----------
  const ROWS = ["Light", "Left", "Right", "Steps", "Alerts"], GUT = 58, ROW_H = 26, TOP = 4, AXIS = 22;
  const box = $("tl"), tip = $("tip");
  let svgW = 0, playhead = null;
  const x = (t) => GUT + (t / dur) * (svgW - GUT - 4);
  const tAt = (px) => Math.max(0, Math.min(dur, ((px - GUT) / (svgW - GUT - 4)) * dur));
  function tickStep() { for (const s of [1, 2, 5, 10, 15, 30, 60]) if (dur / s <= 10) return s; return 120; }
  function drawTimeline() {
    svgW = box.clientWidth;
    const H = TOP + ROWS.length * ROW_H + AXIS, bars = [];
    const bar = (row, a, b, color, opacity = 1, label = "", tipText = "") => {
      const y = TOP + row * ROW_H + 5, w = Math.max(2, x(b) - x(a));
      bars.push(`<rect x="${x(a).toFixed(1)}" y="${y}" width="${w.toFixed(1)}" height="${ROW_H - 10}" rx="2" fill="${color}" opacity="${opacity}" data-tip="${esc(tipText)}"/>`);
      if (label && w > 44) bars.push(`<text x="${(x(a) + 5).toFixed(1)}" y="${y + 12}" class="bl">${esc(label)}</text>`);
    };
    D.segments.forEach(([a, b, li, why]) => bar(0, a, b, C[li] || C.none, 1, "", `${mmss(a)} ${WORD[li] || li}${why ? " · " + why.replaceAll(";", ", ") : ""}`));
    D.contacts.forEach(([a, b, hand, state, obj, grip]) => bar(hand === "left" ? 1 : 2, a, b, C[hand], state === "portable" ? 1 : 0.45, "",
      `${mmss(a)}–${mmss(b)} ${hand} holds ${obj} · ${GRIP[grip] || grip}`));
    D.steps.forEach(([a, b, verb, obj, hand, cap]) => bar(3, a, b, C.step, 1, verb, `${mmss(a)} ${cap || verb + " " + (obj || "")}`));
    D.alerts.forEach(([a, b, kind, detail]) => bar(4, a, b, ALERT[kind] || C.muted, 1, "", `${mmss(a)} ${kind.replace("_", " ")}: ${detail}`));
    const step = tickStep(), ticks = [];
    for (let t = 0; t <= dur + 1e-6; t += step)
      ticks.push(`<line x1="${x(t)}" x2="${x(t)}" y1="${TOP}" y2="${TOP + ROWS.length * ROW_H}" stroke="${C.grid}" stroke-dasharray="2 3"/>` +
                 `<text x="${x(t)}" y="${H - 6}" class="tk" text-anchor="${t === 0 ? "start" : "middle"}">${mmss(t)}</text>`);
    const labels = ROWS.map((r, i) => `<text x="0" y="${TOP + i * ROW_H + 17}" class="rl">${r}</text>`).join("");
    box.innerHTML = `<svg viewBox="0 0 ${svgW} ${H}" height="${H}" role="img" aria-label="Clip timeline">
      <style>.rl{fill:${C.muted};font:12px "Public Sans",sans-serif}.tk{fill:${C.muted};font:12px "IBM Plex Mono",monospace}
      .bl{fill:#fff;font:11px "Public Sans",sans-serif;pointer-events:none}</style>
      ${labels}${ticks.join("")}${bars.join("")}
      <line id="ph" x1="0" x2="0" y1="0" y2="${TOP + ROWS.length * ROW_H}" stroke="${C.accent}" stroke-width="2"/></svg>`;
    playhead = box.querySelector("#ph");
    lastT = -1;
  }
  box.addEventListener("click", (e) => seek(tAt(e.offsetX)));
  box.addEventListener("mousemove", (e) => {
    const r = e.target.closest("rect"), text = r ? r.dataset.tip : mmss(tAt(e.offsetX), true);
    tip.hidden = false; tip.textContent = text;
    const pr = box.parentElement.getBoundingClientRect();
    tip.style.left = Math.min(e.clientX - pr.left + 12, pr.width - tip.offsetWidth - 8) + "px";
    tip.style.top = e.clientY - pr.top - 34 + "px";
  });
  box.addEventListener("mouseleave", () => (tip.hidden = true));
  new ResizeObserver(drawTimeline).observe(box);
  $("legend").innerHTML = [["Usable", C.green], ["Check", C.yellow], ["Unusable", C.red], ["Left hand holds", C.left],
    ["Right hand holds", C.right], ["Now", C.accent]].map(([t, c]) => `<span><i style="background:${c}"></i>${t}</span>`).join("");

  // ---------- this moment ----------
  const hands = D.hands, hTimes = hands.map((h) => h[0]);
  function handAt(t) {
    let lo = 0, hi = hTimes.length - 1;
    if (hi < 0) return null;
    while (lo < hi) { const mid = (lo + hi + 1) >> 1; if (hTimes[mid] <= t) lo = mid; else hi = mid - 1; }
    return hands[lo];
  }
  const handText = (h) => h ? `${esc(h[0])} <span class="m">${h[1].toFixed(2)}</span>${h[2].length ? ` <span class="dim">· ${esc(h[2].join(", "))}</span>` : ""}`
                            : `<span class="dim">not found</span>`;
  function robotText(cons) {
    if (!cons.length) return `<span class="dim">no grab</span>`;
    const grips = cons.map((c) => c[5]);
    if (grips.every((g) => g === "unsure")) return `<span class="dim">can't tell</span>`;
    return ["2f", "5f"].map((r) => {
      const ok = grips.every((g) => D.robot[r].includes(g));
      return `${r === "2f" ? "2-finger" : "5-finger"} <span class="${ok ? "ok" : "no"}">${ok ? "can copy" : "can't"}</span>`;
    }).join(" · ");
  }
  function update() {
    const t = video.currentTime || 0;
    if (Math.abs(t - lastT) > 0.02) {
      lastT = t;
      if (playhead) { const px = x(t); playhead.setAttribute("x1", px); playhead.setAttribute("x2", px); }
      head.style.left = `calc(${(t / dur) * 100}% - 1px)`;
      $("tc").textContent = `This moment · ${mmss(t, true)}`;
      const seg = at(D.segments, t)[0];
      $("lightsq").style.background = seg ? C[seg[2]] || C.none : C.none;
      $("light").textContent = seg ? WORD[seg[2]] || seg[2] : "Not graded";
      $("why").innerHTML = seg && seg[3] ? esc(seg[3].replaceAll(";", " · ")) : "&nbsp;";
      const h = handAt(t);
      $("hl").innerHTML = handText(h && h[1]); $("hr").innerHTML = handText(h && h[2]);
      const cons = at(D.contacts, t);
      $("hold").innerHTML = cons.length ? cons.map((c) => `${c[2] === "left" ? "L" : "R"} · ${esc(c[4])} <span class="dim">${esc(GRIP[c[5]] || c[5])}</span>`).join("; ")
                                        : `<span class="dim">nothing</span>`;
      $("robot").innerHTML = robotText(cons);
      const st = at(D.steps, t)[0];
      $("step").innerHTML = st ? esc(st[5] || `${st[2]} ${st[3] || ""}`) : `<span class="dim">—</span>`;
      const al = at(D.alerts, t);
      $("alert").innerHTML = al.length ? al.map((a) => esc(a[3])).join("; ") : `<span class="dim">none</span>`;
      const rows = LISTS[listKey].rows, i = rows.findIndex(([a, b]) => a <= t && t < b);
      if (i !== lastNow) {
        list.querySelectorAll("li.now").forEach((li) => li.classList.remove("now"));
        const li = list.querySelector(`li[data-i="${i}"]`);
        if (li) { li.classList.add("now"); if (!video.paused) li.scrollIntoView({ block: "nearest" }); }
        lastNow = i;
      }
    }
    requestAnimationFrame(update);
  }
  requestAnimationFrame(update);

  // ---------- keyboard ----------
  document.addEventListener("keydown", (e) => {
    if (e.target.closest("input, textarea")) return;
    if (e.code === "Space") { e.preventDefault(); video.paused ? video.play() : video.pause(); }
    else if (e.key === "ArrowRight") seek(video.currentTime + 5);
    else if (e.key === "ArrowLeft") seek(video.currentTime - 5);
    else if (/^[1-4]$/.test(e.key)) setView(D.views[+e.key - 1]);
  });
})();
