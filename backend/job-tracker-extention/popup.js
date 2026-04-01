// 1. SELECT ELEMENTS FIRST (Global scope)
const loginSection = document.getElementById("loginSection");
const trackerSection = document.getElementById("trackerSection");
const statusMsg = document.getElementById("status");
const jobTitleDisplay = document.getElementById("jobTitle");
const jobCompanyDisplay = document.getElementById("jobCompany");
const sendBtn = document.getElementById("sendBtn");

// 2. DEFINE HELPER FUNCTIONS (Logic definitions)
function fetchJobData() {
  chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
    if (!tabs[0]) return;

    chrome.tabs.sendMessage(tabs[0].id, { type: "GET_JOB_DATA" }, (res) => {
      if (chrome.runtime.lastError || !res) {
        jobTitleDisplay.innerText = "Please refresh the page first.";
        jobCompanyDisplay.innerText = "";
        sendBtn.disabled = true;
        console.warn("Content script connection failed: ", chrome.runtime.lastError?.message);
        return;
      }

      jobTitleDisplay.innerText = res.title || "Unknown Title";
      jobCompanyDisplay.innerText = res.company || "Unknown Company";
      sendBtn.disabled = false;

      // Store data globally in the popup for the 'Save Job' click
      window.jobData = res;
    });
  });
}

function showTracker() {
  loginSection.style.display = "none";
  trackerSection.style.display = "block";
  statusMsg.innerText = "";
  fetchJobData();
}

function showLogin() {
  loginSection.style.display = "block";
  trackerSection.style.display = "none";
  jobTitleDisplay.innerText = "Loading...";
}

// 3. EVENT LISTENERS (Interactive logic)

// Login Action
document.getElementById("loginBtn").onclick = async () => {
  const email = document.getElementById("emailInput").value;
  const password = document.getElementById("passInput").value;

  statusMsg.innerText = "Logging in...";

  try {
    const res = await fetch("https://placewise-api.onrender.com/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    const data = await res.json();
    if (res.ok && data.access_token) {
      chrome.storage.local.set({ token: data.access_token }, () => {
        showTracker();
      });
    } else {
      statusMsg.innerText = "❌ Login Failed: Check credentials";
    }
  } catch (err) {
    statusMsg.innerText = "❌ Connection Error: Is backend running?";
  }
};

// Logout Action
document.getElementById("logoutBtn").onclick = () => {
  chrome.storage.local.remove(["token"], () => {
    showLogin();
  });
};

// Save Job Action
sendBtn.onclick = () => {
  // Guard: jobData must exist before sending
  if (!window.jobData || !window.jobData.title) {
    statusMsg.innerText = "❌ Please refresh the page and try again.";
    return;
  }

  statusMsg.innerText = "Saving...";

  chrome.runtime.sendMessage(
    { type: "SEND_TO_BACKEND", data: window.jobData },
    (res) => {
      // Guard: catch extension-level errors (e.g. background script not ready)
      if (chrome.runtime.lastError) {
        statusMsg.innerText = "❌ Extension error. Try reloading the extension.";
        console.error("Runtime error:", chrome.runtime.lastError.message);
        return;
      }

      if (!res || !res.success) {
        // Show specific error if available
        statusMsg.innerText = `❌ Failed to save. ${res?.error || ""}`;
        return;
      }

      const message = res.data?.message;

      if (message === "created") {
        statusMsg.innerText = "✅ Job added successfully!";
      } else if (message === "already_exists") {
        statusMsg.innerText = "⚠ This job is already in your tracker.";
      } else {
        statusMsg.innerText = "Unexpected response from server.";
      }
    }
  );
};

// 4. INITIALIZATION
chrome.storage.local.get(["token"], (result) => {
  if (result.token) {
    showTracker();
  } else {
    showLogin();
  }
});