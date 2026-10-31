"""Browser page for `label_tool --web`. Kept as a Python string: the repo hooks block .html files."""

PAGE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Hand labels</title>
<style>
  :root { --bg: #f4f3ef; --ink: #1d1d1b; --muted: #6b6a64; --line: #d6d4cc; --panel: #ffffff;
          --left: #e0861f; --right: #1f6fd1; --warn: #b3261e; --ok: #2f7d32; }
  * { box-sizing: border-box; }
  body { margin: 0; background: var(--bg); color: var(--ink);
         font: 14px/1.4 -apple-system, "Helvetica Neue", Arial, sans-serif; }
  header { display: flex; gap: 16px; align-items: baseline; padding: 10px 16px; border-bottom: 1px solid var(--line); }
  header b { font-size: 15px; }
  header span { color: var(--muted); }
  main { display: grid; grid-template-columns: minmax(0, 1fr) 260px; gap: 16px; padding: 16px; }
  @media (max-width: 900px) { main { grid-template-columns: 1fr; } }
  .stage { position: relative; background: #000; border: 1px solid var(--line); align-self: start; }
  canvas { display: block; width: 100%; height: auto; cursor: crosshair; }
  aside { background: var(--panel); border: 1px solid var(--line); padding: 14px; align-self: start; }
  h2 { font-size: 12px; text-transform: uppercase; letter-spacing: .06em; color: var(--muted); margin: 14px 0 6px; }
  h2:first-child { margin-top: 0; }
  .next { font-size: 18px; font-weight: 600; }
  .hands div { padding: 2px 0; }
  .row { display: flex; gap: 6px; flex-wrap: wrap; }
  button { font: inherit; padding: 6px 10px; border: 1px solid var(--line); background: var(--bg);
           border-radius: 3px; cursor: pointer; color: var(--ink); }
  button:hover { border-color: var(--muted); }
  button.on { background: var(--ink); color: #fff; border-color: var(--ink); }
  button.primary { background: var(--ink); color: #fff; border-color: var(--ink); width: 100%; padding: 9px; margin-top: 6px; }
  kbd { font: 12px ui-monospace, Menlo, monospace; color: var(--muted); }
  #msg { min-height: 20px; margin-top: 8px; color: var(--warn); }
  #msg.ok { color: var(--ok); }
  .keys { color: var(--muted); font-size: 12px; margin-top: 12px; }
</style>
</head>
<body>
<header><b id="title">Loading</b><span id="progress"></span></header>
<main>
  <div class="stage"><canvas id="c"></canvas></div>
  <aside>
    <h2>Next click</h2>
    <div class="next" id="next"></div>
    <h2>Hands</h2>
    <div class="hands" id="hands"></div>
    <h2>Side of the current hand</h2>
    <div class="row">
      <button id="bl">Left <kbd>L</kbd></button>
      <button id="br">Right <kbd>R</kbd></button>
      <button id="bu">Undo <kbd>U</kbd></button>
      <button id="bc">Clear hand <kbd>C</kbd></button>
    </div>
    <h2>Tags</h2>
    <div class="row" id="tags"></div>
    <button class="primary" id="bs">Save and next <kbd style="color:#ccc">Enter</kbd></button>
    <div class="row" style="margin-top:6px"><button id="bx">Skip unusable frame <kbd>X</kbd></button></div>
    <div id="msg"></div>
    <div class="keys">For each visible hand: click the wrist, then the thumb, index, middle, ring and little fingertips,
      then set the side. No hands in view: just save. Every save is written to disk straight away.
      <span id="sughelp"></span></div>
  </aside>
</main>
<script>
const NAMES = ["wrist", "thumb tip", "index tip", "middle tip", "ring tip", "little tip"];
const COL = { left: "#e0861f", right: "#1f6fd1", null: "#ffd21f" };   // side not set yet: bright yellow
const c = document.getElementById("c"), ctx = c.getContext("2d");
let st = null, img = new Image(), hands = [], tags = [], busy = false, active = -1;

const $ = id => document.getElementById(id);
function say(text, ok) { $("msg").textContent = text || ""; $("msg").className = ok ? "ok" : ""; }

async function load(s) {
  st = s || await (await fetch("/api/state")).json();
  // suggested hands start pre-filled; sug = index of the suggestion, moved = points the labeller replaced
  hands = (st.suggestions || []).map((g, i) => ({ points: g.points.map(p => [...p]), side: g.side, sug: i, moved: new Set() }));
  tags = []; active = -1;
  $("sughelp").textContent = hands.length ? `Hollow points are ${st.prefill} suggestions: check each one. ` +
    "Click near a point to move it, C removes a wrong hand, L/R fixes the side." : "";
  $("title").textContent = st.clip + (st.frame === null ? "" : "  frame " + st.frame);
  $("progress").textContent = `${st.done}/${st.goal} labelled by ${st.labeller} · ${st.out}`;
  if (st.frame === null) { say("All frames for this run are labelled. You can close this tab.", true); draw(); return; }
  img = new Image();
  img.onload = () => { c.width = img.naturalWidth; c.height = img.naturalHeight; draw(); };
  img.src = `/frame/${st.frame}.jpg`;
  $("tags").innerHTML = st.tags.map((t, i) => `<button data-tag="${t}">${t} <kbd>${i + 1}</kbd></button>`).join("");
  document.querySelectorAll("[data-tag]").forEach(b => b.onclick = () => toggleTag(b.dataset.tag));
  draw();
}

function cur() { return hands[hands.length - 1]; }
function act() { return hands.at(active); }

function draw() {
  if (img.complete && img.naturalWidth) ctx.drawImage(img, 0, 0);
  const r = Math.max(4, c.width / 300);
  for (const h of hands) {
    ctx.strokeStyle = ctx.fillStyle = COL[h.side];
    ctx.lineWidth = Math.max(2, c.width / 800);
    const [w, ...tips] = h.points;
    for (const p of tips) { ctx.beginPath(); ctx.moveTo(w[0], w[1]); ctx.lineTo(p[0], p[1]); ctx.stroke(); }
    h.points.forEach((p, k) => {
      ctx.beginPath(); ctx.arc(p[0], p[1], k ? r : r * 1.6, 0, 7);
      if (h.sug != null && !h.moved.has(k)) {          // suggestion not checked by a click: hollow ring, dark edge
        ctx.lineWidth = Math.max(5, c.width / 300); ctx.strokeStyle = "#111"; ctx.stroke();
        ctx.lineWidth = Math.max(3, c.width / 600); ctx.strokeStyle = COL[h.side]; ctx.stroke();
      } else {
        ctx.fill(); ctx.strokeStyle = "#fff"; ctx.lineWidth = 1.5; ctx.stroke(); ctx.strokeStyle = COL[h.side];
      }
    });
    if (w) { ctx.font = `bold ${r * 5}px sans-serif`; ctx.fillText((h.side || "?")[0].toUpperCase(), w[0] + r * 2.5, w[1] + r * 5); }
  }
  const k = hands.length ? cur().points.length % 6 : 0;
  $("next").textContent = st && st.frame === null ? "done"
    : hands.length && cur().sug != null ? "check the suggestion" : NAMES[k] + (k === 0 && hands.length ? " of a new hand" : "");
  $("hands").innerHTML = hands.length ? hands.map((h, i) =>
    `<div>${hands.at(active) === h ? "&gt; " : ""}Hand ${i + 1}${h.sug != null ? ` (suggested, ${h.moved.size} moved)` : ""}: ` +
    `${h.points.length}/6 points, side <b style="color:${COL[h.side]}">${h.side || "not set"}</b></div>`).join("")
    : "<div>none yet (saving now records “no hands”)</div>";
  const side = hands.length ? act().side : null;
  $("bl").className = side === "left" ? "on" : ""; $("br").className = side === "right" ? "on" : "";
  document.querySelectorAll("[data-tag]").forEach(b => b.className = tags.includes(b.dataset.tag) ? "on" : "");
}

c.addEventListener("click", e => {
  if (!st || st.frame === null) return;
  const b = c.getBoundingClientRect();
  const x = (e.clientX - b.left) * c.width / b.width, y = (e.clientY - b.top) * c.height / b.height;
  const manualOpen = hands.length && cur().sug == null && cur().points.length < 6;
  if (!manualOpen) {
    let best = null, bestD = st.radius;              // move the nearest suggested point, if close enough
    hands.forEach((h, i) => h.sug != null && h.points.forEach((p, k) => {
      const d = Math.hypot(p[0] - x, p[1] - y); if (d <= bestD) { best = [i, k]; bestD = d; }
    }));
    if (best) {
      const [i, k] = best; hands[i].points[k] = [x, y]; hands[i].moved.add(k); active = i; say(""); return draw();
    }
    if (hands.length === 2) return say("Two hands at most.");
    hands.push({ points: [], side: null, sug: null, moved: new Set() });
  }
  cur().points.push([x, y]); active = hands.length - 1; say(""); draw();
});

function setSide(s) { if (!hands.length) return say("Click the wrist first."); act().side = s; say(""); draw(); }
function undo() {
  if (!hands.length) return;
  if (cur().sug != null) return say("Suggested hand: click near a point to move it, or C to remove the hand.");
  cur().points.pop(); if (!cur().points.length) hands.pop(); active = -1; draw();
}
function clearHand() { if (!hands.length) return; hands.splice(active, 1); active = -1; say(""); draw(); }
function toggleTag(t) { tags = tags.includes(t) ? tags.filter(x => x !== t) : [...tags, t]; draw(); }

async function post(path, body) {
  if (busy) return; busy = true;
  try {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const j = await r.json();
    if (r.status === 400) return say(j.error);
    if (r.status === 409) { await load(j); return say(j.error); }
    const prev = st.frame; await load(j);
    say(path.endsWith("save") ? `Saved frame ${prev}.` : `Skipped frame ${prev}.`, true);
  } catch (err) { say("Could not reach the label server. Is it still running in the terminal?"); }
  finally { busy = false; }
}
function save() { if (st && st.frame !== null) post("/api/save", { frame: st.frame, tags, hands: hands.map(h => ({ points: h.points, side: h.side, sug: h.sug })) }); }
function skip() { if (st && st.frame !== null) post("/api/skip", { frame: st.frame }); }

$("bl").onclick = () => setSide("left"); $("br").onclick = () => setSide("right");
$("bu").onclick = undo; $("bc").onclick = clearHand; $("bs").onclick = save; $("bx").onclick = skip;
document.addEventListener("keydown", e => {
  if (e.metaKey || e.ctrlKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (k === "l") setSide("left"); else if (k === "r") setSide("right");
  else if (k === "u") undo(); else if (k === "c") clearHand(); else if (k === "x") skip();
  else if (k === "enter" || k === "n") { e.preventDefault(); save(); }
  else if ("12345".includes(k) && k.length === 1 && st) toggleTag(st.tags[+k - 1]);
});
load();
</script>
</body>
</html>
"""
