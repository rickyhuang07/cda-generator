document.addEventListener("DOMContentLoaded", () => {
  const fileInput = document.getElementById("file");
  const filenameEl = document.getElementById("filename");
  const form = document.getElementById("submission-form");
  const messageEl = document.getElementById("message");
  const fieldIds = ["closer", "closer_email", "closer_phone", "title_company", "title_company_address", "escrow_no", "gross_commission", "mls", "sale_price", "property_address", "buyer", "close_date", "seller", "selling_agent", "broker_process_fees", "selling_agent_commission", "agent_payee_address"];
  let currentFile = null;

  fileInput.addEventListener("change", async () => {
    currentFile = fileInput.files[0] || null;
    filenameEl.textContent = currentFile ? `Attached: ${currentFile.name}` : "";
    if (!currentFile) return;
    const formData = new FormData();
    formData.append("file", currentFile);
    try {
      const response = await fetch("/api/preview", { method: "POST", body: formData });
      if (!response.ok) throw new Error(await responseError(response, "Could not read worksheet"));
      populateForm(await response.json());
      showMessage("Worksheet read. Review the details before submitting.", "success");
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  async function responseError(response, fallback) {
    const text = await response.text();
    try {
      const data = JSON.parse(text);
      return data.detail || fallback;
    } catch {
      return text.replace(/<[^>]*>/g, "").trim() || `${fallback} (${response.status})`;
    }
  }

  function populateForm(data) {
    fieldIds.forEach((id) => {
      const input = document.getElementById(id);
      if (input) input.value = data[id] ?? "";
    });
  }

  function showMessage(text, kind = "") {
    messageEl.textContent = text;
    messageEl.className = `message ${kind}`;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const values = {};
    fieldIds.forEach((id) => { values[id] = document.getElementById(id).value; });
    const formData = new FormData();
    if (currentFile) formData.append("file", currentFile);
    formData.append("overrides", JSON.stringify(values));
    const button = form.querySelector("button[type=submit]");
    button.disabled = true;
    try {
      const response = await fetch("/api/submissions", { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Could not submit form");
      form.reset();
      currentFile = null;
      filenameEl.textContent = "";
      showMessage("Submitted. The owner will review your information and generate the CDA.", "success");
    } catch (error) {
      showMessage(error.message, "error");
    } finally {
      button.disabled = false;
    }
  });
});