const BACKEND_URL = "https://placewise-ai.onrender.com"; // ← update to your Render URL

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "SEND_TO_BACKEND") {
    chrome.storage.local.get(["token"], (result) => {
      const token = result.token;

      if (!token) {
        sendResponse({ success: false, error: "Not logged in" });
        return;
      }

      fetch(`${BACKEND_URL}/applications`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`
        },
        body: JSON.stringify({
          company: request.data.company,
          role:    request.data.title,
        })
      })
      .then(async (response) => {
        const data = await response.json();
        if (response.ok) {
          sendResponse({ success: true, data });
        } else {
          // FIX: handle 401 specifically so popup can prompt re-login
          if (response.status === 401) {
            chrome.storage.local.remove(["token"]);
            sendResponse({ success: false, error: "Session expired. Please log in again.", code: 401 });
          } else {
            sendResponse({ success: false, error: data.detail || "Backend error" });
          }
        }
      })
      .catch((err) => {
        sendResponse({ success: false, error: "Cannot reach backend. Is it running?" });
      });
    });

    return true; // Keep channel open for async
  }
});