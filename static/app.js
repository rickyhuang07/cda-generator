const fileInput = document.getElementById("file");
const dropzone = document.getElementById("dropzone");
const filenameEl = document.getElementById("filename");
const previewCard = document.getElementById("preview-card");
const warningsEl = document.getElementById("warnings");
const generateBtn = document.getElementById("generate");

const FIELDS = [
  "property_address",
  "close_date",
  "sale_price",
  "mls",
  "seller",
  "buyer",
  "selling_agent",
  "closer",
  "title_company",
  "closer_phone",
  "closer_email",
  "escrow_no",
  "today",
  "broker_process_fees",
  "selling_agent_commission",
  "agent_payee_address",
  "broker_name",
  "brokerage_mail_address",
];

let currentFile = null;

function overridesFromForm() {
  const data = {};
  for (const id of FIELDS) {
    data[id] = document.getElementById(id).value;
  }
  return data;
}

function fillPreview(data) {
  for (const id of FIELDS) {
    if (data[id] !== undefined && data[id] !== null) {
      document.getElementById(id).value = data[id];
    }
  }
  document.getElementById("gross_display").value = data.gross_commission_fmt || "";
  warningsEl.textContent = (data.warnings || []).join(" ");
  previewCard.classList.remove("hidden");
}

async defPreview() {
  if (!currentFile) return;
  const body = new FormData();
  body.append("file", currentFile);
  body.append("overrides", "{}");
  const res = await fetch("/api/preview", { method: "POST", body });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Could not parse worksheet." }));
    alert(err.detail || "Could not parse worksheet.");
    return;
  }
  fillPreview(await res.json());
}

fileInput.addEventListener("change", () => {
  currentFile = fileInput.files[0];
  filenameEl.textContent = currentFile ? currentFile.name : "";
  defPreview();
});

["dragenter", "dragover"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("drag");
  });
});
["dragleave", "drop"].forEach((evt) => {
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag");
  });
});
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (!file) return;
  currentFile = file;
  filenameEl.textContent = file.name;
  defPreview();
});

generateBtn.addEventListener("click", async () => {
  if (!currentFile) return;
  const body = new FormData();
  body.append("file", currentFile);
  body.append("overrides", JSON.stringify(overridesFromForm()));
  const res = await fetch("/api/generate", { method: "POST", body });
  if (!res.ok) {
    alert("Could not generate PDF.");
    return;
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  const header = res.headers.get("content-disposition") || "";
  const match = header.match(/filename="([^"]+)"/);
  a.download = match ? match[1] : "CDA.pdf";
  a.click();
  URL.revokeObjectURL(url);
});
