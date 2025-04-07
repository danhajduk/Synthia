let watchdogInterval;

function loadSection(section) {
  const content = document.getElementById('content');
  if (watchdogInterval) clearInterval(watchdogInterval);

  fetch(`static/pages/${section}.html`)
    .then(response => {
      if (!response.ok) {
        throw new Error(`Failed to load ${section}`);
      }
      return response.text();
    })
    .then(html => {
      content.innerHTML = html;
      if (section === 'settings') {
        startWatchdog();
      } else if (section === 'gmail') {
        fetchGmailUnread();
        loadStoredEmails();
      }
    })
    .catch(error => {
      console.error(error);
      content.innerHTML = `<p>Error loading the ${section} section.</p>`;
    });
}

async function getMessage() {
  const base = window.location.pathname.replace(/\/$/, "");
  const res = await fetch(`${base}/api/hello`);
  const data = await res.json();
  document.getElementById("message").textContent = data.message;
}

function startWatchdog() {
  const base = window.location.pathname.replace(/\/$/, "");
  const statusCircle = document.getElementById("watchdog-status");
  const statusLabel = document.getElementById("watchdog-label");

  async function ping() {
    try {
      const res = await fetch(`${base}/api/hello`, { cache: "no-store" });
      if (res.ok) {
        statusCircle.style.backgroundColor = "limegreen";
        statusLabel.textContent = "Online";
      } else {
        statusCircle.style.backgroundColor = "red";
        statusLabel.textContent = "Unreachable";
      }
    } catch (e) {
      statusCircle.style.backgroundColor = "red";
      statusLabel.textContent = "Unreachable";
    }
  }

  ping(); // immediate check
  watchdogInterval = setInterval(ping, 20000); // every 20 seconds
}

function fetchGmailUnread() {
    const base = window.location.pathname.replace(/\/$/, "");
    fetch(`${base}/api/gmail/unread`)
      .then(res => res.json())
      .then(data => {
        document.getElementById('gmail-unread-today').textContent = data.unread_today ?? '–';
      })
      .catch(err => {
        console.error("Gmail fetch error:", err);
        document.getElementById('gmail-unread-today').textContent = "Error";
      });
  }

  function fetchAndStoreEmails() {
    const base = window.location.pathname.replace(/\/$/, "");
    const resultDiv = document.getElementById("gmail-fetch-result");
    resultDiv.textContent = "Fetching... ⏳";
  
    fetch(`${base}/api/gmail/fetch`)
      .then(res => res.json())
      .then(data => {
        if (data.fetched !== undefined) {
          resultDiv.textContent = `✅ Fetched and stored ${data.fetched} email(s).`;
        } else {
          resultDiv.textContent = `⚠️ Error: ${data.error}`;
        }
      })
      .catch(err => {
        console.error("Fetch error:", err);
        resultDiv.textContent = "❌ Failed to fetch emails.";
      });
  }

  function loadStoredEmails() {
    const base = window.location.pathname.replace(/\/$/, "");
    const body = document.getElementById("gmail-email-body");
    body.innerHTML = `<tr><td colspan="2">Loading...</td></tr>`;
  
    fetch(`${base}/api/gmail/list`)
      .then(res => res.json())
      .then(data => {
        if (data.emails?.length) {
          body.innerHTML = "";
          data.emails.forEach(email => {
            const row = document.createElement("tr");
            row.innerHTML = `<td>${email.sender}</td><td>${email.subject}</td>`;
            body.appendChild(row);
          });
        } else {
          body.innerHTML = `<tr><td colspan="2">No emails stored.</td></tr>`;
        }
      })
      .catch(err => {
        console.error("Load email list error:", err);
        body.innerHTML = `<tr><td colspan="2">Failed to load email list.</td></tr>`;
      });
  }
  
  function sendChat() {
    const base = window.location.pathname.replace(/\/$/, "");
    const input = document.getElementById("chat-input");
    const output = document.getElementById("chat-output");
  
    const message = input.value.trim();
    if (!message) return;
  
    output.textContent = "Thinking... 🤖";
  
    fetch(`${base}/api/openai/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message })
    })
      .then(res => res.json())
      .then(data => {
        output.textContent = data.reply ?? `⚠️ ${data.error}`;
      })
      .catch(err => {
        console.error(err);
        output.textContent = "❌ Failed to get a response.";
      });
  }
  