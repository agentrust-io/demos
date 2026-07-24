"use strict";

const $ = (s) => document.querySelector(s);
const api = async (path, body) => {
  const res = await fetch(path, body ? {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body),
  } : {});
  return res.json();
};

function setStatus(up, label) {
  const el = $("#status");
  el.className = "status " + (up ? "up" : "down");
  el.innerHTML = `<span class="d"></span> ${label}`;
}

async function loadPolicy() {
  try {
    const p = await api("/api/policy");
    $("#policy").textContent = p.policy.trim();
    $("#workspace").textContent = p.workspace;
    $("#catalog").innerHTML = p.tools.map((t) =>
      `<div class="crow"><code>${t.tool_name}</code><span class="desc">${t.description}</span></div>`).join("");
    setStatus(true, "gateway " + p.gateway.replace(/^https?:\/\//, ""));
  } catch (e) {
    setStatus(false, "web server unreachable");
  }
}

const TOOL_ARGS = {
  get_balance: () => ({ account_id: $("#gb-account").value }),
  get_customer: () => ({ customer_id: $("#gc-customer").value }),
  transfer_funds: () => ({
    from_account: $("#tf-from").value, to_account: $("#tf-to").value, amount: Number($("#tf-amount").value),
  }),
  export_records: () => ({ dataset: $("#er-dataset").value }),
};

function activityEntry({ tool, http_status, decision, text, request, response }) {
  $("#activity-empty").style.display = "none";
  const entry = document.createElement("div");
  entry.className = "entry " + decision;
  const pill = decision === "allow" ? `${http_status} allow`
    : decision === "deny" ? `${http_status} denied` : `${http_status} error`;
  const summary = decision === "allow" && text != null
    ? text : decision === "deny"
      ? (response.error && response.error.data && response.error.data.error_code) || "POLICY_DENY"
      : (response.error && response.error.message) || "";
  entry.innerHTML = `
    <div class="entry-head">
      <span class="arrow">tools/call</span><span class="tool">${tool}</span>
      <span class="pill">${pill}</span>
    </div>
    <div class="entry-body">
      <p class="lbl">result</p><pre class="code">${escapeHtml(String(summary))}</pre>
      <p class="lbl">request</p><pre class="code">${escapeHtml(JSON.stringify(request, null, 2))}</pre>
      <p class="lbl">gateway response</p><pre class="code">${escapeHtml(JSON.stringify(response, null, 2))}</pre>
    </div>`;
  entry.querySelector(".entry-head").addEventListener("click", () => entry.classList.toggle("open"));
  $("#activity").prepend(entry);
}

function escapeHtml(s) {
  return s.replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

async function sendCall(tool) {
  const args = TOOL_ARGS[tool]();
  const request = {
    jsonrpc: "2.0", id: 1, method: "tools/call",
    params: { name: tool, arguments: args, _cmcp: { workflow_id: "web-console" } },
  };
  const r = await api("/api/call", { tool, arguments: args });
  activityEntry({ tool, http_status: r.http_status, decision: r.decision, text: r.text, request, response: r.response });
  showTab("activity");
}

async function closeSession() {
  const claim = await api("/api/close", {});
  if (claim.error) {
    $("#record").textContent = claim.error;
    showTab("record");
    return;
  }
  $("#record").textContent = JSON.stringify(claim, null, 2);
  $("#verify").disabled = false;
  showTab("record");
}

async function verifyRecord() {
  const v = await api("/api/verify", {});
  if (v.error) { $("#verify-raw").textContent = v.error; showTab("verify"); return; }
  $("#verify-checks").innerHTML = (v.checks || []).map((c) => {
    const pass = c.status === "PASS";
    return `<div class="check ${pass ? "pass" : "fail"}">
      <span class="box">${pass ? "✓" : "✗"}</span>
      <span class="name">${c.name}</span><span class="st">${c.status}</span></div>`;
  }).join("");
  if (v.result) {
    const verified = v.result.status.toLowerCase() === "pass" || v.result.detail === "verified";
    const div = document.createElement("div");
    div.className = "result " + (verified ? "verified" : "partial");
    div.innerHTML = `<span class="status">${v.result.detail}</span> &mdash; software-only run; on real TDX / SEV-SNP the hardware check verifies too.`;
    $("#verify-checks").appendChild(div);
  }
  $("#verify-raw").textContent = v.raw || "";
  showTab("verify");
}

async function reset() {
  await api("/api/reset", {});
  $("#activity").innerHTML = "";
  $("#activity-empty").style.display = "";
  $("#record").textContent = "Close the session to produce a record.";
  $("#verify-checks").innerHTML = "";
  $("#verify-raw").textContent = "Verify a record to see the result.";
  $("#verify").disabled = true;
  showTab("activity");
}

function showTab(name) {
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.dataset.panel === name));
  document.querySelectorAll(".panel").forEach((p) => p.classList.toggle("active", p.id === "panel-" + name));
}

document.querySelectorAll(".run").forEach((b) => b.addEventListener("click", () => sendCall(b.dataset.tool)));
document.querySelectorAll(".tab").forEach((t) => t.addEventListener("click", () => showTab(t.dataset.panel)));
$("#close").addEventListener("click", closeSession);
$("#verify").addEventListener("click", verifyRecord);
$("#reset").addEventListener("click", reset);

loadPolicy();
