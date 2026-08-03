(function () {
  "use strict";
  const page = document.querySelector(".communication-page");
  if (!page) return;

  const csrf = document.querySelector('[name="csrfmiddlewaretoken"]')?.value || "";
  const messageList = document.getElementById("message-list");
  const messageForm = document.getElementById("message-form");
  const textarea = messageForm?.querySelector('textarea[name="content"]');
  const errorBox = document.getElementById("message-error");
  const pollUrl = page.dataset.pollUrl;
  const sendUrl = page.dataset.sendUrl;
  const activeConversation = page.dataset.activeConversation;
  const draftKey = activeConversation ? `communication-draft-${activeConversation}` : "";
  let lastMessageId = Number(
    messageList?.querySelector("[data-message-id]:last-of-type")?.dataset.messageId || 0
  );
  let pollController = null;
  let socket = null;
  let reconnectTimer = null;
  let typingTimer = null;

  function escapeHtml(value) {
    const node = document.createElement("div");
    node.textContent = value || "";
    return node.innerHTML;
  }

  function contextMarkup(message) {
    const reply = message.reply_to
      ? `<aside class="communication-reply-context"><strong>${escapeHtml(message.reply_to.sender)}</strong><span>${escapeHtml(message.reply_to.content)}</span></aside>`
      : "";
    const forwarded = message.forwarded_from
      ? '<small class="communication-forwarded"><i class="fas fa-share"></i> Forwarded</small>'
      : "";
    return reply + forwarded;
  }

  function actionMarkup(message) {
    if (message.deleted) return "";
    return `<button type="button" data-message-action="react" data-emoji="👍" title="React">👍</button>
      <button type="button" data-message-action="reply" title="Reply" aria-label="Reply"><i class="fas fa-reply"></i></button>
      <button type="button" data-message-action="copy" title="Copy message" aria-label="Copy message"><i class="fas fa-copy"></i></button>
      <button type="button" data-message-action="forward-open" title="Forward message" aria-label="Forward message"><i class="fas fa-share"></i></button>
      <button type="button" data-message-action="pin" title="Pin message" aria-label="Pin message"><i class="fas fa-thumbtack"></i></button>
      ${message.mine ? '<button type="button" data-message-action="edit" title="Edit message" aria-label="Edit message"><i class="fas fa-edit"></i></button><button type="button" data-message-action="delete" title="Delete message" aria-label="Delete message"><i class="fas fa-trash-alt"></i></button>' : ""}`;
  }

  function messageMarkup(message) {
    const attachment = message.attachment_url
      ? `<a class="communication-attachment" href="${escapeHtml(message.attachment_url)}" target="_blank" rel="noopener"><i class="fas fa-paperclip"></i> ${escapeHtml(message.attachment_name)}</a>`
      : "";
    const receiptTitle = message.read_at
      ? `Read ${new Date(message.read_at).toLocaleString()}`
      : message.delivered_at
        ? `Delivered ${new Date(message.delivered_at).toLocaleString()}`
        : "";
    return `<article class="communication-message ${message.mine ? "is-mine" : ""}" data-message-id="${message.id}">
      <div class="communication-bubble ${message.deleted ? "is-deleted" : ""}">
        ${message.mine ? "" : `<strong>${escapeHtml(message.sender)}</strong>`}
        ${contextMarkup(message)}
        <p>${escapeHtml(message.content)}</p>${attachment}
      </div>
      <footer><time>${new Date(message.created_at).toLocaleString()}</time>
        ${message.edited ? "<span>Edited</span>" : ""}
        ${message.mine ? `<span data-message-status title="${escapeHtml(receiptTitle)}">${escapeHtml(message.status)}</span>` : ""}
        ${message.pinned ? '<i class="fas fa-star" title="Pinned"></i>' : ""}
        ${actionMarkup(message)}
      </footer></article>`;
  }

  function appendMessage(message) {
    if (!messageList || messageList.querySelector(`[data-message-id="${message.id}"]`)) return;
    document.getElementById("empty-chat")?.remove();
    messageList.insertAdjacentHTML("beforeend", messageMarkup(message));
    lastMessageId = Math.max(lastMessageId, Number(message.id));
    messageList.scrollTop = messageList.scrollHeight;
  }

  function showError(error) {
    if (!errorBox) return;
    errorBox.textContent = error.message || String(error);
    errorBox.hidden = false;
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

  function resetReply() {
    const replyId = document.getElementById("reply-to-id");
    if (replyId) replyId.value = "";
    const replyContext = document.getElementById("reply-context");
    if (replyContext) replyContext.hidden = true;
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
      resetReply();
      if (draftKey) localStorage.removeItem(draftKey);
      updateCharacterCount();
      sendTyping(false);
    } catch (error) {
      showError(error);
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

  function updateReceipt(event) {
    (event.message_ids || []).forEach((id) => {
      const status = messageList?.querySelector(
        `[data-message-id="${id}"] [data-message-status]`
      );
      if (status) {
        status.textContent = event.status;
        status.title = `${event.status === "READ" ? "Read" : "Delivered"} ${new Date(event.timestamp).toLocaleString()}`;
      }
    });
  }

  async function refreshConversationList() {
    if (!page.dataset.updatesUrl) return;
    const response = await fetch(page.dataset.updatesUrl, { credentials: "same-origin" });
    if (!response.ok) return;
    const data = await response.json();
    for (const conversation of data.conversations) {
      const item = document.querySelector(
        `.communication-conversation[data-conversation-id="${conversation.id}"]`
      );
      if (!item) continue;
      const preview = item.querySelector("small");
      if (preview) preview.textContent = conversation.last_message;
      let badge = item.querySelector(".communication-unread");
      if (conversation.unread && !badge) {
        badge = document.createElement("b");
        badge.className = "communication-unread";
        item.appendChild(badge);
      }
      if (badge) {
        badge.textContent = conversation.unread || "";
        badge.hidden = !conversation.unread;
      }
    }
  }

  function connectSocket() {
    const path = page.dataset.websocketUrl;
    if (!path || !("WebSocket" in window)) return;
    clearTimeout(reconnectTimer);
    const protocol = location.protocol === "https:" ? "wss:" : "ws:";
    socket = new WebSocket(`${protocol}//${location.host}${path}`);
    socket.addEventListener("open", () => {
      socket.send(JSON.stringify({ type: "read" }));
    });
    socket.addEventListener("message", (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "message") poll();
      if (data.type === "inbox") refreshConversationList();
      if (data.type === "receipt") updateReceipt(data);
      if (data.type === "typing") {
        const label = document.getElementById("typing-label");
        if (label) {
          label.textContent = `${data.name} is typing...`;
          label.hidden = !data.typing;
        }
      }
      if (data.type === "presence") {
        const label = document.getElementById("presence-label");
        if (label) label.textContent = data.online ? "Online" : "Offline";
      }
    });
    socket.addEventListener("close", () => {
      reconnectTimer = setTimeout(connectSocket, 3000);
    });
  }

  function sendTyping(typing) {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "typing", typing }));
    }
  }

  textarea?.addEventListener("input", () => {
    updateCharacterCount();
    if (draftKey) localStorage.setItem(draftKey, textarea.value);
    sendTyping(true);
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => sendTyping(false), 1200);
  });
  textarea?.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      messageForm.requestSubmit();
    }
  });

  function updateCharacterCount() {
    const counter = document.getElementById("message-character-count");
    if (counter && textarea) counter.textContent = `${textarea.value.length} / 5000`;
  }
  if (textarea && draftKey) textarea.value = localStorage.getItem(draftKey) || "";
  updateCharacterCount();

  messageList?.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-message-action]");
    if (!button) return;
    const article = button.closest("[data-message-id]");
    const id = article.dataset.messageId;
    const action = button.dataset.messageAction;
    const text = article.querySelector(".communication-bubble > p")?.textContent || "";

    if (action === "copy") {
      await navigator.clipboard.writeText(text);
      return;
    }
    if (action === "reply") {
      document.getElementById("reply-to-id").value = id;
      document.getElementById("reply-name").textContent =
        article.classList.contains("is-mine") ? "your message" : article.querySelector(".communication-bubble > strong")?.textContent || "message";
      document.getElementById("reply-copy").textContent = text.slice(0, 160);
      document.getElementById("reply-context").hidden = false;
      textarea?.focus();
      return;
    }
    if (action === "forward-open") {
      document.getElementById("forward-message-id").value = id;
      document.getElementById("forward-message-dialog").showModal();
      return;
    }
    const url = page.dataset.actionTemplate.replace("/0/", `/${id}/`);
    const body = new FormData();
    body.append("action", action);
    if (button.dataset.emoji) body.append("emoji", button.dataset.emoji);
    if (action === "edit") {
      const content = prompt("Edit message", text);
      if (content === null) return;
      body.append("content", content);
    }
    if (action === "delete" && !confirm("Delete this message?")) return;
    try {
      const data = await post(url, body);
      article.outerHTML = messageMarkup(data.message);
    } catch (error) {
      showError(error);
    }
  });

  document.getElementById("cancel-reply")?.addEventListener("click", resetReply);
  document.getElementById("forward-message-form")?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const messageId = document.getElementById("forward-message-id").value;
    const targetId = document.getElementById("forward-conversation-id").value;
    const url = page.dataset.actionTemplate.replace("/0/", `/${messageId}/`);
    const body = new FormData();
    body.append("action", "forward");
    body.append("target_conversation_id", targetId);
    try {
      await post(url, body);
      document.getElementById("forward-message-dialog").close();
    } catch (error) {
      showError(error);
    }
  });

  document.querySelectorAll("[data-conversation-action]").forEach((button) => {
    button.addEventListener("click", async () => {
      const body = new FormData();
      body.append("action", button.dataset.conversationAction);
      const url = `/communication/conversations/${activeConversation}/setting/`;
      if (button.dataset.conversationAction === "block" && !confirm("Block this user?")) return;
      await post(url, body);
      if (["archive", "restore"].includes(button.dataset.conversationAction)) {
        location.href = "/communication/";
      }
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
    const contacts = Array.from(recipientSelect.options).slice(1).map((option) => ({
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
      if (matches.some((contact) => contact.value === selected)) recipientSelect.value = selected;
      if (!matches.length) {
        const empty = new Option("No permitted contacts found", "");
        empty.disabled = true;
        recipientSelect.add(empty);
      }
      recipientCount.textContent = `${matches.length} permitted contact${matches.length === 1 ? "" : "s"}`;
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

  document.getElementById("group-member-search")?.addEventListener("input", (event) => {
    const query = event.target.value.trim().toLowerCase();
    document.querySelectorAll("[data-member-search]").forEach((item) => {
      item.hidden = !item.dataset.memberSearch.includes(query);
    });
  });

  const emojiPicker = document.getElementById("emoji-picker");
  document.getElementById("emoji-toggle")?.addEventListener("click", () => {
    emojiPicker.hidden = !emojiPicker.hidden;
  });
  emojiPicker?.addEventListener("click", (event) => {
    const button = event.target.closest("button");
    if (!button || !textarea) return;
    textarea.setRangeText(button.textContent, textarea.selectionStart, textarea.selectionEnd, "end");
    textarea.dispatchEvent(new Event("input"));
    textarea.focus();
  });

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
    if (!document.hidden) {
      heartbeat(true);
      poll();
      if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "read" }));
    }
  });

  if (messageList) messageList.scrollTop = messageList.scrollHeight;
  connectSocket();
  setInterval(poll, 3000);
})();
