import os
import base64
import re
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
# VERSION 7 - HTML body extraction, all rejection phrases, clean code

CLIENT_CONFIG = {
    "web": {
        "client_id":      os.getenv("GOOGLE_CLIENT_ID"),
        "client_secret":  os.getenv("GOOGLE_CLIENT_SECRET"),
        "redirect_uris":  [os.getenv("GOOGLE_REDIRECT_URI")],
        "auth_uri":       "https://accounts.google.com/o/oauth2/auth",
        "token_uri":      "https://oauth2.googleapis.com/token",
    }
}


def get_flow() -> Flow:
    return Flow.from_client_config(
        CLIENT_CONFIG,
        scopes=SCOPES,
        redirect_uri=os.getenv("GOOGLE_REDIRECT_URI")
    )


HARD_SPAM_DOMAINS = {
    "naukri", "naukricampus", "dare2compete",
    "leetcode", "hackerrank", "hackerearth", "codility",
    "interviewbit", "geeksforgeeks", "glassdoor",
    "shine", "monster", "timesjobs", "foundit", "apna",
    "jobsora", "ambitionbox", "cutshort", "hirist", "iimjobs",
    "mailer", "smtp", "bounce", "newsletter", "digest",
    "udemy", "coursera", "youtube", "kotak",
    # Newsletter / content domains — these NEVER send job application emails
    "deeplearning", "substack", "beehiiv", "mailchimp",
    "sendgrid", "constantcontact", "campaignmonitor", "klaviyo",
    "hubspot", "marketo", "convertkit", "drip", "thebatch",
    # LinkedIn job alert sender (NOT the rejection sender jobs-noreply@linkedin.com)
    "jobalerts-noreply",
    # Indeed job alert domains (NOT noreply@indeed.com which has real company emails)
    "jobalert",  # donotreply@jobalert.indeed.com, alert@indeed.com
    # Community / review sites — never send job application emails
    "cerebralvalley",   # newsletter, NOT a company that hires via email
    "glassdoor",        # community digests, reviews — not job application emails
    "workatastartup",   # YC startup message relay — NOT a real job application
    # Cold outreach / spam internship invitation sites
    "learntricksedutech", "uptricks", "navoditainfotech",
    # Career mentorship spam
    "ritika",           # "Ritika from Unstop" mentor marketing emails
    # Q&A / content platforms — "interview" in their emails is content, not a job invite
    "quora", "english-quora-digest",
    # EdTech platforms — "selected/congratulations" means course enrollment, NOT a job offer
    "greatlearning", "mygreatlearning", "great-learning",
    "codingninjas", "coding-ninjas",
    "simplilearn", "upgrad", "scaler", "pwskills", "masaischool",
    "swayam", "nptel",
}

# Unstop sends REAL rejection emails — handled separately with override logic
# (don't add to HARD_SPAM_DOMAINS)
UNSTOP_DOMAINS = {"unstop", "unstop.com", "unstop.email", "unstop.events"}

# ATS/platform names that should never appear as a company name.
# NOTE: "internshala" is intentionally NOT in this list — Internshala sends real
# hiring/selected/interview emails and "Internshala" is a valid company to track.
PLATFORM_COMPANY_NAMES = {
    "recooty", "indeedapply", "indeed",
    "wellfound", "greenhouse", "lever", "workday", "bamboohr", "smartrecruiters",
    "unstop", "unstop events", "naukri", "jobalert", "jobalerts", "job alert",
    "job alerts", "linkedin job alerts", "linkedin jobs", "naukricampus",
    "dare2compete", "cutshort", "hirist", "iimjobs", "foundit", "apna",
    "shine", "monster", "timesjobs", "ambitionbox", "jobsora",
    "recruitee", "jobvite", "icims", "taleo", "successfactors", "pinpoint",
    "ashbyhq", "rippling", "dover", "teamtailor", "comeet", "freshteam",
    "zohorecruit", "occupop", "jazzhr", "jobsoid", "betterteam", "manatal",
    # EdTech platforms — should never appear as a company name in job tracking
    "greatlearning", "great learning", "coding ninjas", "codingninjas",
    "simplilearn", "upgrad", "scaler", "pwskills", "masai school", "masaischool",
    "coursera", "udemy", "edx", "swayam", "nptel",
    # Generic category words that get extracted as company names
    "courses", "certifications", "certification", "certificate",
    "quora", "quora digest",
}

PLACEMENT_OVERRIDE_SUBJECTS = [
    "your application to", "your application was sent",
    "thank you for applying", "thanks for applying",
    "thank you for your application", "application received",
    "we received your application", "offer letter",
    "interview scheduled", "interview invitation", "interview call",
    "interview on", "invited for interview", "shortlisted for interview",
    "shortlisted for the next", "shortlisted for further",
    "shortlisted", "unfortunately", "regret to inform",
    "not moving forward", "assessment", "you have been selected",
    "congratulations! you have been selected",  # Internshala real selection
    "thank you for submitting", "your application with",
    "update from", "thanks from", "your update from",
    "received your job application", "job application",
    # Indeed-style rejection subjects
    "an update on your application from",
    "update on your application from",
    "an update on your application",
    "update on your application",
    # LinkedIn/Indeed/Unstop rejection subjects
    "your update from",
    "application status",
    "application: status update",
    "status update",
    "not selected",
    "not shortlisted",
    "we regret",
    "application decision",
    "decision on your application",
    "regarding your application",
    "after careful consideration",
    "moving forward with other",
    "chosen to move",
    "pursue other candidates",
    "we have reviewed your application",
    "update on your application for",
    "your application was not",
    "was not selected",
    "was unsuccessful",
    "application unsuccessful",
    "we appreciate your interest",
    "thank you for your interest in",
]


