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
  try { await fetchJson("/api/import", {method:"POST", body:new FormData(event.target)}); toast("Base importada com sucesso."); event.target.reset(); await refresh(); }
  catch (error) { toast(error.message); }
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
