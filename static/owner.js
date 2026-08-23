document.addEventListener("DOMContentLoaded", () => {
  const list = document.getElementById("submission-list");
  const detail = document.getElementById("detail");
  const empty = document.getElementById("empty-detail");
  const generate = document.getElementById("generate");
  const deleteButton = document.getElementById("delete");
  const message = document.getElementById("owner-message");
  const loginCard = document.getElementById("login-card");
  const ownerContent = document.getElementById("owner-content");
  const loginForm = document.getElementById("login-form");
  const loginMessage = document.getElementById("login-message");
  const reviewFields = [
    ["closer", "Escrow Agent"],
    ["closer_email", "Escrow Agent's Email"],
    ["closer_phone", "Escrow Agent's Phone"],
    ["title_company", "Title Company"],
    ["title_company_address", "Title Company Address"],
    ["escrow_no", "Escrow Number"],
    ["gross_commission", "Gross Commission"],
    ["mls", "MLS"],
    ["sale_price", "Sale Price"],
    ["property_address", "Property Address"],
    ["buyer", "Buyer / Tenant"],
    ["close_date", "Close Date"],
    ["seller", "Seller / Landlord"],
    ["selling_agent", "Selling Agent"],
    ["broker_process_fees", "Broker Process Fees"],
    ["selling_agent_commission", "Agent Commission"],
    ["agent_payee_address", "Agent Payee Mailing Address"],
  ];
  let selectedId = null;

  async function loadSubmissions() {
    const response = await fetch("/api/submissions");
    if (response.status === 401) return false;
    const submissions = await response.json();
    list.innerHTML = submissions.length ? "" : '<p class="hint">No submissions yet.</p>';
    submissions.forEach((submission) => {
      const button = document.createElement("button");
      button.className = "submission-item";
      button.type = "button";
      const title = document.createElement("strong");
      title.textContent = submission.overrides.property_address || "Untitled submission";
      const metadata = document.createElement("span");
      metadata.textContent = `${submission.created_at} - ${submission.status}`;
      button.append(title, metadata);
      button.addEventListener("click", () => selectSubmission(submission.id));
      list.appendChild(button);
    });
    return true;
  }

  async function selectSubmission(id) {
    const response = await fetch(`/api/submissions/${id}`);
    const data = await response.json();
    selectedId = id;
    empty.classList.add("hidden");
    detail.classList.remove("hidden");
    detail.replaceChildren();
    reviewFields.forEach(([key, labelText]) => {
        const value = data.preview[key];
        const item = document.createElement("div");
        const label = document.createElement("span");
        label.textContent = labelText;
        const content = document.createElement("strong");
        content.textContent = value ?? "";
        item.append(label, content);
        detail.appendChild(item);
      });
    generate.disabled = false;
    deleteButton.disabled = false;
  }

  document.getElementById("refresh").addEventListener("click", loadSubmissions);
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = new FormData();
    body.append("password", document.getElementById("owner-password").value);
    const response = await fetch("/api/owner/login", { method: "POST", body });
    if (!response.ok) { loginMessage.textContent = "Invalid password."; return; }
    loginCard.classList.add("hidden");
    ownerContent.classList.remove("hidden");
    await loadSubmissions();
  });
  document.getElementById("logout").addEventListener("click", async () => {
    await fetch("/api/owner/logout", { method: "POST" });
    ownerContent.classList.add("hidden");
    loginCard.classList.remove("hidden");
  });
  deleteButton.addEventListener("click", async () => {
    if (!selectedId || !window.confirm("Delete this submission permanently?")) return;
    deleteButton.disabled = true;
    const response = await fetch(`/api/submissions/${selectedId}`, { method: "DELETE" });
    if (!response.ok) {
      message.textContent = "Could not delete submission.";
      deleteButton.disabled = false;
      return;
    }
    selectedId = null;
    detail.replaceChildren();
    detail.classList.add("hidden");
    empty.classList.remove("hidden");
    generate.disabled = true;
    message.textContent = "Submission deleted.";
    await loadSubmissions();
  });
  generate.addEventListener("click", async () => {
    if (!selectedId) return;
    generate.disabled = true;
    const response = await fetch(`/api/submissions/${selectedId}/generate`, { method: "POST" });
    if (!response.ok) { message.textContent = "Could not generate PDF."; generate.disabled = false; return; }
    const blob = await response.blob();
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `CDA_${selectedId}.pdf`;
    link.click();
    URL.revokeObjectURL(link.href);
    message.textContent = "PDF generated.";
    generate.disabled = false;
  });
  loginCard.classList.remove("hidden");
  ownerContent.classList.add("hidden");
});