PROMOTIONAL_SUBJECT_PATTERNS = [
    r"\d+\s+(jobs?|openings?|positions?)\s+(for you|match|near you)",
    r"jobs?\s+(alert|digest|recommendation|suggestion)",
    r"new\s+jobs?\s+match",
    r"is\s+hiring\s+(interns?|freshers?|candidates?)\s*$",
    r"your\s+(weekly|daily|monthly)\s+(digest|update|newsletter)",
    r"(courses?|lessons?|tutorials?)\s+(for you|available|recommended)",
    r"(discount|offer|sale|free\s+trial)\s+(on|for|until)",
    r"activate your .+ skills", r"join .+ contest", r"what is .+ \?",
    r"(top|best) companies? (hiring|recruiting) now",
    r"exclusive (job|career) (opportunities|openings)",
    r"\d+ (new )?jobs? (match|recommendation)",
    r"people also applied", r"jobs? you might like", r"recommended jobs?",
    r"new data analyst jobs", r"don't miss conversations",
    r'^"[^"]+":\s*\w+',
    # LinkedIn Job Alert emails — "Your job alert for [Role]"
    r"your job alert for",
    r"job alert for",
    r"new jobs? that match your",
    r"jobs? matching your",
    # Cold outreach / spam internship invitation patterns
    r"internship (invitation|opportunity|program) at ",
    r"internship opportunities at ",
    r"invitation to (apply|join|participate)",
    r"invitation to the .+ (program|partnership|community)",
    r"student partner program",
    r"(bowl buzz|community digest|trending posts)",   # Glassdoor community
    r"interviewguard|interview fraud",                # Cerebralvalley newsletter
    r"sent you a message",                            # YC / startup message relay
    r"from dsa to offer",
    r"placement stress",
    r"career (guidance|shortcut|start)",
    r"(mentors?|mentor) (can help|whose)",
    r"(your|pranavi)[,\s]+ (from|engineering|these)",  # Mentor spam
    # EdTech promo subject patterns
    r"(microsoft|google|amazon|ibm|flipkart).*(in \d+ (months?|weeks?))",  # "Microsoft in 6 months"
    r"(in \d+ (months?|weeks?)).*(microsoft|google|amazon|ibm)",
    r"prepare for a role",           # Generic EdTech promo
    r"become a .*(developer|engineer|analyst|scientist)",
    r"land (a|your) (job|role|offer) (at|in)",
    r"crack (the )?(interview|campus|placement)",
    r"(boot ?camp|bootcamp) (enrollment|program|batch)",
    r"(free|paid) (course|program|batch|workshop) (on|for|starts)",
    r"(job bootcamp|job guarantee|placement guarantee)",
    r"top stories for",              # Quora digest subject
    r"quora digest",
]


def is_promotional_email(sender: str, subject: str) -> bool:
    subject_lower = subject.lower()
    sender_lower = sender.lower()

    # Hard-block known newsletter / content domains — these NEVER send job application emails
    NEWSLETTER_SENDER_DOMAINS = [
        "deeplearning.ai", "info.deeplearning.ai", "batch.deeplearning.ai",
        "substack.com", "beehiiv.com", "mailchimp.com", "sendgrid.net",
        "constantcontact.com", "campaignmonitor.com", "klaviyo.com",
        "hubspot.com", "marketo.net", "convertkit.com", "drip.com",
        "coursera.org", "udemy.com", "edx.org",
        # Tech community newsletters — NOT job application platforms
        "mail.cerebralvalley.ai", "cerebralvalley.ai",
        # Glassdoor community digests
        "glassdoor.com",
        # Y Combinator message relay (workatastartup is a message relay, not application system)
        "ycombinator.com", "workatastartup.com",
        # Cold outreach / spam internship companies
        "learntricksedutech.com", "uptricks.com", "navoditainfotech.com",
        # Internshala Student Partner Program (ISP) is a MARKETING program, not a job
        # Real Internshala job emails come from student@internshala.com and say
        # "Congratulations! You have been selected for [Role] at [Company]"
        # ISP emails come from student@mail.internshala.com (note: mail. subdomain)
        "mail.internshala.com",
        # Q&A platforms — their "interview" content is articles, not job invites
        "quora.com", "english-quora-digest@quora.com",
        # EdTech — "selected/congratulations" = course enrollment, NOT job offer
        "mygreatlearning.com", "greatlearning.in", "greatlearning.com",
        "codingninjas.com", "codingninjas.in",
        "simplilearn.com", "upgrad.com", "scaler.com",
        "pwskills.com", "masaischool.com",
    ]
    if any(d in sender_lower for d in NEWSLETTER_SENDER_DOMAINS):
        return True

    # LinkedIn Job Alerts sender is always promo
    if "jobalerts-noreply@linkedin.com" in sender_lower:
        return True
    # Block all LinkedIn digest/recommendation senders EXCEPT the real rejection sender
    if re.search(r"(jobalerts|job-alert|jobalert|jobs-digest)@linkedin", sender_lower):
        return True
    # jobs-noreply@linkedin.com sends BOTH real rejections AND job digest emails
    # Distinguish by subject — job digests say "New Data Analyst jobs that match your profile"
    if "jobs-noreply@linkedin.com" in sender_lower:
        # Check for real application signals FIRST — never block these
        real_signals = [
            "your update from", "update from", "unfortunately",
            "your application", "application update", "not moving forward",
            "regret", "not selected", "not shortlisted", "interview",
            "shortlisted", "offer", "congratulations", "selected for",
            "assessment", "an update on"
        ]
        if any(s in subject_lower for s in real_signals):
            return False  # Always let real signals through
        # If it's a job digest/recommendation, block it
        digest_signals = [
            "new jobs that match", "jobs that match your profile",
            "apply now to", "looking for a new job", "explore new jobs for",
            "new data analyst jobs", "new jobs similar to",
        ]
        if any(s in subject_lower for s in digest_signals):
            return True
        # Otherwise fall through — could be a real rejection

    # Unstop sends REAL rejection/selection emails — only block their promos, not real ones
    is_unstop = any(d in sender_lower for d in ["unstop.com", "unstop.email", "unstop.events", "@unstop"])
    if is_unstop:
        # Block mentor marketing / subscription emails (e.g. "Ritika from Unstop")
        # These are cold outreach/newsletter emails, not job application updates
        UNSTOP_MARKETING_PATTERNS = [
            "from dsa to offer", "placement stress", "engineering is confusing",
            "mentors can help", "should you really do an mba", "shortcut",
            "career goals", "offer letter", "next step shouldn't be",
            "career start", "guidance for",
        ]
        if any(p in subject_lower for p in UNSTOP_MARKETING_PATTERNS):
            return True
        # Also block if sender display name looks like a person name (e.g. "Ritika from Unstop")
        # Real Unstop application emails come from "Unstop Events <updates@unstop.email>"
        display_match = re.match(r'^"?([^"<@\n]+)"?\s*<', sender)
        if display_match:
            display = display_match.group(1).strip().lower()
            # Person-name senders like "Ritika from Unstop" are marketing
            if re.match(r'^[a-z]+ from unstop', display):
                return True
        # Allow if subject contains a real application update signal
        UNSTOP_REAL_SIGNALS = [
            "update on your application", "unfortunately", "regret",
            "not selected", "not shortlisted", "not moving forward",
            "shortlisted", "interview", "selected for", "congratulations",
            "rejected", "offer", "assessment", "accepted", "been accepted",
            "has been accepted", "application has been accepted",
            "you have been", "you've been", "pleased to inform",
            "we regret", "application status", "result",
        ]
        if any(s in subject_lower for s in UNSTOP_REAL_SIGNALS):
            return False
        return True  # All other Unstop emails are promo

    # Hard spam domain check MUST come before subject overrides.
    # Without this, a dare2compete email with "offer letter" in subject
    # would bypass all spam checks via PLACEMENT_OVERRIDE_SUBJECTS.
    # We extract ALL domain parts and check each one so that emails from
    # subdomains like hello@careercamp.codingninjas.com are also caught
    # (subdomain="careercamp", apex="codingninjas" — both are checked).
    domain_match = re.search(r"@(([\w\-]+\.)*([\w\-]+))\.([\w\-]+)", sender_lower)
    if domain_match:
        full_domain = domain_match.group(0)[1:]  # strip leading @
        parts = full_domain.split(".")
        for spam_domain in HARD_SPAM_DOMAINS:
            # Match if ANY part of the domain equals or starts with the spam token
            if any(part == spam_domain or part.startswith(spam_domain) for part in parts):
                return True

    for override in PLACEMENT_OVERRIDE_SUBJECTS:
        if override in subject_lower:
            return False

    for pattern in PROMOTIONAL_SUBJECT_PATTERNS:
        if re.search(pattern, subject_lower):
            return True

    return False


