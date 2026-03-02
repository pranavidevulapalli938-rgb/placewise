chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.type === "SEND_TO_BACKEND") {
    // 1. Retrieve the saved JWT token
    chrome.storage.local.get(["token"], (result) => {
      const token = result.token;

      // 2. Make the API call to your FastAPI server
      fetch("http://localhost:8000/applications", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}` 
        },
        body: JSON.stringify({
          company: request.data.company,
          role: request.data.title, // Maps 'title' from JS to 'role' in Python
          status: "Applied"
        })
      })
      .then(async (response) => {
  const data = await response.json();  // <-- get backend JSON

  if (response.ok) {
    sendResponse({ success: true, data: data }); // <-- forward it
  } else {
    console.error("Backend Error:", data);
    sendResponse({ success: false, error: data });
  }
})
      .catch((err) => {
        console.error("Fetch Error:", err);
        sendResponse({ success: false, error: err.message });
      });
    });
    return true; // Keeps the communication channel open for the async fetch
  }
});