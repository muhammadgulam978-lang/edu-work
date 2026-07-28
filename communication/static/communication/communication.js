(function () {
  "use strict";
  const page = document.querySelector(".communication-page");
  if (!page) return;

  const csrf = document.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
  const messageList = document.getElementById("message-list");
  const messageForm = document.getElementById("message-form");
  const errorBox = document.getElementById("message-error");
  const pollUrl = page.dataset.pollUrl;
  const sendUrl = page.dataset.sendUrl;
  let lastMessageId = Number(
    messageList?.querySelector("[data-message-id]:last-of-type")?.dataset.messageId || 0
  );
  let pollController = null;

  function escapeHtml(value) {
    const node = document.createElement("div");
    node.textContent = value || "";
    return node.innerHTML;
  }

  function messageMarkup(message) {
    const attachment = message.attachment_url
      ? `<a class="communication-attachment" href="${escapeHtml(message.attachment_url)}" target="_blank" rel="noopener"><i class="fas fa-paperclip"></i> ${escapeHtml(message.attachment_name)}</a>`
      : "";
    return `<article class="communication-message ${message.mine ? "is-mine" : ""}" data-message-id="${message.id}">
      <div class="communication-bubble ${message.deleted ? "is-deleted" : ""}">
        ${message.mine ? "" : `<strong>${escapeHtml(message.sender)}</strong>`}
        <p>${escapeHtml(message.content)}</p>${attachment}
      </div>
      <footer><time>${new Date(message.created_at).toLocaleString()}</time>
        ${message.edited ? "<span>Edited</span>" : ""}
        ${message.mine ? `<span>${escapeHtml(message.status)}</span>` : ""}
        ${message.pinned ? '<i class="fas fa-star" title="Pinned"></i>' : ""}
        ${message.deleted ? "" : `<button type="button" data-message-action="react" data-emoji="👍" title="React">👍</button>
          <button type="button" data-message-action="pin" title="Pin message" aria-label="Pin message"><i class="fas fa-thumbtack" aria-hidden="true"></i></button>
          ${message.mine ? '<button type="button" data-message-action="delete" title="Delete message" aria-label="Delete message"><i class="fas fa-trash-alt" aria-hidden="true"></i></button>' : ""}`}
      </footer></article>`;
  }

  function appendMessage(message) {
    if (!messageList || messageList.querySelector(`[data-message-id="${message.id}"]`)) return;
    document.getElementById("empty-chat")?.remove();
    messageList.insertAdjacentHTML("beforeend", messageMarkup(message));
    lastMessageId = Math.max(lastMessageId, Number(message.id));
    messageList.scrollTop = messageList.scrollHeight;
  }

  async function post(url, body) {
    const response = await fetch(url, {
      method: "POST",
      headers: { "X-CSRFToken": csrf, "X-Requested-With": "XMLHttpRequest" },
      body,
      credentials: "same-origin",
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Request failed.");
    return data;
  }

  messageForm?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const submit = messageForm.querySelector('[type="submit"]');
    submit.disabled = true;
    errorBox.hidden = true;
    try {
      const data = await post(sendUrl, new FormData(messageForm));
      appendMessage(data.message);
      messageForm.reset();
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    } finally {
      submit.disabled = false;
    }
  });

  async function poll() {
    if (!pollUrl || document.hidden) return;
    pollController?.abort();
    pollController = new AbortController();
    try {
      const response = await fetch(`${pollUrl}?after=${lastMessageId}`, {
        signal: pollController.signal,
        credentials: "same-origin",
      });
      if (!response.ok) return;
      const data = await response.json();
      data.messages.forEach(appendMessage);
    } catch (error) {
      if (error.name !== "AbortError") console.debug("Communication refresh delayed.");
    }
  }

  messageList?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-message-action]");
    if (!button) return;
    const article = button.closest("[data-message-id]");
    const id = article.dataset.messageId;
    const url = page.dataset.actionTemplate.replace("/0/", `/${id}/`);
    const body = new FormData();
    body.append("action", button.dataset.messageAction);
    if (button.dataset.emoji) body.append("emoji", button.dataset.emoji);
    try {
      const data = await post(url, body);
      article.outerHTML = messageMarkup(data.message);
    } catch (error) {
      errorBox.textContent = error.message;
      errorBox.hidden = false;
    }
  });

  document.querySelectorAll("[data-conversation-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const body = new FormData();
      body.append("action", button.dataset.conversationAction);
      const url = `/communication/conversations/${page.dataset.activeConversation}/setting/`;
      if (button.dataset.conversationAction === "block" && !confirm("Block this user?")) return;
      await post(url, body);
      if (button.dataset.conversationAction === "archive") location.href = "/communication/";
    });
  });

  document.getElementById("conversation-search")?.addEventListener("input", (event) => {
    const query = event.target.value.trim().toLowerCase();
    document.querySelectorAll(".communication-conversation").forEach((item) => {
      item.hidden = !item.dataset.conversationName.includes(query);
    });
  });

  const recipientSearch = document.getElementById("recipient-search");
  const recipientSelect = document.getElementById("recipient-select");
  const recipientCount = document.getElementById("recipient-search-count");
  if (recipientSearch && recipientSelect && recipientCount) {
    const contacts = Array.from(recipientSelect.options)
      .slice(1)
      .map((option) => ({
        value: option.value,
        label: option.textContent.trim(),
        search: option.dataset.search || option.textContent.toLowerCase(),
      }));

    function filterRecipients() {
      const query = recipientSearch.value.trim().toLowerCase();
      const selected = recipientSelect.value;
      const matches = contacts.filter((contact) => contact.search.includes(query));
      recipientSelect.replaceChildren(new Option("Select a permitted contact", ""));
      matches.forEach((contact) => {
        const option = new Option(contact.label, contact.value);
        option.dataset.search = contact.search;
        recipientSelect.add(option);
      });
      if (matches.some((contact) => contact.value === selected)) {
        recipientSelect.value = selected;
      }
      if (!matches.length) {
        const empty = new Option("No permitted contacts found", "");
        empty.disabled = true;
        recipientSelect.add(empty);
      }
      recipientCount.textContent =
        `${matches.length} permitted contact${matches.length === 1 ? "" : "s"}`;
    }

    recipientSearch.addEventListener("input", filterRecipients);
    recipientSearch.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        if (recipientSelect.options.length === 2) {
          recipientSelect.selectedIndex = 1;
          recipientSelect.focus();
        }
      }
    });
  }

  document.querySelectorAll("[data-open-dialog]").forEach((button) => {
    button.addEventListener("click", () => {
      document.getElementById(button.dataset.openDialog)?.showModal();
    });
  });
  document.querySelectorAll("[data-close-dialog]").forEach((button) => {
    button.addEventListener("click", () => button.closest("dialog")?.close());
  });

  async function heartbeat(online) {
    const body = new FormData();
    body.append("online", String(online));
    try { await post(page.dataset.heartbeatUrl, body); } catch (_) {}
  }
  heartbeat(true);
  window.addEventListener("beforeunload", () => {
    navigator.sendBeacon(
      page.dataset.heartbeatUrl,
      new URLSearchParams({ online: "false", csrfmiddlewaretoken: csrf })
    );
  });
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) { heartbeat(true); poll(); }
  });
  if (messageList) messageList.scrollTop = messageList.scrollHeight;
  setInterval(poll, 3000);
})();