def parse_email_for_status(subject: str, body: str) -> str | None:
    text = (subject + " " + body).lower()

    # SELECTED
    SELECTED_PHRASES = [
        "offer letter", "pleased to offer you", "happy to inform you",
        "we are delighted to offer", "congratulations on your selection",
        "you have been selected", "you have been chosen", "welcome aboard",
        "joining date", "your joining", "extend an offer to you",
        "we would like to offer you", "pleased to extend", "selected for the role",
        "selected for the position", "pleased to welcome you",
        "you are selected", "you've been selected", "happy to welcome you",
        # Unstop / platform acceptance phrasing
        "your application has been accepted", "application has been accepted",
        "has been accepted for the role", "accepted for the position",
        "happy to accept your application", "your profile has been accepted",
        "pleased to accept", "accepted your application",
    ]
    if any(p in text for p in SELECTED_PHRASES):
        return "Selected"

    # OA
    OA_PHRASES = [
        "online assessment", "complete the assessment", "take the online test",
        "assessment link", "coding challenge", "hackerrank test", "hackerearth test",
        "codility test", "complete the test by", "aptitude test link",
        "invited to complete", "invited to take", "please complete the following test",
        "complete this assessment", "assessment has been sent", "test link",
        "take this test", "your assessment", "amcat", "cocubes", "elitmus",
        "mettl test", "attempt the test",
    ]
    if any(p in text for p in OA_PHRASES):
        return "OA Received"

    # INTERVIEW — require scheduling context, not just the word "interview"
    INTERVIEW_PHRASES = [
        "we would like to schedule an interview", "you have been shortlisted for an interview",
        "interview has been scheduled", "your interview is scheduled",
        "interview invitation", "invite you for an interview", "interview slot",
        "please schedule your interview", "select a slot for your interview",
        "technical interview", "hr interview", "round 1 interview", "round 2 interview",
        "video interview link", "your interview on", "interview on zoom",
        "interview on google meet", "interview on microsoft teams",
        "confirm your availability", "scheduling an interview with you",
        "interview scheduling", "like to invite you for", "pleased to invite you",
        "would like to discuss your application", "shortlisted for the next round",
        "selected for interview", "interview call", "call letter", "campus interview",
        "face to face interview", "f2f interview", "panel interview", "interview details",
        "schedule your interview", "you have cleared", "you've cleared",
        "proceed to the next round", "moved to the next round", "next round of interview",
        "shortlisted for further", "shortlisted candidates", "we are pleased to invite",
        "zoom link for interview", "joining us for an interview",
    ]
    if any(p in text for p in INTERVIEW_PHRASES):
        return "Interview Scheduled"

    # REJECTED — check BODY, many rejections have "thank you" in subject but rejection in body
    REJECTION_PHRASES = [
        "we regret to inform", "unable to move forward with your application",
        "not moving forward with your candidacy", "your application was not successful",
        "we will not be moving forward", "decided not to move forward",
        "position has been filled", "we have decided to pursue other candidates",
        "unfortunately, we will not", "unfortunately we are unable to offer",
        "not shortlisted for further rounds", "application has not been successful",
        "we won't be able to proceed", "not selected for the next round",
        "not been shortlisted", "not shortlisted", "regret to let you know",
        "regret to share that", "unable to proceed with your application",
        "not progressing your application",
        # Amazon exact: "we have decided to progress with other candidates"
        "decided to progress with other candidates",
        "we have decided to progress with other",
        "progress with other candidates for this role",
        # Apple exact: "we've chosen to move ahead with other candidates"
        "we've chosen to move ahead with other candidates",
        "chosen to move ahead with other candidates",
        "we've chosen to move ahead",
        # Goldman Sachs exact: "regret to inform you that you are not eligible"
        "regret to inform you that you are not eligible",
        "you are not eligible for this role",
        # LinkedIn rejection updates
        "unfortunately, we will not be moving forward with your application",
        "we will not be moving forward with your application",
        "unfortunately, we will not be moving forward",
        "we will not be moving forward",
        # SHORT phrases — match even when snippet cuts off at ~200 chars
        # e.g. "Unfortunately, we will [CUTOFF]" -> "unfortunately, we will" matches
        "unfortunately, we will",
        "unfortunately, we won't",
        "unfortunately we will",
        "unfortunately we won't",
        # GatherGov / government job portals
        "your application has not been selected",
        "not been selected for further consideration",
        "will not be moving forward with your candidature",
        "not selected for this opportunity",
        "unsuccessful in your application",
        # Big tech style
        "we've chosen to move ahead with other", "we have chosen to move ahead with other",
        "chosen to move forward with other candidates", "chosen to move ahead with other applicants",
        "however, we've decided to move", "however, we have decided to move",
        "we will be moving forward with other", "we have moved forward with other",
        "we've decided to move forward with other", "decided to move forward with another",
        "move forward with other candidate", "we won't be moving forward with your application",
        "not be moving forward with your application",
        # Amazon specific body phrases
        "we have reviewed your application and",
        "not moving forward with your application at this time",
        "after careful consideration, we have decided",
        "we are moving forward with other applicants",
        # Softer rejections
        "pursuing other candidates", "pursue other applicants",
        "we have filled this position", "the position has been filled",
        "no longer moving forward", "after careful consideration, we",
        "after careful consideration, i", "after reviewing your application, we",
        "keep your profile for future", "we'll keep your resume on file",
        "keep your resume on file", "won't be moving forward",
        "not a match at this time", "not the right fit at this time",
        "does not meet our requirements", "unfortunately, your application",
        "unfortunately your application", "unfortunately, we've decided",
        "unfortunately we've decided", "not selected this time", "not been selected",
        "unsuccessful on this occasion", "not successful on this occasion",
        "we have decided not to proceed", "decided not to proceed with your",
        "not to proceed with your application", "not progressing your candidacy",
        # Indeed exact rejection phrase
        "has moved to the next step in their hiring process, and your application was not selected",
        "your application was not selected at this time",
        "application was not selected",
        "has decided to move forward with other applicants",
        "moved to the next step in their hiring process",
        # Unstop exact rejection phrases
        "has decided to move on with other candidates",
        "decided to move on with other candidates",
        "move on with other candidates on the basis",
        "has decided to move on with other",
        "moved on with other candidates",
        # General "move on with" rejections
        "decided to move on with other",
        "moving on with other candidates",
        "moving on with other applicants",
        "we regret to inform you that we",
        "not been shortlisted for this role",
        "not shortlisted for this position",
        "not shortlisted for this role",
        "we are unable to consider your application",
        "unable to consider your candidature",
        "we will not be able to move forward",
        "we are not able to move forward",
        "not able to proceed with your application",
        "your application has been closed",
        "other candidates whose experience",
        "profiles that more closely match",
        "profiles that closely match our requirements",
        "we have moved ahead with other candidates",
        "we're moving forward with other candidates",
        "we are moving ahead with other",
        "moved ahead with other applicants",
        "proceeding with other candidates",
        "proceeding with other applicants",
        "not a fit for this role",
        "not the right match for this role",
        "will not be proceeding with your application",
        "decided not to proceed further",
        "position has already been filled",
        "role has been filled",
        "this role has been closed",
        "position is no longer available",
        # LinkedIn-specific body rejection phrases
        "we appreciate you taking the time to apply",
        "we appreciate your interest in this opportunity, but",
        "we have decided to move in a different direction",
        "we've decided to move in a different direction",
        "we will not be able to move forward with your application",
        "we are not moving forward with your application",
        "your application has not progressed",
        "not progressed to the next stage",
        "not progressed to the next round",
        "unfortunately, you have not been shortlisted",
        "unfortunately you have not been shortlisted",
        "unfortunately, you were not selected",
        "unfortunately you were not selected",
        "we have filled the position",
        "the role has been filled",
        "we've filled this position",
        "we won't be taking your application forward",
        "not taking your application forward",
        "we have decided to close your application",
        "your application is now closed",
        "we're unable to offer you",
        "we are unable to offer you",
        "thank you for your interest, however",
        "thank you for your interest. however",
        "after reviewing your profile",
        "after reviewing your background",
        "your profile does not match",
        "your background does not match",
        "does not align with our current requirements",
        "not aligned with our requirements",
        "does not meet the requirements",
        "does not meet our current needs",
        "not what we are looking for at this time",
        "we're moving in a different direction",
        "we are moving in a different direction",
        # Short triggering phrases — must be specific enough to not fire on newsletters
        # REMOVED bare "unfortunately," — too broad, fires on newsletter content
        # These are specific enough to only appear in actual rejection emails:
        "unfortunately, we will not be moving",
        "unfortunately, we won't be moving",
        "unfortunately, we are unable to move",
        "unfortunately, your application has",
        "unfortunately, you have not been",
        "unfortunately, you were not selected",
        "unfortunately, we have decided",
        "unfortunately, we won't",
        "unfortunately, we will",
        "we regret that",
        "we're sorry to inform",
        "we are sorry to inform",
        "i regret to inform",
        # Short/subject-line rejections (fires even when body is empty)
        "application unsuccessful",
        "your application was unsuccessful",
        "we regret to inform",
        "we regret",
    ]
    if any(p in text for p in REJECTION_PHRASES):
        return "Rejected"

    # APPLIED
    APPLIED_PHRASES = [
        "your application was sent to", "your application to",
        "your application was sent", "you applied for", "application was sent to",
        "we have received your application", "thank you for applying",
        "thank you for your application", "thanks for applying",
        "thanks for your application", "your application has been received",
        "application has been submitted", "application confirmation",
        "we'll review your application", "we will review your application",
        "your resume has been received", "successfully applied",
        "application submitted successfully", "keep track of your application",
        "you've applied to", "you have applied to", "application was submitted",
        "application is under review", "we've received your application",
        "your application is being reviewed",
        "thank you for showing interest", "we have received your resume",
        "received your cv", "received your profile", "your candidature has been received",
        "your application for the", "applied for the role", "applied for the position",
        "application for the position of", "your job application",
        "we received your job application", "regarding your application",
        "application reference", "your indeed application", "applied on indeed",
        "your internshala application", "application for internship",
        "your application has been", "applied to",
        "thank you for submitting your profile", "submitting your profile to",
        "we've received your job application", "we have received your job application",
        "thanks - we've received your job application",
        "your application has been received and is under review",
        "thanks for your interest in the following role",
    ]
    if any(p in text for p in APPLIED_PHRASES):
        return "Applied"

    return None


