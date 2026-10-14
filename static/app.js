const input = document.querySelector("#message-input");
const sendButton = document.querySelector("#send-button");
const messages = document.querySelector("#messages");
const welcome = document.querySelector("#welcome");
const scrollArea = document.querySelector("#chat-scroll");
const charCount = document.querySelector("#char-count");
let requestPending = false;
let requestVersion = 0;
let conversationHistory = [];

function scrollToBottom() {
  scrollArea.scrollTo({ top: scrollArea.scrollHeight, behavior: "smooth" });
}

function addMessage(role, text, response) {
  const row = document.createElement("article");
  row.className = `message-row ${role}`;

  if (role === "assistant") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = "✳";
    row.append(avatar);
  }

  const content = document.createElement("div");
  content.className = "message-content";
  const label = document.createElement("div");
  label.className = "message-label";
  label.textContent = role === "user" ? "YOU" : response?.topic || "BUDDY";

  if (role === "assistant" && response && response.safety_level !== "general") {
    const banner = document.createElement("div");
    banner.className = `safety-banner ${response.safety_level}`;
    banner.textContent = response.safety_level === "emergency"
      ? "If you may be in immediate danger, contact local emergency services now."
      : "For your safety, please check with a healthcare professional before acting.";
    content.append(banner);
  }

  content.append(label);
  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.textContent = text;
  content.append(bubble);

  if (role === "assistant" && response?.sources?.length) {
    const sourceList = document.createElement("div");
    sourceList.className = "message-meta";
    for (const source of response.sources) {
      const link = document.createElement("a");
      link.className = "source-link";
      link.href = source.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = source.title;
      sourceList.append(link);
    }
    content.append(sourceList);
  }

  if (role === "assistant" && response?.suggestions?.length) {
    const suggestions = document.createElement("div");
    suggestions.className = "message-meta";
    for (const suggestion of response.suggestions) {
      const button = document.createElement("button");
      button.className = "chat-suggestion";
      button.type = "button";
      button.textContent = suggestion;
      button.addEventListener("click", () => {
        sendMessage(response.retryMessage || suggestion);
      });
      suggestions.append(button);
    }
    content.append(suggestions);
  }

  row.append(content);
  if (role === "user") {
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.setAttribute("aria-hidden", "true");
    avatar.textContent = "You";
    row.append(avatar);
  }
  messages.append(row);
  scrollToBottom();
}

function showTyping() {
  const row = document.createElement("div");
  row.className = "message-row";
  row.id = "typing-indicator";
  const avatar = document.createElement("div");
  avatar.className = "avatar";
  avatar.textContent = "✳";
  const dots = document.createElement("div");
  dots.className = "bubble typing";
  dots.setAttribute("aria-label", "Buddy is thinking");
  dots.innerHTML = "<span></span><span></span><span></span>";
  row.append(avatar, dots);
  messages.append(row);
  scrollToBottom();
}

function resizeInput() {
  input.style.height = "auto";
  input.style.height = `${Math.min(input.scrollHeight, 115)}px`;
  sendButton.disabled = requestPending || input.value.trim().length === 0;
  charCount.textContent = `${input.value.length} / 2000`;
}

async function sendMessage(value = input.value) {
  const message = value.trim();
  if (!message || requestPending) return;
  requestPending = true;
  const currentVersion = ++requestVersion;
  const history = conversationHistory.slice(-10);
  welcome.hidden = true;
  addMessage("user", message);
  conversationHistory.push({ role: "user", content: message });
  input.value = "";
  resizeInput();
  sendButton.disabled = true;
  showTyping();

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    });
    if (!response.ok) {
      const details = await response.json().catch(() => ({}));
      throw new Error(details.detail?.[0]?.msg || "Buddy couldn't answer just now. Please try again.");
    }
    const data = await response.json();
    if (currentVersion !== requestVersion) return;
    document.querySelector("#typing-indicator")?.remove();
    addMessage("assistant", data.reply, data);
    conversationHistory.push({ role: "assistant", content: data.reply });
    conversationHistory = conversationHistory.slice(-10);
  } catch (error) {
    if (currentVersion !== requestVersion) return;
    document.querySelector("#typing-indicator")?.remove();
    const errorMessage = error instanceof TypeError
      ? "I couldn't reach the chat service. Check that the app server is running, then try again."
      : error.message || "Buddy couldn't answer just now. Please try again.";
    addMessage(
      "assistant",
      errorMessage,
      {
        topic: "Connection problem",
        safety_level: "general",
        suggestions: ["Try again"],
        retryMessage: message,
      },
    );
    conversationHistory.push({
      role: "assistant",
      content: errorMessage,
    });
    conversationHistory = conversationHistory.slice(-10);
  } finally {
    if (currentVersion === requestVersion) {
      requestPending = false;
      sendButton.disabled = input.value.trim().length === 0;
    }
  }
}

input.addEventListener("input", resizeInput);
input.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendMessage();
  }
});
sendButton.addEventListener("click", () => sendMessage());
document.querySelectorAll("[data-prompt]").forEach((button) => {
  button.addEventListener("click", () => sendMessage(button.dataset.prompt));
});
document.querySelector("#new-chat").addEventListener("click", () => {
  requestVersion += 1;
  requestPending = false;
  document.querySelector("#typing-indicator")?.remove();
  messages.replaceChildren();
  conversationHistory = [];
  welcome.hidden = false;
  input.value = "";
  resizeInput();
  input.focus();
});
