const state = {
  lastTranslation: "",
};

const elements = {
  direction: document.querySelector("#direction"),
  toneLevel: document.querySelector("#toneLevel"),
  explainSlang: document.querySelector("#explainSlang"),
  translateButton: document.querySelector("#translateButton"),
  copyButton: document.querySelector("#copyButton"),
  inputText: document.querySelector("#inputText"),
  outputText: document.querySelector("#outputText"),
  message: document.querySelector("#message"),
  charCount: document.querySelector("#charCount"),
  healthBadge: document.querySelector("#healthBadge"),
};

document.addEventListener("DOMContentLoaded", () => {
  elements.outputText.classList.add("placeholder");
  bindEvents();
  updateCharCount();
  checkHealth();
});

function bindEvents() {
  elements.translateButton.addEventListener("click", handleTranslate);
  elements.copyButton.addEventListener("click", copyTranslation);
  elements.inputText.addEventListener("input", updateCharCount);

  document.querySelectorAll("[data-example]").forEach((button) => {
    button.addEventListener("click", () => {
      elements.inputText.value = button.dataset.example;
      updateCharCount();
      setMessage("");
      elements.inputText.focus();
    });
  });
}

async function checkHealth() {
  try {
    const response = await fetch("/health");
    const data = await response.json();

    elements.healthBadge.textContent = data.ok ? `Ready: ${data.model}` : "Model needs attention";
    elements.healthBadge.classList.toggle("ok", data.ok);
    elements.healthBadge.classList.toggle("warn", !data.ok);

    if (!data.ok) {
      setMessage(data.message, "error");
    }
  } catch {
    elements.healthBadge.textContent = "Backend unavailable";
    elements.healthBadge.classList.add("warn");
    setMessage("The backend is not reachable. Start the FastAPI server and refresh the page.", "error");
  }
}

async function handleTranslate() {
  const text = elements.inputText.value.trim();

  if (!text) {
    setMessage("Paste or type something first.", "error");
    elements.inputText.focus();
    return;
  }

  setLoading(true);
  setMessage("");
  setOutput("Translating locally...", true);

  try {
    const response = await fetch("/translate", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        text,
        direction: elements.direction.value,
        tone_level: elements.toneLevel.value,
        explain_slang: elements.explainSlang.checked,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(data.detail || "Translation failed. Please try again.");
    }

    state.lastTranslation = data.translation;
    setOutput(data.translation);
    elements.copyButton.disabled = false;
    setMessage(`Translated with ${data.model}.`, "success");
  } catch (error) {
    state.lastTranslation = "";
    elements.copyButton.disabled = true;
    setOutput("Your translation will appear here.", true);
    setMessage(friendlyError(error), "error");
  } finally {
    setLoading(false);
  }
}

async function copyTranslation() {
  if (!state.lastTranslation) {
    return;
  }

  try {
    await navigator.clipboard.writeText(state.lastTranslation);
    setMessage("Copied to clipboard.", "success");
  } catch {
    setMessage("Copy failed. Select the output text and copy it manually.", "error");
  }
}

function setLoading(isLoading) {
  elements.translateButton.disabled = isLoading;
  elements.translateButton.classList.toggle("is-loading", isLoading);
}

function setOutput(text, isPlaceholder = false) {
  elements.outputText.textContent = text;
  elements.outputText.classList.toggle("placeholder", isPlaceholder);
}

function setMessage(text, type = "") {
  elements.message.textContent = text;
  elements.message.className = type ? `message ${type}` : "message";
}

function updateCharCount() {
  const length = elements.inputText.value.length;
  elements.charCount.textContent = `${length} / 6000`;
}

function friendlyError(error) {
  const message = error?.message || "";

  if (message.toLowerCase().includes("ollama")) {
    return message;
  }

  if (message.toLowerCase().includes("model")) {
    return message;
  }

  return message || "Something went wrong while translating. Check that Ollama and the backend are running.";
}
