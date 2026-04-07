/*
  User Support Chat Widget (Groq)
  Injected widget for existing user UI pages.
  Safe usage:
  - Keep real key in .env and inject into process.env.GROQ_API_KEY in Node/Vite builds.
  - Do not hardcode real keys in committed frontend files.
*/

(function () {
  const GROQ_API_KEY = ((typeof process !== 'undefined' && process.env && process.env.GROQ_API_KEY) || 'YOUR_GROQ_API_KEY_HERE');
  const SYSTEM_PROMPT = 'You are a helpful customer support AI assistant for a data integrity platform. Be concise, clear, and practical.';

  const GROQ_ENDPOINT = 'https://api.groq.com/openai/v1/chat/completions';
  const GROQ_MODEL = 'llama3-8b-8192';
  const MAX_TOKENS = 300;
  const TEMPERATURE = 0.7;

  const PLACEHOLDER_KEY = 'YOUR_GROQ_API_KEY_HERE';
  const chatHistory = [];

  let isOpen = false;
  let isFull = false;
  let isTyping = false;
  let typingNode = null;

  function injectStyles() {
    const style = document.createElement('style');
    style.textContent = `
      .ai-chat-bubble {
        position: fixed;
        right: 22px;
        bottom: 22px;
        width: 58px;
        height: 58px;
        border: 0;
        border-radius: 50%;
        background: #1e293b;
        color: #fff;
        cursor: pointer;
        font-size: 24px;
        display: grid;
        place-items: center;
        box-shadow: 0 18px 35px rgba(15, 23, 42, 0.16);
        transition: transform 0.2s ease, background 0.2s ease;
        z-index: 12000;
      }
      .ai-chat-bubble:hover { transform: translateY(-2px) scale(1.02); background: #334155; }

      .ai-chat-panel {
        position: fixed;
        right: 22px;
        bottom: 92px;
        width: 340px;
        height: 500px;
        display: flex;
        flex-direction: column;
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        overflow: hidden;
        box-shadow: 0 18px 35px rgba(15, 23, 42, 0.16);
        transform-origin: bottom right;
        transform: translateY(16px) scale(0.94);
        opacity: 0;
        pointer-events: none;
        transition: transform 0.24s ease, opacity 0.24s ease;
        z-index: 12000;
      }
      .ai-chat-panel.open { transform: translateY(0) scale(1); opacity: 1; pointer-events: auto; }
      .ai-chat-panel.full {
        right: 0;
        bottom: 0;
        width: 100vw;
        height: 100vh;
        border-radius: 0;
        border: 0;
        max-height: 100vh;
        box-shadow: none;
      }

      .ai-chat-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
        background: #1e293b;
        color: #fff;
        padding: 12px 12px 12px 14px;
      }
      .ai-chat-title { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
      .ai-chat-title strong {
        font-size: 14px;
        line-height: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      .ai-chat-status { font-size: 12px; display: flex; align-items: center; gap: 6px; opacity: 0.95; }
      .ai-chat-status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #22c55e;
        box-shadow: 0 0 0 3px rgba(34, 197, 94, 0.2);
      }
      .ai-chat-actions { display: flex; align-items: center; gap: 6px; }
      .ai-chat-icon-btn {
        border: 1px solid rgba(255, 255, 255, 0.25);
        background: rgba(255, 255, 255, 0.08);
        color: #fff;
        padding: 6px 10px;
        font-size: 12px;
        border-radius: 8px;
        cursor: pointer;
      }
      .ai-chat-icon-btn:hover { background: rgba(255, 255, 255, 0.18); }

      .ai-warning-banner {
        display: none;
        background: #fef2f2;
        color: #7f1d1d;
        border-bottom: 1px solid #fecaca;
        padding: 10px 12px;
        font-size: 12px;
        line-height: 1.45;
      }
      .ai-warning-banner.show { display: block; }

      .ai-chat-body {
        flex: 1;
        overflow-y: auto;
        padding: 14px;
        background: #f8fafc;
        display: flex;
        flex-direction: column;
        gap: 10px;
      }
      .ai-chat-panel.full .ai-chat-body {
        max-width: 920px;
        width: 100%;
        margin: 0 auto;
        padding: 20px 22px;
      }

      .msg-row { display: flex; }
      .msg-row.user { justify-content: flex-end; }
      .msg-row.bot { justify-content: flex-start; }
      .msg-bubble {
        max-width: 85%;
        border-radius: 14px;
        padding: 10px 12px;
        font-size: 14px;
        line-height: 1.45;
        border: 1px solid #e2e8f0;
        white-space: pre-wrap;
        word-wrap: break-word;
      }
      .msg-row.user .msg-bubble {
        background: #1e293b;
        color: #fff;
        border-color: #1e293b;
        border-bottom-right-radius: 4px;
      }
      .msg-row.bot .msg-bubble {
        background: #fff;
        color: #0f172a;
        border-bottom-left-radius: 4px;
      }

      .typing-wrap {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 9px 10px;
        border-radius: 12px;
        background: #fff;
        border: 1px solid #e2e8f0;
        width: fit-content;
      }
      .typing-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
        background: #94a3b8;
        animation: aiTypingBounce 1s infinite ease-in-out;
      }
      .typing-dot:nth-child(2) { animation-delay: 0.15s; }
      .typing-dot:nth-child(3) { animation-delay: 0.3s; }
      @keyframes aiTypingBounce {
        0%, 80%, 100% { transform: translateY(0); opacity: 0.45; }
        40% { transform: translateY(-5px); opacity: 1; }
      }

      .ai-chat-input-wrap {
        border-top: 1px solid #e2e8f0;
        background: #fff;
        padding: 10px;
      }
      .ai-chat-panel.full .ai-chat-input-wrap { padding: 14px 18px; }
      .ai-chat-input-row {
        display: flex;
        gap: 8px;
        align-items: flex-end;
        max-width: 920px;
        margin: 0 auto;
      }
      .ai-chat-input {
        flex: 1;
        min-height: 42px;
        max-height: 140px;
        resize: vertical;
        border: 1px solid #e2e8f0;
        border-radius: 10px;
        padding: 10px;
        font: inherit;
        font-size: 14px;
        color: #0f172a;
        outline: none;
      }
      .ai-chat-input:focus {
        border-color: #1e293b;
        box-shadow: 0 0 0 3px rgba(30, 41, 59, 0.12);
      }
      .ai-send-btn {
        border: 0;
        border-radius: 10px;
        padding: 11px 14px;
        background: #1e293b;
        color: #fff;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        min-width: 76px;
      }
      .ai-send-btn:hover { background: #334155; }

      @media (max-width: 560px) {
        .ai-chat-panel {
          right: 12px;
          left: 12px;
          width: auto;
          bottom: 84px;
          height: 68vh;
        }
        .ai-chat-panel.full { right: 0; left: 0; }
        .ai-chat-bubble { right: 14px; bottom: 14px; }
      }
    `;
    document.head.appendChild(style);
  }

  function injectMarkup() {
    const bubble = document.createElement('button');
    bubble.className = 'ai-chat-bubble';
    bubble.id = 'aiChatBubble';
    bubble.setAttribute('aria-label', 'Open support chat');
    bubble.setAttribute('title', 'Chat with support');
    bubble.textContent = '💬';

    const panel = document.createElement('section');
    panel.className = 'ai-chat-panel';
    panel.id = 'aiChatPanel';
    panel.setAttribute('aria-hidden', 'true');
    panel.innerHTML = `
      <header class="ai-chat-header">
        <div class="ai-chat-title">
          <strong>AI Support Assistant</strong>
          <div class="ai-chat-status"><span class="ai-chat-status-dot"></span>Online</div>
        </div>
        <div class="ai-chat-actions">
          <button class="ai-chat-icon-btn" id="aiToggleFullBtn" title="Toggle full window">Full Window</button>
          <button class="ai-chat-icon-btn" id="aiCloseBtn" aria-label="Close chat">Close</button>
        </div>
      </header>
      <div class="ai-warning-banner" id="aiWarningBanner">
        Warning: GROQ_API_KEY is still placeholder. Configure your environment key before production use.
      </div>
      <div class="ai-chat-body" id="aiChatBody"></div>
      <div class="ai-chat-input-wrap">
        <div class="ai-chat-input-row">
          <textarea id="aiChatInput" class="ai-chat-input" rows="1" placeholder="Type your message and press Enter..."></textarea>
          <button id="aiSendBtn" class="ai-send-btn">Send</button>
        </div>
      </div>
    `;

    document.body.appendChild(bubble);
    document.body.appendChild(panel);

    return { bubble, panel };
  }

  function scrollToBottom(body) {
    body.scrollTop = body.scrollHeight;
  }

  function appendMessage(body, role, text) {
    const row = document.createElement('div');
    row.className = 'msg-row ' + (role === 'user' ? 'user' : 'bot');

    const bubbleNode = document.createElement('div');
    bubbleNode.className = 'msg-bubble';
    bubbleNode.textContent = text;

    row.appendChild(bubbleNode);
    body.appendChild(row);
    scrollToBottom(body);
  }

  function showTyping(body) {
    if (isTyping) return;
    isTyping = true;
    const row = document.createElement('div');
    row.className = 'msg-row bot';
    const wrap = document.createElement('div');
    wrap.className = 'typing-wrap';
    wrap.innerHTML = '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>';
    row.appendChild(wrap);
    body.appendChild(row);
    typingNode = row;
    scrollToBottom(body);
  }

  function hideTyping() {
    isTyping = false;
    if (typingNode && typingNode.parentNode) typingNode.parentNode.removeChild(typingNode);
    typingNode = null;
  }

  async function fetchGroqReply() {
    const messages = [{ role: 'system', content: SYSTEM_PROMPT }].concat(chatHistory);

    const response = await fetch(GROQ_ENDPOINT, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + GROQ_API_KEY,
      },
      body: JSON.stringify({
        model: GROQ_MODEL,
        messages: messages,
        max_tokens: MAX_TOKENS,
        temperature: TEMPERATURE,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      throw new Error('Groq API error ' + response.status + ': ' + errorText);
    }

    const data = await response.json();
    const content = data && data.choices && data.choices[0] && data.choices[0].message && data.choices[0].message.content
      ? String(data.choices[0].message.content).trim()
      : '';
    return content || 'I could not generate a response right now. Please try again.';
  }

  function init() {
    injectStyles();
    const injected = injectMarkup();

    const bubble = injected.bubble;
    const panel = injected.panel;
    const closeBtn = document.getElementById('aiCloseBtn');
    const toggleFullBtn = document.getElementById('aiToggleFullBtn');
    const body = document.getElementById('aiChatBody');
    const input = document.getElementById('aiChatInput');
    const sendBtn = document.getElementById('aiSendBtn');
    const warningBanner = document.getElementById('aiWarningBanner');

    warningBanner.classList.toggle('show', GROQ_API_KEY === PLACEHOLDER_KEY || !String(GROQ_API_KEY).trim());

    appendMessage(body, 'bot', 'Hi, I am your AI support assistant. How can I help you today?');

    function openChat() {
      isOpen = true;
      panel.classList.add('open');
      panel.setAttribute('aria-hidden', 'false');
      setTimeout(function () { input.focus(); }, 120);
    }

    function closeChat() {
      isOpen = false;
      panel.classList.remove('open');
      panel.setAttribute('aria-hidden', 'true');
    }

    function toggleFullWindow() {
      isFull = !isFull;
      panel.classList.toggle('full', isFull);
      toggleFullBtn.textContent = isFull ? 'Compact View' : 'Full Window';
      scrollToBottom(body);
    }

    function autoResizeInput() {
      input.style.height = 'auto';
      input.style.height = Math.min(input.scrollHeight, 140) + 'px';
    }

    async function sendMessage() {
      const text = input.value.trim();
      if (!text || isTyping) return;

      appendMessage(body, 'user', text);
      chatHistory.push({ role: 'user', content: text });
      input.value = '';
      input.style.height = 'auto';

      if (GROQ_API_KEY === PLACEHOLDER_KEY || !String(GROQ_API_KEY).trim()) {
        appendMessage(body, 'bot', 'Please set a valid GROQ_API_KEY in your environment first.');
        return;
      }

      try {
        showTyping(body);
        const reply = await fetchGroqReply();
        hideTyping();
        appendMessage(body, 'bot', reply);
        chatHistory.push({ role: 'assistant', content: reply });
      } catch (err) {
        hideTyping();
        appendMessage(body, 'bot', 'Sorry, I hit an error: ' + err.message);
      }
    }

    bubble.addEventListener('click', function () {
      if (isOpen) closeChat();
      else openChat();
    });

    closeBtn.addEventListener('click', closeChat);
    toggleFullBtn.addEventListener('click', toggleFullWindow);
    sendBtn.addEventListener('click', sendMessage);

    input.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });

    input.addEventListener('input', autoResizeInput);

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && isOpen) closeChat();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
