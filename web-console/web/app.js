"use strict";
const $ = (s) => document.querySelector(s);
const api = async (path, body) => (await fetch(path, body
  ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }
  : {})).json();
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

let CTX = null;
let selected = "clean";
let reasonMap = {};

function showView(name) {
  document.querySelectorAll(".navitem").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  document.querySelectorAll(".view").forEach((v) => v.classList.toggle("active", v.id === "view-" + name));
}
document.querySelectorAll(".navitem").forEach((b) => b.addEventListener("click", () => showView(b.dataset.view)));

async function boot() {
  CTX = await api("/api/context");
  $("#gw-status").textContent = "gateway " + CTX.gateway.replace(/^https?:\/\//, "");
  CTX.guardrails.forEach((g) => (reasonMap[g.reason] = g));

  // scenarios
  $("#scenarios").innerHTML = CTX.scenarios.map((s) => `
    <button class="scn${s.id === selected ? " sel" : ""}" data-id="${s.id}">
      <div class="label">${esc(s.label)}</div>
      <div class="obligor">${esc(s.obligor)}</div>
      <div class="amt">${esc(s.amount)}</div>
      <span class="exp ${s.outcome}">${esc(s.expect)}</span>
    </button>`).join("");
  document.querySelectorAll(".scn").forEach((c) => c.addEventListener("click", () => {
    selected = c.dataset.id;
    document.querySelectorAll(".scn").forEach((x) => x.classList.toggle("sel", x === c));
  }));

  // guardrails + policy
  $("#guardrails").innerHTML = CTX.guardrails.map((g) =>
    `<div class="gr"><span class="reg">${esc(g.regulation)}</span><span class="plain">${esc(g.plain)}</span></div>`).join("");
  $("#policy").textContent = CTX.policy.trim();

  // tools
  $("#tools").innerHTML = CTX.tools.map((t) =>
    `<div class="trow"><code>${esc(t.tool_name)}</code><span class="dom ${t.compliance_domain}">${esc(t.compliance_domain)}</span><span class="desc">${esc(t.description)}</span></div>`).join("");
}

async function run() {
  const btn = $("#run");
  btn.disabled = true; btn.textContent = "Running…"; $("#run-hint").textContent = "";
  $("#timeline").innerHTML = ""; $("#summary").className = "summary hide";
  try {
    const r = await api("/api/run", { scenario: selected });
    renderRun(r);
  } catch (e) {
    $("#run-hint").textContent = "run failed -- is the gateway up?";
  } finally {
    btn.disabled = false; btn.textContent = "Run assessment";
  }
}

function renderRun(r) {
  const steps = r.steps || [];
  const write = steps.find((s) => s.tool && s.tool.endsWith("risk_report_writer"));
  const denied = write && write.decision === "deny";
  const sum = $("#summary");
  sum.className = "summary " + (denied ? "deny" : "allow");
  if (denied) {
    const reason = write.advice.reason || "";
    const g = reasonMap[reason];
    sum.innerHTML = `<span class="st">Write blocked.</span> ${esc(g ? g.plain : reason)}
      <span class="reg">${esc(write.advice.regulation || (g && g.regulation) || "")}</span>
      <div class="mut" style="margin-top:6px">The risk report was not written to core banking.</div>`;
  } else {
    sum.innerHTML = `<span class="st">Assessment recorded.</span> All six steps passed policy; the report was written to core banking under Cedar enforcement.`;
  }

  $("#timeline").innerHTML = steps.map((s) => {
    const dec = s.decision || "allow";
    const adv = (dec === "deny" && (s.advice.regulation || s.advice.reason)) ? `
      <div class="adv"><span>${esc((reasonMap[s.advice.reason] || {}).plain || s.advice.reason || "denied by policy")}</span>
      ${s.advice.regulation ? `<span class="reg">${esc(s.advice.regulation)}</span>` : ""}</div>` : "";
    return `<li class="tl ${dec}">
      <span class="num">${s.n}/6</span>
      <span class="body"><span class="toolname">${esc(s.tool)}</span>
        ${s.note ? `<div class="note">${esc(s.note)}</div>` : ""}${adv}</span>
      <span class="pill">${dec === "deny" ? "403 denied" : "200 allow"}</span>
    </li>`;
  }).join("");
  // staggered reveal
  document.querySelectorAll("#timeline .tl").forEach((el, i) => setTimeout(() => el.classList.add("in"), 90 + i * 130));

  // record view
  if (r.claim) {
    $("#record").textContent = JSON.stringify(r.claim, null, 2);
    $("#verify").disabled = false;
    $("#rec-hint").textContent = "";
  }
}

async function verify() {
  const v = await api("/api/verify", {});
  if (v.error) { $("#verify-result").innerHTML = `<div class="rslt">${esc(v.error)}</div>`; return; }
  $("#verify-checks").innerHTML = (v.checks || []).map((c) => {
    const p = c.status === "PASS";
    return `<div class="check ${p ? "pass" : "fail"}"><span class="box">${p ? "✓" : "✗"}</span><span class="name">${esc(c.name)}</span><span class="st">${c.status}</span></div>`;
  }).join("");
  if (v.result) {
    const ok = v.result.detail === "verified";
    $("#verify-result").innerHTML = `<div class="rslt ${ok ? "verified" : "partial"}"><b>${esc(v.result.detail)}</b> &mdash; software-only run; on real TDX / SEV-SNP the hardware check verifies too.</div>`;
  }
}

$("#run").addEventListener("click", run);
$("#verify").addEventListener("click", verify);
boot();