def extract_company_from_email(sender: str, subject: str) -> str | None:
    # ── Block personal Gmail/Yahoo/Hotmail senders entirely ──────────────────
    if re.search(r"@(gmail|yahoo|hotmail|outlook|rediffmail|protonmail)\.(com|in|co\.in)", sender, re.IGNORECASE):
        return None

    # ── Internshala: sender is student@internshala.com ──────────────────────
    # Internshala sends real hiring/selected/interview emails on behalf of companies.
    # Track as "Internshala" so Selected/Interview entries are preserved in the DB.
    if re.search(r"@internshala\.com", sender, re.IGNORECASE):
        # Try to extract actual company from subject first
        m = re.search(
            r"(?:selected by|shortlisted by|interview (?:call |invite )?from|offer from) ([A-Za-z][^\n\|!,\.]{1,60}?)(?:\s*[!,\|]|\s*$)",
            subject, re.IGNORECASE
        )
        if m:
            c = m.group(1).strip().rstrip("!.,")
            if 1 < len(c) < 60:
                return c
        return "Internshala"  # Keep platform as company name for selection tracking

    # ── Indeed: display name IS the company, sender is noreply@indeed.com ────
    # e.g. "Twite AI Technologies <noreply@indeed.com>"
    # Block job alert senders: donotreply@jobalert.indeed.com, alert@indeed.com
    if re.search(r"@indeed\.com|@jobalert\.indeed\.com", sender, re.IGNORECASE):
        # Block job alert senders explicitly
        if re.search(r"(jobalert|alert@indeed|donotreply)", sender, re.IGNORECASE):
            return None
        m = re.match(r'^"?([^"<@\n]+)"?\s*<', sender)
        if m:
            display = m.group(1).strip()
            INDEED_GENERIC = {"indeed", "noreply", "no-reply", "notifications", "jobs", "indeed jobs"}
            if display.lower() not in INDEED_GENERIC and len(display) > 1:
                return display.strip()
        # Fallback: parse subject "An update on your application from [Company]"
        m2 = re.search(
            r"(?:an update on your application from|update on your application from) ([A-Za-z][^\n\|]{1,80}?)(?:\s*[\|]|\s*$)",
            subject, re.IGNORECASE
        )
        if m2:
            c = m2.group(1).strip().rstrip(".,")
            if 1 < len(c) < 80:
                return c
        return None  # Don't fall through to domain "Indeed"

    # ── Unstop: real rejection/update emails — extract company from subject/body ─
    # Subject: "Update on your application for Data Science Internship!"
    # Body: "the Yugensoft Innovations has decided to move on with other candidates"
    is_unstop_sender = any(d in sender.lower() for d in ["unstop.com", "unstop.email", "unstop.events", "@unstop"])
    if is_unstop_sender:
        # Try subject: "application for [Role] at [Company]" or "accepted for the role of [Role] at [Company]"
        m = re.search(
            r"(?:application for .+ at|application at|for the role of .+ at|accepted .+ at) ([A-Za-z][^\n\|!,\.]{1,60}?)(?:\s*[!,\|\.]|\s*$)",
            subject, re.IGNORECASE
        )
        if m:
            c = m.group(1).strip().rstrip("!.,")
            if 1 < len(c) < 60 and c.lower() not in PLATFORM_COMPANY_NAMES:
                return c
        # Subject like "Update on your application for Data Science Internship!" — no company
        # Company will be extracted from body in the main loop
        return None
    # When Recooty/Breezy/SmartRecruiters sends the email, the display name is
    # the ATS name, not the actual company — we'd log "Recooty" as company.
    ATS_SENDER_PATTERN = re.compile(
        r"@[\w\.\-]*(recooty|breezy|smartrecruiters|recruitee|jobvite|icims|taleo"
        r"|successfactors|bamboohr|pinpoint|ashbyhq|rippling|dover|teamtailor"
        r"|comeet|freshteam|zohorecruit|occupop|jazzhr|jobsoid|betterteam"
        r"|manatal|recruitly|innovexis|optimspace)[\w\.\-]*\.",
        re.IGNORECASE
    )
    if ATS_SENDER_PATTERN.search(sender):
        # Still try to salvage company name from subject patterns
        m = re.search(
            r"your application to .+ at ([A-Za-z][^\-\n,\.]{1,50}?)(?:\s*[\-,\|]|\s*$|\.|,)",
            subject, re.IGNORECASE
        )
        if m:
            c = m.group(1).strip().rstrip(".,")
            if 1 < len(c) < 60:
                return c
        # Also try "CompanyName | Thanks" format
        m2 = re.match(
            r"(?i)^([A-Za-z][A-Za-z0-9 .&-]{1,40}?)\s*\|\s*(?:thanks|your application|application received)",
            re.sub(r'^(Re|Fwd|FW|RE|FWD):\s*', '', subject.strip(), flags=re.IGNORECASE)
        )
        if m2:
            c = m2.group(1).strip()
            if 1 < len(c) < 60:
                return c
        return None  # Can't trust ATS sender display name

    # Strip reply/forward prefixes
    subject = re.sub(r'^(Re|Fwd|FW|RE|FWD):\s*', '', subject.strip(), flags=re.IGNORECASE)
    # Greenhouse/Lever format: "CompanyName | Thanks..." or "CompanyName | Your application..."
    m = re.match(r"(?i)^([A-Za-z][A-Za-z0-9 .&-]{1,40}?)\s*\|\s*(?:thanks|your application|application received)", subject)
    if m:
        c = m.group(1).strip()
        if 1 < len(c) < 60:
            return c

    # LinkedIn: "Your application to [Role] at [Company]"
    m = re.search(
        r"your application to .+ at ([A-Za-z][^\-\n,\.]{1,50}?)(?:\s*[\-,\|]|\s*$|\.|,)",
        subject, re.IGNORECASE
    )
    if m:
        c = m.group(1).strip().rstrip(".,")
        if 1 < len(c) < 60:
            return c

    # "application was sent to [Company]" — also handles numeric starts like "72 Dragons"
    m = re.search(
        r"application was sent to ([A-Za-z0-9][^\-\n,\.]{1,50}?)(?:\s*[\-,\|]|\s*$|\.|,)",
        subject, re.IGNORECASE
    )
    if m:
        c = m.group(1).strip().rstrip(".,")
        if 1 < len(c) < 60:
            return c

    # "Thank you for applying to [Company]"
    m = re.search(
        r"(?:thank you for applying to|thanks for applying to) ([A-Za-z][^!\n,]{1,50}?)(?:\s*[!,\|]|\s*$)",
        subject, re.IGNORECASE
    )
    if m:
        c = m.group(1).strip().rstrip("!.,")
        if 1 < len(c) < 60:
            return c

    # "Your Application with [Company]" — Goldman Sachs style
    m = re.search(
        r"your application with ([A-Za-z][^\-\n,\.]{1,50}?)(?:\s*[\-,\|]|\s*$)",
        subject, re.IGNORECASE
    )
    if m:
        c = m.group(1).strip().rstrip(".,")
        if 1 < len(c) < 60:
            return c

    # "Your update from [Company]" / "Update from [Company]" / "An update on your application from [Company]"
    m = re.search(
        r"(?:your update from|update from|thanks from|an update on your application from|update on your application from) ([A-Za-z][^\n\|]{1,80}?)(?:\s*[\|]|\s*$)",
        subject, re.IGNORECASE
    )
    if m:
        c = m.group(1).strip().rstrip(".,")
        # Strip trailing " - Status/Application/Update" noise
        c = re.sub(r"\s*\-\s*(Application|Status|Update|Job|Position|Role).*$", "", c, flags=re.IGNORECASE).strip()
        # Strip trailing city/country suffixes like ", India" or "- Chennai"
        c = re.sub(r"\s*[,\-]\s*(India|Chennai|Mumbai|Bangalore|Hyderabad|Pune|Delhi|Remote).*$", "", c, flags=re.IGNORECASE).strip()
        c = c.rstrip(".,")
        if 1 < len(c) < 80:
            return c

    # "submitting your profile to [Company]"
    m = re.search(
        r"submitting your profile to ([A-Za-z][^!\n,\.]{1,50}?)(?:\s*[!,\.]|\s*$)",
        subject, re.IGNORECASE
    )
    if m:
        c = m.group(1).strip().rstrip("!.,")
        if 1 < len(c) < 60:
            return c

    # Display name from sender
    m = re.match(r'^"?([^"<@\n]+)"?\s*<', sender)
    if m:
        display = m.group(1).strip()
        GENERIC = {"linkedin", "indeed", "wellfound", "noreply",
                   "no-reply", "notifications", "jobs", "careers", "talent",
                   "y combinator", "ycombinator", "greenhouse", "lever", "workday"}
        # Block "Name from Platform" pattern — e.g. "Ritika from Unstop", "Ananyaa from Unstop"
        # These are always marketing/mentor emails, never real hiring companies
        if re.match(r'^[A-Za-z]+ from [A-Za-z]', display.strip()):
            return None
        looks_like_person = bool(
            re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', display.strip()) or
            re.match(r'^[A-Z][a-z]+ [a-z]+$', display.strip()) or
            re.match(r'^[a-z]+ [a-z]+$', display.strip()) or
            re.match(r'^[A-Z][a-z]+,\s*[A-Z][a-z]+$', display.strip()) or
            re.match(r'^[A-Z][a-z]+$', display.strip()) or
            re.match(r'^[a-z]+$', display.strip())
        )
        if display.lower() not in GENERIC and not looks_like_person:
            for suffix in [" Careers", " Recruiting", " Recruitment", " HR",
                           " Human Resources", " Talent", " Team", " Hiring",
                           " Jobs", " Notifications", " No Reply", " noreply",
                           " Alerts", " Support", " Events"]:
                display = re.sub(re.escape(suffix), "", display, flags=re.IGNORECASE).strip()
            # Block platform/aggregator names from being returned as company
            if display.lower() in PLATFORM_COMPANY_NAMES:
                return None
            if 1 < len(display) < 60:
                return display.strip()

    # Fall back to domain
    m = re.search(r"@([\w\-]+)\.([\w\.\-]+)", sender)
    if m:
        subdomain = m.group(1)
        apex = m.group(2).split(".")[0]
        GENERIC_SUB = {"noreply", "no-reply", "donotreply", "mail", "email",
                       "notifications", "mailer", "smtp", "bounce", "careers",
                       "jobs", "talent", "hiring", "recruit", "info", "hello",
                       "hr", "support", "alerts", "eu", "updates"}
        GENERIC_APEX = {"gmail", "yahoo", "outlook", "hotmail", "rediffmail",
                        "greenhouse", "lever", "workday", "oracle", "com", "co"}
        candidate = None
        if subdomain in GENERIC_SUB or subdomain in GENERIC_APEX:
            if apex not in GENERIC_APEX and len(apex) > 2:
                candidate = apex.capitalize()
        elif subdomain not in GENERIC_APEX and len(subdomain) > 2:
            candidate = subdomain.capitalize()
        # Never return a platform/aggregator name as a company
        if candidate and candidate.lower() not in PLATFORM_COMPANY_NAMES:
            return candidate

    return None


