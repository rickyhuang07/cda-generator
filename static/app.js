document.addEventListener("DOMContentLoaded", () => {
  const dropzone = document.getElementById("dropzone");
  const fileInput = document.getElementById("file");
  const filenameEl = document.getElementById("filename");
  const previewCard = document.getElementById("preview-card");
  const generateBtn = document.getElementById("generate");
  const warningsEl = document.getElementById("warnings");

  // List of inputs editable in the form
  const fieldIds = [
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

  // 1. Prevent browser default drop behaviors
  ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(
      eventName,
      (e) => {
        e.preventDefault();
        e.stopPropagation();
      },
      false
    );
  });

  // 2. Visual feedback on drag hover
  ["dragenter", "dragover"].forEach((eventName) => {
    dropzone.addEventListener(eventName, () => dropzone.classList.add("hover"), false);
  });

  ["dragleave", "drop"].forEach((eventName) => {
    dropzone.addEventListener(eventName, () => dropzone.classList.remove("hover"), false);
  });

  // 3. Handle file drop
  dropzone.addEventListener("drop", (e) => {
    const dt = e.dataTransfer;
    const files = dt.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  });

  // 4. Handle manual file selection via click
  dropzone.addEventListener("click", (e) => {
    if (e.target !== fileInput) {
      fileInput.click();
    }
  });

  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  });

  // 5. Send file to /api/preview
  async function handleFile(file) {
    if (!file.name.match(/\.(xlsx|xlsm)$/i)) {
      alert("Please upload an Excel file (.xlsx or .xlsm)");
      return;
    }

    currentFile = file;
    filenameEl.textContent = `Selected: ${file.name}`;

    const formData = new FormData();
    formData.append("file", file);
    formData.append("overrides", "{}");

    try {
      const response = await fetch("/api/preview", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Error parsing file");
      }

      const data = await response.json();
      populateForm(data);
    } catch (err) {
      alert(`Upload failed: ${err.message}`);
    }
  }

  // 6. Populate HTML inputs with parsed data
  function populateForm(data) {
    fieldIds.forEach((id) => {
      const input = document.getElementById(id);
      if (input) {
        input.value = data[id] !== undefined && data[id] !== null ? data[id] : "";
      }
    });

    const grossDisplay = document.getElementById("gross_display");
    if (grossDisplay) {
      grossDisplay.value = data.gross_commission_fmt || "$0.00";
    }

    if (warningsEl) {
      warningsEl.textContent =
        data.warnings && data.warnings.length > 0 ? data.warnings.join("; ") : "";
    }

    previewCard.classList.remove("hidden");
  }

  // 7. Collect overrides and request PDF from /api/generate
  generateBtn.addEventListener("click", async () => {
    if (!currentFile) {
      alert("Please upload a file first.");
      return;
    }

    const overrides = {};
    fieldIds.forEach((id) => {
      const input = document.getElementById(id);
      if (input && input.value !== "") {
        overrides[id] = input.value;
      }
    });

    const formData = new FormData();
    formData.append("file", currentFile);
    formData.append("overrides", JSON.stringify(overrides));

    try {
      generateBtn.disabled = true;
      generateBtn.textContent = "Generating PDF...";

      const response = await fetch("/api/generate", {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        throw new Error("Failed to generate PDF");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;

      const disposition = response.headers.get("content-disposition");
      let filename = "CDA.pdf";
      if (disposition && disposition.includes("filename=")) {
        filename = disposition.split("filename=")[1].replace(/"/g, "");
      }
      a.download = filename;

      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      alert(`Error: ${err.message}`);
    } finally {
      generateBtn.disabled = false;
      generateBtn.textContent = "Download CDA PDF";
    }
  });
});