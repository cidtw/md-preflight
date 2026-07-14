const form = document.getElementById("eval-form");
const resultEl = document.getElementById("result");

form?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const data = new FormData(form);
  const parameters = {
    quality: Number(data.get("quality")),
    cost: Number(data.get("cost")),
    risk: Number(data.get("risk")),
  };

  resultEl.hidden = false;
  resultEl.textContent = "Running…";

  try {
    const response = await fetch("/api/evaluate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ parameters }),
    });
    const payload = await response.json();
    if (!response.ok) {
      resultEl.textContent = JSON.stringify(payload, null, 2);
      return;
    }
    resultEl.textContent = [
      payload.recommendation,
      "",
      `band: ${payload.band}`,
      `score: ${payload.score}`,
      "",
      JSON.stringify(payload.details, null, 2),
    ].join("\n");
  } catch (error) {
    resultEl.textContent = String(error);
  }
});