def get_email_body(msg_payload) -> str:
    """Recursively extract body — plain text preferred, HTML stripped as fallback."""
    plain = ""
    html_raw = ""

    if "parts" in msg_payload:
        for part in msg_payload["parts"]:
            mime = part.get("mimeType", "")
            sub_plain, sub_html = _extract_parts(part)
            plain += sub_plain
            html_raw += sub_html
    else:
        plain, html_raw = _extract_parts(msg_payload)

    if plain.strip():
        return plain

    # Strip HTML tags for keyword matching
    if html_raw:
        text = re.sub(r'<[^>]+>', ' ', html_raw)
        text = re.sub(r'&nbsp;', ' ', text)
        text = re.sub(r'&amp;', '&', text)
        text = re.sub(r'&#\d+;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    return ""


def _extract_parts(part) -> tuple:
    plain = ""
    html_raw = ""
    mime = part.get("mimeType", "")

    if "parts" in part:
        for subpart in part["parts"]:
            sp, sh = _extract_parts(subpart)
            plain += sp
            html_raw += sh
    else:
        data = part.get("body", {}).get("data", "")
        if data:
            decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
            if "plain" in mime:
                plain = decoded
            elif "html" in mime:
                html_raw = decoded

    return plain, html_raw


def fetch_and_parse_placement_emails(credentials_dict: dict) -> list[dict]:
    from datetime import datetime, timezone

    creds = Credentials(
        token=credentials_dict["token"],
        refresh_token=credentials_dict.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    )

    service = build("gmail", "v1", credentials=creds)

    queries = [
        (
            "("
            'subject:"thank you for applying" OR '
            'subject:"thanks for applying" OR '
            'subject:"thank you for your application" OR '
            'subject:"thanks for your application" OR '
            'subject:"your application was sent" OR '
            'subject:"your application to" OR '
            'subject:"application received" OR '
            'subject:"application confirmation" OR '
            'subject:"your application" OR '
            'subject:"we received your application" OR '
            'subject:"successfully applied" OR '
            'subject:"interview" OR '
            'subject:"call letter" OR '
            'subject:"shortlisted" OR '
            'subject:"invitation" OR '
            'subject:"selected for" OR '
            'subject:"next round" OR '
            'subject:"online assessment" OR '
            'subject:"assessment" OR '
            'subject:"test link" OR '
            'subject:"coding challenge" OR '
            'subject:"offer letter" OR '
            'subject:"offer of employment" OR '
            'subject:"congratulations" OR '
            'subject:"unfortunately" OR '
            'subject:"regret to inform" OR '
            'subject:"not moving forward" OR '
            'subject:"not selected" OR '
            'subject:"not been selected" OR '
            'subject:"not shortlisted" OR '
            'subject:"we regret" OR '
            'subject:"your application status" OR '
            'subject:"update on your application" OR '
            'subject:"application decision" OR '
            'subject:"decision regarding" OR '
            'subject:"we have reviewed" OR '
            'subject:"after careful consideration" OR '
            'subject:"moving forward with other" OR '
            'subject:"pursue other" OR '
            'subject:"chosen to move" OR '
            'subject:"thank you for applying to" OR '
            'subject:"thanks for applying to" OR '
            'subject:"regarding your application" OR '
            'subject:"application for" OR '
            'subject:"application: status update" OR '
            'subject:"amazon application" OR '
            'subject:"thank you for submitting" OR '
            'subject:"submitting your profile" OR '
            'subject:"your application with" OR '
            'subject:"update from" OR '
            'subject:"thanks from" OR '
            'subject:"received your job application" OR '
            'subject:"we have received your job" OR '
            'subject:"submitting your profile"'
            ") "
            # NOTE: intentionally NOT filtering -category:promotions here.
            # LinkedIn rejection emails ("Your update from X", "Your application to X at Y")
            # sometimes land in Promotions tab. The linkedin_queries below with
            # includeSpamTrash=True act as a safety net, but we want standard queries
            # to catch inbox-delivered rejections too.
        ),
        'from:wellfound.com OR from:ycombinator.com subject:"application"',
        # Indeed application/rejection emails
        # noreply@indeed.com = company-specific rejection/update emails (display name = company)
        # jobalert.indeed.com / alert@indeed.com = job alert spam (blocked by HARD_SPAM_DOMAINS)
        'from:indeed.com subject:"an update on your application"',
        'from:indeed.com subject:"update on your application"',
        'from:indeed.com subject:"your application"',
        'from:indeed.com subject:"indeed application"',
        # Unstop rejection/update emails — real rejections from updates@unstop.email / updates@unstop.events
        'from:unstop.email subject:"update on your application"',
        'from:unstop.events subject:"update on your application"',
        'from:unstop.email subject:"your application"',
        'from:unstop.events subject:"your application"',
        'from:unstop.email OR from:unstop.events',
        # Catch rejection emails where subject is neutral but body has rejection phrases
        '"unfortunately" ("application" OR "candidacy" OR "candidature" OR "position")',
        '"regret to inform" ("application" OR "candidacy" OR "position")',
        '"not moving forward" ("application" OR "candidacy")',
        '"not shortlisted" OR "not been shortlisted"',
        '"decided to pursue other" OR "decided to move forward with other"',
        '"decided to move on with other candidates"',
        '"after careful consideration" ("application" OR "candidacy" OR "role")',
        '"has moved to the next step" "your application"',
    ]

    # LinkedIn rejection emails are auto-archived by Gmail and never appear in Inbox.
    # The Gmail API by default only searches Inbox + Sent + other standard labels.
    # includeSpamTrash=True + no label filter reaches ALL MAIL including archived.
    # We run these as separate API calls with includeSpamTrash=True.
    linkedin_queries = [
        'from:jobs-noreply@linkedin.com subject:"your update from"',
        'from:jobs-noreply@linkedin.com subject:"update from"',
        'from:jobs-noreply@linkedin.com subject:"your application"',
        'from:jobs-noreply@linkedin.com subject:"unfortunately"',
        'from:jobs-noreply@linkedin.com subject:"not moving forward"',
        'from:jobs-noreply@linkedin.com subject:"application status"',
        'from:jobs-noreply@linkedin.com subject:"an update on your application"',
        'from:jobs-noreply@linkedin.com subject:"update on your application"',
        # Broad catch-all for all LinkedIn job notification emails (rejection sender only)
        'from:jobs-noreply@linkedin.com',
        # inmail replies about applications
        'from:inmail-hit-reply@linkedin.com subject:"application"',
        # Indeed archived rejections (specific sender only)
        'from:noreply@indeed.com subject:"an update on your application"',
        'from:noreply@indeed.com subject:"update on your application"',
        'from:noreply@indeed.com subject:"your application"',
        'from:noreply@indeed.com subject:"unfortunately"',
        'from:noreply@indeed.com subject:"application status"',
        # Body-content rejection searches across all senders (archived too)
        # These use includeSpamTrash=True so they reach ALL mail including Promotions/archived
        '"unfortunately, we will not be moving forward with your application"',
        '"unfortunately, we will not be moving forward"',
        '"we will not be moving forward with your application"',
        '"not moving forward with your application"',
        '"we regret to inform you" "application"',
        '"decided to move forward with other" "application"',
        '"not been shortlisted" "application"',
        '"after careful consideration" "application"',
        '"not selected for this" "application"',
        '"your application was not selected"',
        # subject-only: catches "Your update from X" regardless of body
        'subject:"your update from"',
    ]

    seen_ids = set()
    messages = []

    # Standard queries (inbox + sent + categories)
    for query in queries:
        page_token = None
        while True:
            params = {"userId": "me", "q": query, "maxResults": 500}
            if page_token:
                params["pageToken"] = page_token
            results = service.users().messages().list(**params).execute()
            batch = results.get("messages", [])
            for msg in batch:
                if msg["id"] not in seen_ids:
                    seen_ids.add(msg["id"])
                    messages.append(msg)
            page_token = results.get("nextPageToken")
            print(f"[gmail_parser] Fetched {len(messages)} unique IDs...")
            if not page_token or len(messages) >= 3000:
                break

    # LinkedIn queries with includeSpamTrash=True to reach archived/all-mail
    for query in linkedin_queries:
        page_token = None
        while True:
            params = {
                "userId": "me",
                "q": query,
                "maxResults": 500,
                "includeSpamTrash": True,   # KEY: reaches All Mail / archived folders
            }
            if page_token:
                params["pageToken"] = page_token
            results = service.users().messages().list(**params).execute()
            batch = results.get("messages", [])
            for msg in batch:
                if msg["id"] not in seen_ids:
                    seen_ids.add(msg["id"])
                    messages.append(msg)
            page_token = results.get("nextPageToken")
            print(f"[gmail_parser] LinkedIn fetch: {len(messages)} unique IDs total...")
            if not page_token or len(messages) >= 3000:
                break

    print(f"[gmail_parser] Total to process: {len(messages)}")
    parsed_results = []

    def fetch_message_with_retry(msg_id, retries=3, delay=2):
        """Fetch a single message with retry on transient network errors."""
        import time
        for attempt in range(retries):
            try:
                return service.users().messages().get(
                    userId="me", id=msg_id, format="full"
                ).execute()
            except Exception as e:
                err_str = str(e).lower()
                is_transient = any(x in err_str for x in [
                    "getaddrinfo", "connection", "timeout", "reset", "forcibly",
                    "server at gmail", "unable to find", "errno 11001", "errno 10054"
                ])
                if is_transient and attempt < retries - 1:
                    wait = delay * (2 ** attempt)
                    print(f"[RETRY] {msg_id} attempt {attempt+1}/{retries} after {wait}s: {str(e)[:60]}")
                    time.sleep(wait)
                else:
                    raise

    for msg_ref in messages:
        try:
            msg = fetch_message_with_retry(msg_ref["id"])

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            subject = headers.get("Subject", "")
            sender  = headers.get("From", "")
            snippet = msg.get("snippet", "")
            body    = get_email_body(msg["payload"])

            # Always combine body + snippet for maximum rejection phrase coverage
            full_text = body + " " + snippet

            internal_ms = int(msg.get("internalDate", 0))
            email_date = datetime.fromtimestamp(internal_ms / 1000, tz=timezone.utc) if internal_ms else None

            if is_promotional_email(sender, subject):
                print(f"[SKIP promo] {sender[:40]} | {subject[:50]}")
                continue

            is_job_platform = (
                "linkedin" in sender.lower() or
                "indeed" in sender.lower() or
                "unstop" in sender.lower()
            )

            # For LinkedIn/Indeed/Unstop: ALWAYS do deep MIME extraction.
            # Their HTML emails often produce 100-500 chars of navigation junk from
            # get_email_body(), hiding the actual rejection phrase. Deep extract gets all parts.
            def _deep_extract(payload):
                result = ""
                for part in payload.get("parts", []):
                    mime = part.get("mimeType", "")
                    data = part.get("body", {}).get("data", "")
                    if data and ("plain" in mime or "html" in mime):
                        decoded = base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
                        if "html" in mime:
                            decoded = re.sub(r'<[^>]+>', ' ', decoded)
                            decoded = re.sub(r'&nbsp;', ' ', decoded)
                            decoded = re.sub(r'&amp;', '&', decoded)
                            decoded = re.sub(r'&#\d+;', ' ', decoded)
                            decoded = re.sub(r'\s+', ' ', decoded).strip()
                        result += " " + decoded
                    result += _deep_extract(part)
                return result

            if is_job_platform:
                deep_text = _deep_extract(msg["payload"]).strip()
                if deep_text:
                    full_text = deep_text + " " + snippet
                else:
                    full_text = body + " " + snippet
            elif not body.strip() or len(body.strip()) < 100:
                # For other senders with empty/short body, try deep extract too
                deep_text = _deep_extract(msg["payload"]).strip()
                if deep_text:
                    full_text = deep_text + " " + snippet

            # Always append snippet — it's often the most reliable readable text
            if snippet and snippet not in full_text:
                full_text = full_text + " " + snippet

            # SNIPPET FAST-PATH: For LinkedIn/Indeed, the snippet IS the rejection text.
            # Check snippet alone first for high-confidence statuses.
            # CRITICAL: NEVER trust "Applied" from snippet alone.
            # LinkedIn rejection emails begin with "Thank you for your interest in [role]..."
            # (an Applied phrase) BEFORE the "Unfortunately, we will not be moving forward"
            # rejection text. Gmail snippets are ~200 chars and cut off before "Unfortunately",
            # so snippet_status would return "Applied" — masking the real Rejected status.
            # Only use snippet if it detects Rejected / Interview / Selected / OA.
            snippet_status = None
            if is_job_platform and snippet:
                s = parse_email_for_status(subject, snippet)
                if s and s != "Applied":
                    snippet_status = s

            status = snippet_status or parse_email_for_status(subject, full_text)

            # Second pass: if still no status, try subject-only classification
            # (catches rejections where body is paywalled/blocked/empty)
            if not status:
                status = parse_email_for_status(subject, "")

            if not status:
                # Extra debug for "update from" / Indeed emails that should have rejection status
                if "update from" in subject.lower() or "update on your application" in subject.lower():
                    body_preview = full_text[:300].replace("\n", " ")
                    print(f"[SKIP no-match][update-debug] subject={subject[:60]}")
                    print(f"  sender={sender[:50]}")
                    print(f"  body_preview: {body_preview[:200]}")
                else:
                    print(f"[SKIP no-match] {subject[:60]}")
                continue

            company = extract_company_from_email(sender, subject)

            # Unstop fallback: company name is in the body, not subject/sender
            # Body pattern: "the [Company] has decided to move on with other candidates"
            if not company and any(d in sender.lower() for d in ["unstop.com", "unstop.email", "unstop.events"]):
                # Rejection pattern
                m = re.search(
                    r"(?:the\s+)?([A-Z][A-Za-z0-9 &\.]{1,60}?)\s+has decided to move",
                    full_text
                )
                if m:
                    c = m.group(1).strip()
                    if c.lower() not in PLATFORM_COMPANY_NAMES and 1 < len(c) < 60:
                        company = c
                if not company:
                    # Accepted pattern: "your application to [Company] has been accepted"
                    m2 = re.search(
                        r"(?:application to|application for .+ at|at) ([A-Z][A-Za-z0-9 &\.]{1,60}?) (?:has been accepted|have accepted|is accepted)",
                        full_text
                    )
                    if m2:
                        c = m2.group(1).strip()
                        if c.lower() not in PLATFORM_COMPANY_NAMES and 1 < len(c) < 60:
                            company = c
                if not company:
                    # Generic fallback: "[Company] has decided not to move forward"
                    m3 = re.search(
                        r"([A-Z][A-Za-z0-9 &\.]{1,60}?)\s+(?:has decided|have decided|decided)",
                        full_text
                    )
                    if m3:
                        c = m3.group(1).strip()
                        if c.lower() not in PLATFORM_COMPANY_NAMES and 1 < len(c) < 60:
                            company = c

            if not company:
                print(f"[SKIP no-company] {sender[:40]}")
                continue

            print(f"[FOUND] {company} | {status} | {subject[:50]}")
            parsed_results.append({
                "company":        company,
                "status":         status,
                "subject":        subject,
                "sender":         sender,
                "snippet":        snippet[:500],
                "email_date":     email_date,
                "gmail_message_id": msg_ref["id"],
            })

        except Exception as e:
            import traceback
            err_str = str(e)
            # Log transient errors briefly, full trace for unexpected ones
            if any(x in err_str.lower() for x in ["getaddrinfo", "connection", "forcibly", "server at gmail"]):
                print(f"[ERROR-NET] {msg_ref['id']}: {err_str[:80]}")
            else:
                print(f"[ERROR] {msg_ref['id']}: {err_str}")
                print(traceback.format_exc()[:300])
            continue

    print(f"[gmail_parser] Done: {len(parsed_results)} matched out of {len(messages)} scanned")
    return parsed_results