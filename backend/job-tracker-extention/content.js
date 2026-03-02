/**
 * Robust Job Detail Extractor
 * Handles Naukri, LinkedIn, Indeed, Internshala, and Wellfound
 */
function extractJobDetails() {
  let title = "";
  let company = "";
  const url = window.location.href;

  // ---------- NAUKRI (Even More Robust Version) ----------
if (url.includes("naukri.com")) {
    // 1. Title
    title = document.querySelector("h1")?.innerText || 
            document.querySelector(".jd-header-title")?.innerText || 
            document.title.split("|")[0].trim();

    // 2. Company: Added selectors for the newest layout you found
    company = document.querySelector(".styles_jhc__hiring-for__NG9SF")?.innerText || 
              document.querySelector("a[title*='Careers']")?.innerText || // Targets "Five Splash Infotech Careers"
              document.querySelector(".jd-header-comp-name a")?.innerText ||
              document.querySelector(".premium-comp-name")?.innerText ||
              document.querySelector(".casual-comp-name")?.innerText ||
              "Unknown Company";
              
    // Clean up: If it grabbed "Company Name Careers", remove the "Careers" part
    if (company.toLowerCase().endsWith(" careers")) {
        company = company.substring(0, company.length - 8).trim();
    }
}
  // ---------- LINKEDIN ----------
  else if (url.includes("linkedin.com")) {
    // 1. Grab the raw title
    let rawTitle = document.querySelector("h1")?.innerText || document.title;

    // 2. Clean the Title: Remove anything after '|', '·', or '-' 
    // This stops it from saying "| Inficore Soft | LinkedIn"
    title = rawTitle.split(/\||·|-/)[0].trim();

    // 3. Company: Look for the link that contains "/company/"
    const companyLink = document.querySelector('a[href*="/company/"]');
    
    company = companyLink?.innerText.trim() || 
              document.querySelector(".job-details-jobs-unified-top-card__company-name")?.innerText.trim() ||
              "Unknown Company";

    // Clean up Company if LinkedIn added a bullet there too
    if (company.includes("·")) {
        company = company.split("·")[0].trim();
    }
}

  // ---------- INDEED ----------
  else // ---------- INDEED (Clean Title Version) ----------
if (url.includes("indeed.com")) {
    // 1. Grab raw title from Header or Page Title
    let rawTitle = document.querySelector(".jobsearch-JobInfoHeader-title")?.innerText ||
                   document.querySelector("h1")?.innerText ||
                   document.title;

    // 2. Clean the Title: Split by '-' or '|' and take the first part
    // This removes "- AI agent startup - job post"
    title = rawTitle.split(/[-|]/)[0].trim();

    // 3. Target the Company
    company = document.querySelector(".jobsearch-CompanyReview--heading")?.innerText.trim() ||
              document.querySelector(".companyName")?.innerText.trim() ||
              document.querySelector("[class*='InlineCompanyRating'] div")?.innerText.trim() ||
              "Unknown Company";

    // 4. Final indeed-specific cleanup (remove 'new' or 'hiring' labels)
    title = title.replace(/new\n|hiring\n/gi, "").trim();
}
  // ---------- INTERNSHALA ----------
  else // ---------- INTERNSHALA (Listing & Detail View) ----------
if (url.includes("internshala.com")) {
    // 1. Role: Look for the specific ID you found (#job_title) first
    title = document.querySelector("#job_title")?.innerText.trim() ||
            document.querySelector(".profile_on_detail_page")?.innerText.trim() ||
            document.querySelector(".heading_3")?.innerText.trim() ||
            document.title.split("|")[0].trim();

    // 2. Company: Look for the specific class you found (.company-name) first
    company = document.querySelector(".company-name")?.innerText.trim() ||
              document.querySelector(".company_and_premium a")?.innerText.trim() ||
              document.querySelector(".link_display_name")?.innerText.trim() ||
              "Unknown Company";
              
    // 3. Title Cleaning: Final polish to remove "at [Company]" or extra text
    if (title.includes(" at ")) {
        title = title.split(" at ")[0].trim();
    }
    // Removes the "Internship in..." prefix if it grabbed the page title
    if (title.includes("Internship:")) {
        title = title.split("Internship:")[1].trim();
    }
}
  // ---------- WELLFOUND (AL AngelList) ----------
  else if (url.includes("wellfound.com")) {
    title = document.querySelector("h1")?.innerText;
    company = document.querySelector(".nc-text-color-black.nc-font-bold")?.innerText;
  }

  // ---------- CLEANING LOGIC ----------
  // Removes "New", "Hiring", or extra line breaks common in job board HTML
  const clean = (str) => str?.replace(/\n/g, " ").replace(/\s\s+/g, " ").trim();

  const finalTitle = clean(title) || clean(document.title);
  const finalCompany = clean(company) || "Unknown Company";

  return {
    title: finalTitle,
    company: finalCompany,
    url: url
  };
}

// Listen for messages from the popup
chrome.runtime.onMessage.addListener((req, sender, sendResponse) => {
  if (req.type === "GET_JOB_DATA") {
    const data = extractJobDetails();
    console.log("Extracted Data:", data); // Helpful for debugging
    sendResponse(data);
  }
  return true; // Required for async response support
});