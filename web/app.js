const $ = (selector) => document.querySelector(selector);
const fetchJson = async (url, options) => {
  const response = await fetch(url, options);
  const payload = await response.json();
  if (!response.ok) throw new Error(payload.error || "Nao foi possivel concluir.");
  return payload;
};
const toast = (text) => {
  $("#toast").textContent = text; $("#toast").classList.add("show");
  setTimeout(() => $("#toast").classList.remove("show"), 3500);
};
const setBaseProgress = (percent, text) => {
  const value = Math.max(0, Math.min(100, Math.round(percent)));
  $("#base-progress").style.width = `${value}%`;
  $("#base-progress-label").textContent = `${value}%`;
  $("#base-loading-text").textContent = text;
};
const showBaseProgress = () => {
  setBaseProgress(0, "Preparando arquivo...");
  $("#base-loading").classList.remove("hidden");
};
const hideBaseProgress = () => $("#base-loading").classList.add("hidden");
const uploadBase = (form) => new Promise((resolve, reject) => {
  const request = new XMLHttpRequest();
  request.open("POST", "/api/import");
  request.upload.addEventListener("progress", event => {
    if (event.lengthComputable) setBaseProgress(event.loaded / event.total * 85, "Enviando planilha...");
  });
  request.upload.addEventListener("load", () => setBaseProgress(90, "Processando dados da planilha..."));
  request.addEventListener("load", () => {
    let payload = {};
    try { payload = JSON.parse(request.responseText || "{}"); }
    catch { return reject(new Error("Resposta invalida do servidor.")); }
    if (request.status < 200 || request.status >= 300) return reject(new Error(payload.error || "Nao foi possivel concluir."));
    setBaseProgress(100, "Base diaria carregada.");
    resolve(payload);
  });
  request.addEventListener("error", () => reject(new Error("Falha ao enviar a planilha.")));
  request.send(new FormData(form));
});
const table = (rows, columns) => {
  if (!rows.length) return "<p>Nenhum registro disponivel.</p>";
  return `<table><thead><tr>${columns.map(c => `<th>${c[1]}</th>`).join("")}</tr></thead><tbody>${
    rows.map(row => `<tr>${columns.map(([key]) => `<td>${key === "status" ? `<span class="badge ${row[key]}">${row[key]}</span>` : (row[key] ?? "")}</td>`).join("")}</tr>`).join("")
  }</tbody></table>`;
};
async function refresh() {
  const [dashboard, imports, shelf, runs, validations] = await Promise.all([
    fetchJson("/api/dashboard"), fetchJson("/api/imports"), fetchJson("/api/shelf"),
    fetchJson("/api/runs"), fetchJson("/api/validations")
  ]);
  $("#metrics").innerHTML = [
    ["Processamentos", dashboard.runs], ["Itens conferidos", dashboard.items],
    ["Itens aprovados", dashboard.approved], ["Assertividade", `${dashboard.accuracy}%`]
  ].map(([name,value]) => `<div class="card metric"><span>${name}</span><strong>${value}</strong></div>`).join("");
  const max = Math.max(...dashboard.errors.map(e => e.count), 1);
  $("#errors").innerHTML = dashboard.errors.length ? dashboard.errors.map(e =>
    `<div class="bar-row"><span>${e.name}</span><div class="bar"><i style="width:${e.count/max*100}%"></i></div><b>${e.count}</b></div>`
  ).join("") : "<p>Nenhuma divergencia registrada.</p>";
  $("#imports").innerHTML = table(imports, [["id","ID"],["base_type","Base"],["filename","Arquivo"],["imported_at","Importado em"],["row_count","Linhas"]]);
  $("#shelf-table").innerHTML = table(shelf, [["cliente","Destino / CNPJ"],["cliente_nome","Cliente"],["shelf_minimo","Shelf minimo"],["updated_at","Atualizado em"]]);
  $("#runs").innerHTML = table(runs, [["id","ID"],["created_at","Executado em"],["filename","Arquivo"],["remessa","Remessa identificada"],["status","Status"],["approved_items","Aprovados"],["total_items","Itens"],["unidentified_items","Sem produto"]]);
  $("#validations").innerHTML = table(validations, [["run_id","Execucao"],["data_embarque","Data embarque"],["remessa","Remessa"],["cliente","Cliente"],["palete","Palete"],["produto","Material"],["lote","Lote"],["validade","Validade"],["shelf_percentual","Shelf embarcado"],["shelf_minimo","Shelf minimo"],["bloqueio_status","Bloqueio"],["status","Status"],["errors","Divergencias"]]);
}
document.querySelectorAll(".tab").forEach(button => button.addEventListener("click", () => {
  document.querySelectorAll(".tab,.panel").forEach(el => el.classList.remove("active"));
  button.classList.add("active"); $(`#${button.dataset.tab}`).classList.add("active");
}));
$("#base-form").addEventListener("submit", async event => {
  event.preventDefault();
  showBaseProgress();
  try {
    await uploadBase(event.target);
    toast("Base importada com sucesso."); event.target.reset(); await refresh();
    setTimeout(hideBaseProgress, 450);
  } catch (error) { hideBaseProgress(); toast(error.message); }
});
$("#clear-base").addEventListener("click", async () => {
  const baseType = $("#base-form select[name=base_type]").value;
  const label = $("#base-form select[name=base_type] option:checked").textContent;
  if (!confirm(`Remover a base vigente de "${label}"?`)) return;
  try {
    const result = await fetchJson("/api/clear-base", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body:JSON.stringify({base_type:baseType})
    });
    toast(result.removed ? "Base vigente removida." : "Nenhuma base vigente encontrada.");
    await refresh();
  } catch (error) { toast(error.message); }
});
$("#shelf-form").addEventListener("submit", async event => {
  event.preventDefault();
  const data = Object.fromEntries(new FormData(event.target));
  try { await fetchJson("/api/shelf", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(data)}); toast("Parametro atualizado."); event.target.reset(); await refresh(); }
  catch (error) { toast(error.message); }
});
$("#process-form").addEventListener("submit", async event => {
  event.preventDefault();
  try {
    const result = await fetchJson("/api/process", {method:"POST", body:new FormData(event.target)});
    $("#process-result").classList.remove("hidden");
    $("#process-result").innerHTML = `<h2>Conferencia concluida</h2><p>${result.length} arquivo(s) processado(s). Consulte a aba Historico para ver os itens.</p>`;
    toast("Arquivos processados."); event.target.reset(); await refresh();
  } catch (error) { toast(error.message); }
});
refresh().catch(error => toast(error.message));
