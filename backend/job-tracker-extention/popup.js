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
      // Check for connection errors (e.g., script not loaded or page not refreshed)
      if (chrome.runtime.lastError || !res) {
        jobTitleDisplay.innerText = "Not a supported job page.";
        console.warn("Content script connection failed: ", chrome.runtime.lastError?.message);
        return;
      }

      // Populate the UI with extracted data
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
  statusMsg.innerText = ""; // Clear login messages
  fetchJobData(); 
}

function showLogin() {
  loginSection.style.display = "block";
  trackerSection.style.display = "none";
  jobTitleDisplay.innerText = "Loading..."; // Reset for next use
}

// 3. EVENT LISTENERS (Interactive logic)

// Login Action
document.getElementById("loginBtn").onclick = async () => {
  const email = document.getElementById("emailInput").value;
  const password = document.getElementById("passInput").value;

  statusMsg.innerText = "Logging in...";

  try {
    const res = await fetch("http://localhost:8000/login", {
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

// Save Job Action (Connects to background.js)
sendBtn.onclick = () => {
  statusMsg.innerText = "Saving...";
  chrome.runtime.sendMessage(
    { type: "SEND_TO_BACKEND", data: window.jobData },
    (res) => {
  if (!res || !res.success) {
    statusMsg.innerText = "❌ Failed to save.";
    return;
  }

  const message = res.data?.message;

  if (message === "created") {
    statusMsg.innerText = "✅ Job added successfully!";
  } 
  else if (message === "already_exists") {
    statusMsg.innerText = "⚠ This job is already in your tracker.";
  } 
  else {
    statusMsg.innerText = "Unexpected response from server.";
  }
}
  );
};

// 4. INITIALIZATION (The engine starts here)
chrome.storage.local.get(["token"], (result) => {
  if (result.token) {
    showTracker();
  } else {
    showLogin();
  }
});