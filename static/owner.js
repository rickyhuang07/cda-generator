document.addEventListener("DOMContentLoaded", () => {
  const list = document.getElementById("submission-list");
  const detail = document.getElementById("detail");
  const empty = document.getElementById("empty-detail");
  const generate = document.getElementById("generate");
  const message = document.getElementById("owner-message");
  let selectedId = null;

  async function loadSubmissions() {
    const response = await fetch("/api/submissions");
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
  }

  async function selectSubmission(id) {
    const response = await fetch(`/api/submissions/${id}`);
    const data = await response.json();
    selectedId = id;
    empty.classList.add("hidden");
    detail.classList.remove("hidden");
    detail.replaceChildren();
    Object.entries(data.preview)
      .filter(([key]) => !key.endsWith("_fmt") && !["warnings", "_gross_commission_override"].includes(key))
      .forEach(([key, value]) => {
        const item = document.createElement("div");
        const label = document.createElement("span");
        label.textContent = key.replaceAll("_", " ");
        const content = document.createElement("strong");
        content.textContent = value ?? "";
        item.append(label, content);
        detail.appendChild(item);
      });
    generate.disabled = false;
  }

  document.getElementById("refresh").addEventListener("click", loadSubmissions);
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
  loadSubmissions().catch(() => { list.innerHTML = '<p class="message error">Could not load submissions.</p>'; });
});