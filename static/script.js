const updateBtn = document.getElementById("update-btn");
const promptInput = document.getElementById("prompt-input");
const diagramPreview = document.getElementById("diagram-preview");
const statusMessage = document.getElementById("status-message");
const viewHistoryBtn = document.getElementById("view-history-btn");
const historyList = document.getElementById("history-list");
const zoomInBtn = document.getElementById("zoom-in");
const zoomOutBtn = document.getElementById("zoom-out");

let history = [];

function updateHistory(changePrompt) {
  history.push(changePrompt);
  const historyItem = document.createElement("p");
  historyItem.textContent = changePrompt;
  historyList.appendChild(historyItem);
}

updateBtn.addEventListener("click", async () => {
  const changePrompt = promptInput.value.trim();

  if (!changePrompt) {
    alert("Please enter a prompt.");
    return;
  }

  statusMessage.textContent = "Loading...";
  try {
    const response = await fetch("http://localhost:8000/iterative-mermaid", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ prompt: changePrompt }),
    });

    if (response.ok) {
      const data = await response.json();
      diagramPreview.src = `/output/${data.filename}`;
      statusMessage.textContent = "Diagram updated successfully!";
      updateHistory(changePrompt);
    } else {
      statusMessage.textContent = "Error updating diagram.";
    }
  } catch (error) {
    statusMessage.textContent = `Error: ${error.message}`;
  }

  promptInput.value = "";
});

viewHistoryBtn.addEventListener("mouseover", () => {
  historyList.classList.toggle("hidden");
});

let zoomLevel = 1;
zoomInBtn.addEventListener("click", () => {
  zoomLevel += 0.1;
  diagramPreview.style.transform = `scale(${zoomLevel})`;
});
zoomOutBtn.addEventListener("click", () => {
  zoomLevel = Math.max(0.1, zoomLevel - 0.1);
  diagramPreview.style.transform = `scale(${zoomLevel})`;
});
