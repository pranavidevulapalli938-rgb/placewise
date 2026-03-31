import os
import re
import json
import base64
import time
import threading as _threading
import httpx

# ── Groq rate limiter (free tier = 30 req/min, ~6000 TPM) ────────────────────
_groq_lock      = _threading.Lock()
_groq_last_call = 0.0
_GROQ_MIN_GAP   = 5.0   # 5s gap = max 12 req/min — safe under both RPM and TPM limits

def _groq_rate_limit():
    """Block until it's safe to make another Groq API call."""
    global _groq_last_call
    with _groq_lock:
        now  = time.time()
        wait = _GROQ_MIN_GAP - (now - _groq_last_call)
        if wait > 0:
            time.sleep(wait)
        _groq_last_call = time.time()
# ─────────────────────────────────────────────────────────────────────────────
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

# ── IPv4 fix for httplib2 on Windows ─────────────────────────────────────────
import socket as _socket
_orig_getaddrinfo = _socket.getaddrinfo
def _ipv4_only_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, _socket.AF_INET, type, proto, flags)
_socket.getaddrinfo = _ipv4_only_getaddrinfo
# ─────────────────────────────────────────────────────────────────────────────
# ── Groq setup ────────────────────────────────────────────────────────────────
# Groq is free (14,400 req/day, 30 req/min) and uses OpenAI-compatible API.
# Get your free key at: https://console.groq.com
# No quota sharing with other services — completely isolated.

# ── LLM backend — Claude Haiku (Anthropic) ───────────────────────────────
# Cost: ~₹20 per full 624-email sync, ~₹2/month normal use
# Accuracy: ~97% — best in class for email classification
# Get key at: https://console.anthropic.com → API Keys
# Add to .env: ANTHROPIC_API_KEY=sk-ant-...
# Falls back to Groq if Anthropic key missing, then regex if both missing.

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL   = "claude-haiku-4-5-20251001"  # Cheapest + most accurate

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL   = "llama-3.1-8b-instant"   # 14,400 req/day free (70b = only 1,000/day)

def _get_anthropic_key() -> str | None:
    return os.getenv("ANTHROPIC_API_KEY") or None

def _get_groq_key() -> str | None:
    return os.getenv("GROQ_API_KEY") or None

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
    "recooty", "indeedapply", "indeed", "indeed apply",
    "wellfound", "greenhouse", "lever", "workday", "bamboohr", "smartrecruiters",
    "unstop", "unstop events", "naukri", "jobalert", "jobalerts", "job alert",
    "job alerts", "linkedin", "linkedin job alerts", "linkedin jobs", "naukricampus",
    "dare2compete", "cutshort", "hirist", "iimjobs", "foundit", "apna",
    "shine", "monster", "timesjobs", "ambitionbox", "jobsora",
    "recruitee", "jobvite", "icims", "taleo", "successfactors", "pinpoint",
    "ashbyhq", "rippling", "dover", "teamtailor", "comeet", "freshteam",
    "zohorecruit", "occupop", "jazzhr", "jobsoid", "betterteam", "manatal",
    # ATS platforms that send on behalf of companies (global)
    "darwinbox", "keka", "kekahr", "greythr", "sumhr", "hibob", "personio",
    "factorial", "workable", "myworkday", "oracle", "oraclehcm",
    "paycor", "adp", "kronos", "ultipro", "sap", "sapsuccessfactors",
    "hirevue", "mettl", "mymettl", "devskiller", "vervoe", "testgorilla",
    "skillsignal", "criteria", "wayup", "handshake", "joinhandshake",
    "wellfound", "greenhouse-mail", "lever.co", "beamery",
    # Generic display names that are not companies
    "hr team", "recruitment team", "talent acquisition", "hiring team",
    "talent team", "people team", "careers team", "jobs team",
    "no reply", "noreply", "do not reply", "donotreply",
    # EdTech platforms — should never appear as a company name in job tracking
    "greatlearning", "great learning", "coding ninjas", "codingninjas",
    "simplilearn", "upgrad", "scaler", "pwskills", "masai school", "masaischool",
    "coursera", "udemy", "edx", "swayam", "nptel",
    # Generic category words that get extracted as company names
    "courses", "certifications", "certification", "certificate",
    "quora", "quora digest",
    # Generic domain names that get extracted as company via domain fallback
    "careers", "career", "jobs", "hiring", "recruitment", "talent",
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
    # LinkedIn "viewed" emails — hiring team saw the application
    "your application was viewed",
    "application was viewed by",
    # Darwinbox ATS confirmation emails
    "candidate application has been submitted",
    "application has been submitted successfully",
    "submitted successfully",
    # Indeed confirmation emails
    "indeed application:",
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
    # "your application status update is here" — Unstop/platform status emails
    "your application status update is here",
    "application status update is here",
    "your missing application status update",
    "the application status update is here",
    # "your profile has been shortlisted for the next step"
    "shortlisted for the next step",
    # "Application Received:" direct confirmation
    "application received:",
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
    r"(your),\s+(from|engineering|these)\b",  # Mentor spam generic
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
    # Account registration / welcome emails — NOT job application confirmations
    # e.g. "Welcome to Microsoft Careers!" is a portal signup, not a job application
    r"^welcome to ",
    r"^welcome! ",
    r"created your account",
    r"complete your profile",
    r"verify your (email|account)",
    r"confirm your (email|account)",
    r"account (created|activated|verified)",
    r"activate your account",
    r"set up your (account|profile)",
    r"get started (with|on)",
    r"you(r| have) (successfully )?(signed up|registered|created an account)",
    # ── LinkedIn connection / social notifications ─────────────────────────
    # These NEVER contain job application info — pure social noise
    r"accepted your invitation",
    r"accepted your connection",
    r"explore their network",
    r"^you have \d+ new invitation",
    r"^you have an invitation",
    r"^you have a new message",
    r"sent you a connection",
    r"wants to connect",
    r"people you may know",
    r"commented::",                     # LinkedIn comment notifications
    r"💬.+commented",
    # ── Generic congratulations with no job context ────────────────────────
    # "Congratulations!" alone is NOT a job email — real ones say the company name
    r"^congratulations!?\s*$",          # Subject is literally just "Congratulations!"
    r"^congratulations are in order",
    r"you're now registered with",
    r"successfully registered",
    r"registered with bse",
    # ── Insurance / banking / non-job notifications ────────────────────────
    r"pa insurance is issued",
    r"pnr no\.",
    r"(your|a) (train|flight|bus|hotel) (ticket|booking|reservation)",
    # ── Turing assessment links (not job emails, just test reminders) ──────
    r"^your login link is ready",
    r"complete your turing assessment",
    # ── "Update:" prefix LinkedIn emails that aren't application updates ───
    r"^update: your invitation from",
    r"^update: [a-z]+, your missing application",
    r"^update: [a-z]+, the application status update is here\s*$",  # personalized non-updates
]


def is_promotional_email(sender: str, subject: str) -> bool:
    subject_lower = subject.lower()
    sender_lower = sender.lower()

    # ── FAST SUBJECT PRE-CHECK ─────────────────────────────────────────────
    # Catch the most common noise emails instantly before any domain checks.
    # These subject patterns NEVER appear in real job application emails.
    INSTANT_SPAM_SUBJECTS = [
        "accepted your invitation",
        "accepted your connection",
        "explore their network",
        "you have 1 new invitation",
        "you have an invitation",
        "wants to connect",
        "your login link is ready",
        "complete your turing assessment",
        "pa insurance is issued",
        "registered with bse",
        "update: your invitation from",
    ]
    if any(p in subject_lower for p in INSTANT_SPAM_SUBJECTS):
        return True

    # Also block bare "Congratulations!" with nothing after it
    if re.match(r'^congratulations[!.]?\s*$', subject_lower):
        return True


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
        # Global EdTech / bootcamp platforms
        "springboard.com", "lambda.school", "lambdaschool.com",
        "thinkful.com", "galvanize.com", "generalassemb.ly",
        "datacamp.com", "pluralsight.com", "linkedin.com",
        # Hackathon/contest platforms (not job portals)
        "devpost.com", "mlh.io", "major-league-hacking.com",
        # AI/Tech newsletters (not job portals)
        "huggingface.co", "paperswithcode.com", "weights-biases.com",
        # Internshala Student Partner Program (ISP) is a MARKETING program, not a job
        # Real Internshala job emails come from student@internshala.com and say
        # "Congratulations! You have been selected for [Role] at [Company]"
        # ISP emails come from student@mail.internshala.com (note: mail. subdomain)
        "mail.internshala.com",
        # internshala.com (non-mail subdomain) sends real job emails, but
        # trainings@internshala.com is pure EdTech marketing — block it
        "trainings@internshala.com",
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

    # Internshala student@internshala.com sends BOTH real job emails AND marketing.
    # Real emails: "Congratulations! You have been selected for [Role] at [Company]"
    # Marketing: offer letter guarantee promos, ISP, profile boost, application nudges
    if "student@internshala.com" in sender_lower:
        INTERNSHALA_MARKETING_SUBJECTS = [
            "offer letter is guaranteed",
            "confirm your offer letter",
            "your offer letter is confirmed",
            "offer letter after this",
            "guarantee your offer",
            "your application needs action",
            "application is pending for submissio",
            "a quick update for your application boost",
            "high chance of getting shortli",
            "invitation to apply from",
            "your application boost",
            # removed: personalized registration prompt (now handled by generic patterns)
        ]
        if any(p in subject_lower for p in INTERNSHALA_MARKETING_SUBJECTS):
            return True
        # Real Internshala selection emails always say "selected for [Role] at [Company]"
        INTERNSHALA_REAL_SIGNALS = [
            "congratulations! you have been selected for",
            "you have been selected for",
            "shortlisted for interview",
            "interview call from",
            "offer from",
        ]
        if any(s in subject_lower for s in INTERNSHALA_REAL_SIGNALS):
            return False
        # Default: let through (regex will decide if it matches a status)

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
    # IMPORTANT: Microsoft application emails contain phrases like:
    # "if you're selected for an interview" / "if you are selected for an interview"
    # These are conditional future tense — NOT a real job offer.
    # All "selected" phrases must be guarded against "if/should/when/once" prefixes.
    SELECTED_PHRASES = [
        "offer letter", "pleased to offer you", "happy to inform you",
        "we are delighted to offer", "congratulations on your selection",
        "you have been chosen", "welcome aboard",
        "joining date", "your joining", "extend an offer to you",
        "we would like to offer you", "pleased to extend", "selected for the role",
        "selected for the position", "pleased to welcome you",
        "happy to welcome you",
        # Unstop / platform acceptance phrasing
        "has been accepted for the role", "accepted for the position",
        "happy to accept your application", "your profile has been accepted",
        "pleased to accept", "accepted your application",
    ]
    if any(p in text for p in SELECTED_PHRASES):
        return "Selected"

    # These phrases need conditional guards — must NOT be preceded by if/should/when/once/until
    CONDITIONAL_SELECTED = [
        r'you have been selected',
        r"you've been selected",
        r'you are selected',
        r"you're selected",
        r'your application has been accepted',
        r'application has been accepted',
    ]
    CONDITIONAL_PREFIX = r'(?<!if )(?<!should )(?<!when )(?<!once )(?<!until )'
    for pattern in CONDITIONAL_SELECTED:
        if re.search(CONDITIONAL_PREFIX + pattern, text):
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
        # LinkedIn "viewed" notifications — hiring team saw the application
        "your application was viewed",
        "application was viewed by",
        "great job getting noticed by the hiring team",
        # "Indeed Application: [Role]" subject line — apply confirmation from Indeed
        "indeed application:",
        # "Congratulations! Your application for [Role]" — platform apply confirmation
        # (NOT a selection — this is just acknowledgement of submission)
        "congratulations! your application for",
        "congratulations, your application for",
        # "Application Received: [Role]" — direct confirmation
        "application received:",
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

    # ── Darwinbox ATS: noreply@darwinbox.in — extract company from "|Company" in subject ──
    if re.search(r"@darwinbox\.", sender, re.IGNORECASE):
        # Subject format: "Candidate Application has been submitted successfully |CompanyName"
        m = re.search(r"\|\s*([A-Za-z0-9][^\|\n]{1,60}?)\s*$", subject)
        if m:
            c = m.group(1).strip().rstrip(".,")
            if 1 < len(c) < 60 and c.lower() not in PLATFORM_COMPANY_NAMES:
                return c
        # Also try "Application for [Role] at [Company]"
        m2 = re.search(r"(?:application for .+ at|at) ([A-Za-z][^\|\n,\.]{1,60}?)(?:\s*[\|,\.]|\s*$)", subject, re.IGNORECASE)
        if m2:
            c = m2.group(1).strip().rstrip(".,")
            if 1 < len(c) < 60 and c.lower() not in PLATFORM_COMPANY_NAMES:
                return c
        return None  # Don't fall through to "Darwinbox"

    # ── Workday ATS: myworkday.com — company subdomain IS the company ──────────
    if re.search(r"@myworkday\.com|\.myworkday\.com", sender, re.IGNORECASE):
        # Sender: "CompanyName Recruiting <recruiting@companyname.myworkday.com>"
        m = re.match(r'^"?([^"<@\n]+)"?\s*<', sender)
        if m:
            display = m.group(1).strip()
            for suffix in [" Recruiting", " Careers", " HR", " Jobs", " Talent"]:
                display = display.replace(suffix, "").strip()
            if display.lower() not in PLATFORM_COMPANY_NAMES and len(display) > 1:
                return display
        return None

    # ── Greenhouse ATS: greenhouse.io — display name or subject has company ────
    if re.search(r"@greenhouse\.io|@greenhouse-mail\.com", sender, re.IGNORECASE):
        # Subject: "CompanyName | Your application..." or "Thank you for your application at CompanyName"
        m = re.match(r"(?i)^([A-Za-z][A-Za-z0-9 .&'-]{1,40}?)\s*\|", subject)
        if m:
            c = m.group(1).strip()
            if 1 < len(c) < 60 and c.lower() not in PLATFORM_COMPANY_NAMES:
                return c
        m2 = re.search(r"(?:application at|applying to|applied to) ([A-Za-z][^\|,\.!]{1,60}?)(?:\s*[!,\|\.]|\s*$)", subject, re.IGNORECASE)
        if m2:
            c = m2.group(1).strip().rstrip(".,!")
            if 1 < len(c) < 60 and c.lower() not in PLATFORM_COMPANY_NAMES:
                return c
        return None

    # ── Lever ATS: hire.lever.co — display name usually has company ────────────
    if re.search(r"@lever\.co|@hire\.lever\.co", sender, re.IGNORECASE):
        m = re.match(r'^"?([^"<@\n]+)"?\s*<', sender)
        if m:
            display = m.group(1).strip()
            for suffix in [" Recruiting", " Careers", " HR", " Jobs", " Talent", " Team"]:
                display = display.replace(suffix, "").strip()
            if display.lower() not in PLATFORM_COMPANY_NAMES and len(display) > 1:
                return display
        return None

    # ── Handshake: joinhandshake.com — common for US university students ────────
    if re.search(r"@joinhandshake\.com", sender, re.IGNORECASE):
        m = re.search(r"(?:from|at|with) ([A-Za-z][^\|,\.!]{1,60}?)(?:\s*[!,\|\.]|\s*$)", subject, re.IGNORECASE)
        if m:
            c = m.group(1).strip().rstrip(".,!")
            if 1 < len(c) < 60 and c.lower() not in PLATFORM_COMPANY_NAMES:
                return c
        return None

    # ── Indeed: display name IS the company, sender is noreply@indeed.com ────
    # e.g. "Twite AI Technologies <noreply@indeed.com>"
    # Block job alert senders: donotreply@jobalert.indeed.com, alert@indeed.com
    if re.search(r"@indeed\.com|@jobalert\.indeed\.com", sender, re.IGNORECASE):
        # Block job alert senders explicitly
        if re.search(r"(jobalert|alert@indeed|donotreply)", sender, re.IGNORECASE):
            return None
        # "Indeed Application: [Role]" emails — sender display is "Indeed Apply", not a company
        # These are apply-confirmation emails; skip them (no real company to extract)
        if re.search(r"^indeed application:", subject, re.IGNORECASE):
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
        r"|manatal|recruitly|innovexis|optimspace"
        # Global ATS platforms
        r"|workable|workday|myworkday|oracle|oraclecloud|oraclehcm"
        r"|keka|kekahr|darwinbox|greythr|sumhr|zoho|zohorecruitment"
        r"|hibob|personio|factorial|recruitcee|greenhouse|lever|jazz"
        r"|jobscore|jobsoid|jobsync|jobvite|breezyhr|applytojob"
        r"|recruitingbypaycor|paycor|adp|adpvantage|kronos|ultipro"
        r"|sap|sapsuccessfactors|oraclehire|beamery|hirevue|codility"
        r"|hackerrank|hackerearth|mettl|mercer|mymettl|hackerrank|devskiller"
        r"|vervoe|testgorilla|skillsignal|criteria|criteria-corp|hiretrue"
        r"|jobteaser|wayup|handshake|joinhandshake|chegg|glassdoor"
        r"|wellfound|angelist|ycombinator|workatastartup)[\w\.\-]*\.",
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

    # Darwinbox ATS: "Candidate Application has been submitted successfully |CompanyName"
    # Also handles: "Application submitted |CompanyName" or "[anything] |CompanyName"
    m = re.search(r"\|\s*([A-Za-z0-9][^\|\n]{1,60}?)\s*$", subject)
    if m:
        c = m.group(1).strip().rstrip(".,")
        if 1 < len(c) < 60 and c.lower() not in PLATFORM_COMPANY_NAMES:
            return c

    # Darwinbox ATS: "Candidate Application has been submitted successfully |Godigit"
    if re.search(r"(candidate application|application submitted|submitted successfully)", subject, re.IGNORECASE):
        # Also try extracting from body via sender name
        sender_match = re.match(r'^"?([^"<@\n]+)"?\s*<', sender)
        if sender_match:
            display = sender_match.group(1).strip()
            if display.lower() not in PLATFORM_COMPANY_NAMES and len(display) > 1:
                return display

    # "Indeed Application: [Role]" — from indeedapply@indeed.com
    # Company not in subject for these, extract from sender display name
    if re.search(r"^indeed application:", subject, re.IGNORECASE):
        sender_match = re.match(r'^"?([^"<@\n]+)"?\s*<', sender)
        if sender_match:
            display = sender_match.group(1).strip()
            if display.lower() not in PLATFORM_COMPANY_NAMES and len(display) > 1:
                return display

    # "Your application was viewed by [Company]" — LinkedIn viewed notification
    m = re.search(
        r"(?:application was viewed by|viewed by) ([A-Za-z0-9][^\-\n,\.]{1,60}?)(?:\s*[\-,\|]|\s*$|\.|,)",
        subject, re.IGNORECASE
    )
    if m:
        c = m.group(1).strip().rstrip(".,")
        if 1 < len(c) < 60 and c.lower() not in PLATFORM_COMPANY_NAMES:
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
        # Words that look like person names (single capitalized word) but are actually companies/platforms
        NOT_A_PERSON = {
            "careers", "internshala", "wellfound", "naukri", "unstop",
            "linkedin", "indeed", "glassdoor", "foundit", "cutshort",
            "microsoft", "google", "amazon", "apple", "oracle",
            "infosys", "wipro", "accenture", "deloitte", "capgemini",
            "cognizant", "ibm", "payu", "razorpay", "cashfree", "juspay",
            "phonepe", "freshworks", "zoho", "swiggy", "zomato", "flipkart",
            "meesho", "cred", "groww", "zerodha", "upstox", "slice",
        }
        # Check if the first word of display name is a known company/brand
        # "Microsoft Careers" → first_word="microsoft" → NOT a person
        first_word = display.strip().split()[0].lower() if display.strip() else ""
        looks_like_person = bool(
            # Two-word patterns that look like "First Last" — but only if first word is NOT a known brand
            (re.match(r'^[A-Z][a-z]+ [A-Z][a-z]+$', display.strip()) and first_word not in NOT_A_PERSON) or
            (re.match(r'^[A-Z][a-z]+ [a-z]+$', display.strip()) and first_word not in NOT_A_PERSON) or
            re.match(r'^[a-z]+ [a-z]+$', display.strip()) or
            re.match(r'^[A-Z][a-z]+,\s*[A-Z][a-z]+$', display.strip()) or
            (re.match(r'^[A-Z][a-z]+$', display.strip()) and display.lower() not in NOT_A_PERSON) or
            re.match(r'^[a-z]+$', display.strip())
        )
        if display.lower() not in GENERIC and not looks_like_person:
            # Normalize known multi-word company display names to their canonical short form
            # e.g. "EY Talent Attraction and Acquisition" → "EY"
            # e.g. "Ernst & Young" → "EY"
            DISPLAY_NAME_NORMALIZATIONS = [
                (r"^ey\b", "EY"),
                (r"^ernst\s*&?\s*young\b", "EY"),
                (r"^deloitte\b", "Deloitte"),
                (r"^pwc\b", "PwC"),
                (r"^pricewaterhousecoopers\b", "PwC"),
                (r"^kpmg\b", "KPMG"),
                (r"^bain\b", "Bain"),
                (r"^mckinsey\b", "McKinsey"),
                (r"^boston consulting\b", "BCG"),
                (r"^bcg\b", "BCG"),
                (r"^accenture\b", "Accenture"),
                (r"^infosys\b", "Infosys"),
                (r"^wipro\b", "Wipro"),
                (r"^tata consultancy\b|^tcs\b", "TCS"),
                (r"^microsoft\b", "Microsoft"),
                (r"^google\b", "Google"),
                (r"^amazon\b", "Amazon"),
                (r"^goldman sachs\b", "Goldman Sachs"),
                (r"^morgan stanley\b", "Morgan Stanley"),
                (r"^jpmorgan\b|^jp morgan\b", "JPMorgan"),
            ]
            for pattern, normalized in DISPLAY_NAME_NORMALIZATIONS:
                if re.match(pattern, display.strip(), re.IGNORECASE):
                    return normalized
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
    # Handle deep subdomains like donotreply@email.careers.microsoft.com
    # by scanning all domain parts from right-to-left (excluding TLD) to find
    # the first meaningful non-generic part, e.g. "microsoft" from the above.
    m = re.search(r"@([\w\.\-]+)", sender)
    if m:
        full_domain = m.group(1).lower()
        parts = full_domain.split(".")
        # Remove TLD (last part like "com", "in", "io")
        if len(parts) > 1:
            parts = parts[:-1]
        GENERIC_PARTS = {
            "noreply", "no-reply", "donotreply", "mail", "email",
            "notifications", "mailer", "smtp", "bounce", "careers",
            "jobs", "talent", "hiring", "recruit", "info", "hello",
            "hr", "support", "alerts", "eu", "updates",
            "gmail", "yahoo", "outlook", "hotmail", "rediffmail",
            "greenhouse", "lever", "workday", "oracle", "com", "co",
            "www", "app", "api", "secure", "static", "cdn",
        }
        # Scan from right-to-left (most specific brand part is usually second-to-last)
        candidate = None
        for part in reversed(parts):
            if part not in GENERIC_PARTS and len(part) > 2:
                # Capitalize properly: "microsoft" → "Microsoft"
                candidate = part.capitalize()
                break
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


def extract_role_from_text(subject: str, body: str) -> str:
    """
    Extract the job role from email subject + body.
    Returns "(via Gmail)" if no role found.
    Tries subject first (most reliable), then body.
    """
    import re as _re

    # ── Subject patterns ──────────────────────────────────────────────────────
    # "Indeed Application: [Role]"
    m = _re.search(r"^indeed application:\s*(.+)$", subject, _re.IGNORECASE)
    if m:
        r = m.group(1).strip()
        if 3 < len(r) < 80 and "@" not in r:
            return r

    # "Your application to [Role] at [Company]"
    m = _re.search(r"[Yy]our application to (.+?) at [A-Z]", subject)
    if m:
        r = m.group(1).strip()
        if 3 < len(r) < 80 and "@" not in r:
            return r

    # "application for [Role] at / intern / position / role"
    m = _re.search(
        r"[Aa]pplication for (?:the )?(.+?)(?:\s+at\s+|\s+[Ii]ntern\b|\s+[Pp]osition\b|\s+[Rr]ole\b)",
        subject
    )
    if m:
        r = m.group(1).strip().rstrip(".,")
        if 3 < len(r) < 80 and "@" not in r:
            return r

    # "Thanks for applying for [Role]" / "Thank you for applying for [Role]"
    m = _re.search(
        r"[Tt]han(?:ks|k you) for applying (?:for|to) (?:the )?(.+?)(?:\s+at\s+|\s*[!,\|]|\s*$)",
        subject
    )
    if m:
        r = m.group(1).strip().rstrip("!.,")
        if 3 < len(r) < 80 and "@" not in r:
            return r

    # ── Body patterns (only if subject gave nothing) ──────────────────────────
    if body:
        body_lower = body[:3000]  # Only scan first 3000 chars

        # Microsoft-style: "submit your application for INTERN (Job number: 200024208)"
        # or "application for SOFTWARE ENGINEER INTERN (Job number: ...)"
        m = _re.search(
            r"(?:submit(?:ting)? your application for|application for)\s+([A-Z][A-Z0-9 /\-&]{3,80}?)\s*\(Job number",
            body, _re.IGNORECASE
        )
        if m:
            r = m.group(1).strip().rstrip(".,")
            if 3 < len(r) < 80 and "@" not in r:
                return r.title()

        # "application for [Role]" / "applied for [Role]" / "applying for [Role]"
        m = _re.search(
            r"(?:application for|applied for|applying for|apply for) (?:the (?:role|position) of |the )?([A-Za-z][A-Za-z0-9 /\-&]{3,70}?)(?:\s+(?:at|with|position|role|intern)\b|\s*[,\.\n])",
            body_lower, _re.IGNORECASE
        )
        if m:
            r = m.group(1).strip().rstrip(".,")
            JUNK = {"this position", "this role", "this opportunity", "internship", "the role",
                    "a position", "an internship", "this job", "the position"}
            if 3 < len(r) < 80 and "@" not in r and r.lower() not in JUNK:
                return r.title() if r.islower() else r

        # "role of [Role]" / "position of [Role]"
        m = _re.search(
            r"(?:role of|position of|the role:|the position:)\s+([A-Za-z][A-Za-z0-9 /\-&]{3,70}?)(?:\s*[,\.\n]|$)",
            body_lower, _re.IGNORECASE
        )
        if m:
            r = m.group(1).strip().rstrip(".,")
            if 3 < len(r) < 80 and "@" not in r:
                return r.title() if r.islower() else r

        # "[Role] at [Company]" — only if followed by a known company word
        m = _re.search(
            r"([A-Za-z][A-Za-z0-9 /\-&]{3,50}?)\s+(?:intern(?:ship)?|engineer|analyst|developer|consultant|associate|manager|scientist)\b",
            body_lower[:500], _re.IGNORECASE
        )
        if m:
            r = m.group(0).strip().rstrip(".,")
            if 3 < len(r) < 80 and "@" not in r:
                return r.title() if r.islower() else r

    return "(via Gmail)"



# ─────────────────────────────────────────────────────────────────────────────
# GEMINI-BASED EXTRACTION  (replaces all regex company/role/status extraction)
# ─────────────────────────────────────────────────────────────────────────────
# GROQ-BASED EXTRACTION  (free, fast, no quota sharing with ai_placement)
# Get your free key at: https://console.groq.com
# Free tier: 14,400 req/day, 30 req/min — more than enough for PlaceWise
# ─────────────────────────────────────────────────────────────────────────────

LLM_PROMPT = """You are a placement email classifier for a university student's job application tracker.

Given an email, return a JSON object with EXACTLY these fields:

{
  "is_job_email": true,
  "company": "Exact hiring company name",
  "role": "Exact job title",
  "status": "Applied"
}

RULES:

1. is_job_email = true ONLY for real job/internship application emails.
   Set false for: newsletters, course enrollments, bootcamp ads, job alert digests,
   LinkedIn connection invites, EdTech promotions, portal signup confirmations,
   hackathon invites, webinar invites, discount offers.

2. company = the actual EMPLOYER, not the portal or ATS platform.
   - LinkedIn, Indeed, Greenhouse, Lever, Workday, Unstop, Internshala, Recooty, BambooHR are NOT companies — they are platforms.
   - "EY Talent Attraction" → "EY"
   - "Microsoft Careers" → "Microsoft"
   - "Amazon Jobs" → "Amazon"
   - For "your application was sent to [Company]" → [Company] is the answer.
   - For "your application to [Role] at [Company]" → [Company] is the answer.

3. role = the specific job title. Extract from subject or body.
   Examples: "Software Engineer Intern", "Data Analyst", "Data Science Intern"
   For Microsoft emails, search body for "application for [ROLE] (Job number:" pattern.
   If unknown, use "(via Gmail)".

4. status must be EXACTLY one of these five values:
   - "Applied" — application received/submitted/confirmed. Use for:
     * "Thank you for your application" (ALWAYS Applied, even from Microsoft)
     * "Your application was sent to..."
     * "We received your application"
     * "Keep track of your application"
     * "Thank you for applying"
     * "Your application was viewed by [Company]" — hiring team viewed your application, still Applied
     * "Great job getting noticed by the hiring team" — still Applied
     * Any body text saying "if you are selected" or "if selected for interview" — this is FUTURE CONDITIONAL, not a selection. Still Applied.
   - "OA Received" — online assessment/coding test invitation
   - "Interview Scheduled" — confirmed interview invite or shortlisted for interview
   - "Selected" — ONLY for actual job/internship OFFER with offer letter, joining date, or stipend.
     NEVER use Selected for: thank you emails, shortlisting for interview, bootcamp enrollment, EdTech programs, hackathon results
   - "Rejected" — not moving forward, unfortunately, regret to inform

5. If is_job_email is false → set company, role, status all to null.

CRITICAL EXAMPLES:
- Subject "Thank you for your application!" from Microsoft → is_job_email:true, status:"Applied"
- Subject "Your application was sent to Cashfree Payments" → status:"Applied"
- Subject "Thanks for applying at EY" → status:"Applied", company:"EY"
- Subject "Your application was viewed by 72 Dragons" → is_job_email:true, status:"Applied", company:"72 Dragons"
- Subject "Your application was viewed by Cashfree" → is_job_email:true, status:"Applied", company:"Cashfree"
- Subject "Candidate Application has been submitted successfully |Godigit" → is_job_email:true, status:"Applied", company:"Godigit"
- Subject "Indeed Application: Data Science Intern" → is_job_email:true, status:"Applied", role:"Data Science Intern"
- Subject "Indeed Application: Machine Learning Intern" → is_job_email:true, status:"Applied", role:"Machine Learning Intern"
- Subject "You are invited to complete an online assessment" → status:"OA Received"
- Subject "You have been shortlisted for an interview" → status:"Interview Scheduled"
- Subject "We are pleased to offer you the role" → status:"Selected"
- Subject "Unfortunately, we will not be moving forward" → status:"Rejected"
- Subject "LeetCode Weekly Contest" → is_job_email:false
- Subject "Invitation to join our bootcamp" → is_job_email:false
- Subject "John accepted your invitation, explore their network" → is_job_email:false

Return ONLY the JSON object. No markdown, no explanation, no extra text.
"""


def claude_extract_email_info(sender: str, subject: str, body: str) -> dict | None:
    """
    Use Claude Haiku (Anthropic) to extract company, role, and status.
    Cost: ~₹0.033 per email (~₹20 for full 624-email sync).
    Most accurate option — ~97% classification accuracy.
    Returns dict with keys: is_job_email, company, role, status
    Returns None if key missing or call fails.
    """
    api_key = _get_anthropic_key()
    if not api_key:
        return None

    body_snippet = (body or "")[:1500].strip()
    user_content = f"Sender: {sender}\nSubject: {subject}\nBody:\n{body_snippet}"

    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 200,
        "system": LLM_PROMPT,
        "messages": [{"role": "user", "content": user_content}],
    }

    for attempt in range(3):
        try:
            resp = httpx.post(ANTHROPIC_API_URL, headers=headers, json=payload, timeout=15)
            if resp.status_code == 429:
                wait = 10 * (attempt + 1)
                print(f"[CLAUDE 429] Rate limit, waiting {wait}s...")
                time.sleep(wait)
                continue
            resp.raise_for_status()
            raw = resp.json()["content"][0]["text"].strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*```$", "", raw)
            data = json.loads(raw)
            return data
        except Exception as e:
            print(f"[CLAUDE ERROR] {str(e)[:100]}")
            return None

    return None


def groq_extract_email_info(sender: str, subject: str, body: str) -> dict | None:
    """
    Use Groq (Llama 3.1) to extract company, role, and status from a job email.
    Groq free tier: 14,400 req/day, 30 req/min — no quota sharing issues.
    Returns dict with keys: is_job_email, company, role, status
    Returns None if Groq key missing or call fails.
    """
    api_key = _get_groq_key()
    if not api_key:
        return None

    body_snippet = (body or "")[:1500].strip()
    user_content = f"Sender: {sender}\nSubject: {subject}\nBody:\n{body_snippet}"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": LLM_PROMPT},
            {"role": "user",   "content": user_content},
        ],
        "temperature": 0,
        "max_tokens": 200,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(5):
        try:
            _groq_rate_limit()   # enforce 5s gap between calls — safe under RPM and TPM limits
            resp = httpx.post(GROQ_API_URL, headers=headers, json=payload, timeout=15)
            if resp.status_code == 429:
                # Use Groq's retry-after header if present — it tells us exactly how long to wait
                retry_after = int(resp.headers.get("retry-after", 10 * (attempt + 1)))
                print(f"[GROQ 429] Rate limit, waiting {retry_after}s (attempt {attempt+1}/5)...")
                time.sleep(retry_after)
                continue
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
            raw = re.sub(r"\s*```$", "", raw)
            data = json.loads(raw)
            return data
        except Exception as e:
            print(f"[GROQ ERROR] {str(e)[:100]}")
            return None

    print("[GROQ ERROR] All retries exhausted — falling back to regex")
    return None


def fetch_and_parse_placement_emails(credentials_dict: dict, seen_message_ids: set[str] | None = None) -> list[dict]:
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
            'subject:"submitting your profile" OR '
            'subject:"submitted successfully" OR '
            'subject:"candidate application" OR '
            'subject:"application submitted" OR '
            'subject:"application has been submitted" OR '
            'subject:"indeed application" OR '
            'subject:"application for the" OR '
            'subject:"your application for" OR '
            'subject:"thanks for applying" OR '
            'subject:"received your application" OR '
            'subject:"application status update" OR '
            'subject:"your candidature" OR '
            'subject:"your candidacy" OR '
            'subject:"you have been shortlisted" OR '
            'subject:"we have shortlisted" OR '
            'subject:"next steps for your application" OR '
            'subject:"offer of employment" OR '
            'subject:"job offer" OR '
            'subject:"position has been filled" OR '
            'subject:"your recent application" OR '
            'subject:"application update"'
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

    # ── Per-email processing ─────────────────────────────────────────────────
    # ARCHITECTURE: Groq LLM-first with regex fallback
    #   1. is_promotional_email() → fast local filter, skips obvious spam (free)
    #   2. regex fast-path → if regex gives clear status+company, skip LLM entirely
    #   3. groq_extract_email_info() → LLM-based extraction for ambiguous emails
    #   4. regex fallback → if Groq unavailable or fails
    # Groq: free 14,400 req/day, 30 req/min, no quota sharing with ai_placement.

    anthropic_available = _get_anthropic_key() is not None
    groq_available      = _get_groq_key() is not None

    if anthropic_available:
        print("[gmail_parser] Claude Haiku (Anthropic) extraction enabled ✅ (~₹2/month)")
    elif groq_available:
        print("[gmail_parser] Groq (Llama 3.3-70b) extraction enabled ✅ (free)")
    else:
        print("[gmail_parser] No LLM key — using regex fallback ⚠️ (add ANTHROPIC_API_KEY or GROQ_API_KEY)")

    def _deep_extract(payload):
        """Recursively extract all text from MIME parts."""
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

    _seen = seen_message_ids or set()

    for msg_ref in messages:
        try:
            # ── Fast skip: already in DB ──────────────────────────────────────
            if msg_ref["id"] in _seen:
                continue

            msg = fetch_message_with_retry(msg_ref["id"])

            headers  = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            subject  = headers.get("Subject", "")
            sender   = headers.get("From", "")
            snippet  = msg.get("snippet", "")
            body     = get_email_body(msg["payload"])
            full_text = body + " " + snippet

            internal_ms = int(msg.get("internalDate", 0))
            email_date  = datetime.fromtimestamp(internal_ms / 1000, tz=timezone.utc) if internal_ms else None

            # ── Stage 1: Spam filter (fast, local, no API call) ──────────────
            if is_promotional_email(sender, subject):
                print(f"[SKIP promo] {sender[:40]} | {subject[:50]}")
                continue

            # ── Stage 2: Deep body extraction for HTML-heavy emails ──────────
            is_job_platform = any(p in sender.lower() for p in ["linkedin", "indeed", "unstop"])
            if is_job_platform or not body.strip() or len(body.strip()) < 100:
                deep_text = _deep_extract(msg["payload"]).strip()
                if deep_text:
                    full_text = deep_text + " " + snippet

            if snippet and snippet not in full_text:
                full_text = full_text + " " + snippet

            # ── Stage 3: Regex fast-path — skip Groq for easy emails ────────
            # If regex already gives us both a clear status AND a company, Groq
            # adds no value. Only fall through to Groq for ambiguous cases.
            company = role = status = None
            _regex_status  = parse_email_for_status(subject, full_text)
            _regex_company = extract_company_from_email(sender, subject)

            # SUBJECT-OVERRIDE: If the subject clearly signals "Applied",
            # never let the body override it to "Selected".
            # This fixes Microsoft "Thank you for your application!" being
            # classified as Selected because body says "if you are selected".
            # SUBJECT-OVERRIDE: If the subject says "thank you/applied" BUT the body
            # only has CONDITIONAL selected phrases ("if you are selected"),
            # override to Applied. But if the body has a DEFINITIVE acceptance
            # ("has been accepted", "we are pleased to offer"), keep Selected.
            APPLIED_SUBJECTS = [
                "thank you for your application",
                "thanks for your application",
                "thank you for applying",
                "thanks for applying",
                "your application was sent",
                "your application was received",
                "we received your application",
                "application received",
                "application confirmation",
                "keep track of your application",
                "your application has been received",
                "application submitted",
            ]
            # Definitive acceptance phrases — these mean REAL selection even in "applied" subject emails
            DEFINITIVE_SELECTED = [
                "has been accepted", "have been accepted", "been accepted",
                "pleased to offer", "delighted to offer", "offer letter",
                "joining date", "welcome aboard", "you are selected",
                "you have been selected", "pleased to welcome",
            ]
            subject_lower = subject.lower()
            full_text_lower = full_text.lower()
            if (
                _regex_status == "Selected"
                and any(s in subject_lower for s in APPLIED_SUBJECTS)
                and not any(d in full_text_lower for d in DEFINITIVE_SELECTED)
            ):
                _regex_status = "Applied"
                print(f"[STATUS-OVERRIDE] Conditional selected phrase in body → forcing Applied")

            llm_available = anthropic_available or groq_available

            def _call_llm(s, sub, txt):
                """Call Claude Haiku first, fall back to Groq."""
                result = None
                if anthropic_available:
                    result = claude_extract_email_info(s, sub, txt)
                if result is None and groq_available:
                    result = groq_extract_email_info(s, sub, txt)
                return result

            # ── SMART ROUTING ────────────────────────────────────────────────
            # Goal: minimise LLM calls while catching every edge case.
            #
            # SAFE REGEX (skip LLM):
            #   • Strong status: Rejected / OA Received / Interview Scheduled
            #     → These are unambiguous. Regex is 100% reliable.
            #   • "your application was sent to X" → definitely Applied
            #     → LinkedIn EasyApply confirmation. Never says Selected.
            #   • "thank you for applying to X" → definitely Applied
            #
            # MUST USE LLM:
            #   • "your application to [Role] at [Company]" — LinkedIn update email
            #     Body might say "has been accepted" (Selected) or just "applied"
            #   • "your update from [Company]" — could be any status
            #   • No regex company found at all → LLM needed for extraction
            #   • No regex status found at all → LLM needed

            SAFE_APPLIED_SUBJECTS = [
                "your application was sent to",
                "thank you for applying to",
                "thanks for applying to",
                "thank you for applying at",
                "thanks for applying at",
                "thank you for your application",
                "thanks for your application",
                "we received your application",
                "application received",
                "application confirmation",
                "keep track of your application",
                "application submitted",
                "your application has been received",
                # Darwinbox ATS — "Candidate Application has been submitted successfully |CompanyName"
                "candidate application has been submitted",
                "application has been submitted successfully",
                "submitted successfully",
                # Indeed — "Indeed Application: [Role]"
                "indeed application:",
                # Generic ATS confirmation patterns
                "your application for the",
                "application for the",
                "your application has been submitted",
            ]

            AMBIGUOUS_SUBJECTS = [
                "your application to",       # Zetheta case — could be Applied OR Selected
                "your update from",          # LinkedIn update — could be any status
                "application update",        # generic update
                "update on your application",
                "regarding your application",
            ]

            subject_lower_r = subject.lower()
            is_safe_applied = any(s in subject_lower_r for s in SAFE_APPLIED_SUBJECTS)
            is_ambiguous    = any(s in subject_lower_r for s in AMBIGUOUS_SUBJECTS)

            company = role = status = None

            # Path A: Strong regex status → trust regex, skip LLM
            STRONG_STATUSES = {"Rejected", "Interview Scheduled", "OA Received", "Selected"}
            if _regex_status in STRONG_STATUSES and _regex_company:
                company = _regex_company
                status  = _regex_status
                role    = extract_role_from_text(subject, full_text)
                print(f"[REGEX-HIT] {company} | {status} | {subject[:50]}")

            # Path B: Safe Applied subject + company found → trust regex, skip LLM
            elif is_safe_applied and _regex_company and not is_ambiguous:
                company = _regex_company
                status  = "Applied"
                role    = extract_role_from_text(subject, full_text)
                print(f"[REGEX-HIT] {company} | Applied | {subject[:50]}")

            # Path C: Ambiguous subject OR no company/status → use LLM
            elif llm_available and (is_ambiguous or not _regex_company or not _regex_status):
                result = _call_llm(sender, subject, full_text)
                if result and result.get("is_job_email"):
                    company = result.get("company") or _regex_company or None
                    role    = result.get("role") or "(via Gmail)"
                    status  = result.get("status") or None
                    VALID   = {"Applied", "OA Received", "Interview Scheduled", "Selected", "Rejected"}
                    if status not in VALID:
                        status = None
                    tag = "CLAUDE" if anthropic_available else "GROQ"
                    if company:
                        print(f"[{tag}] {company} | {status} | {role[:40]}")
                elif result and result.get("is_job_email") is False:
                    tag = "CLAUDE" if anthropic_available else "GROQ"
                    print(f"[{tag}-SKIP] Not a job email: {subject[:60]}")
                    continue

            # Path D: Has regex result but no LLM — use regex as-is
            elif _regex_status and _regex_company:
                company = _regex_company
                status  = _regex_status
                role    = extract_role_from_text(subject, full_text)
                print(f"[REGEX-HIT] {company} | {status} | {subject[:50]}")

            # ── Stage 5: Pure regex fallback (Gemini unavailable or errored) ──
            if not status:
                # Reuse already-computed regex values; try snippet fast-path for job platforms
                snippet_status = None
                if is_job_platform and snippet:
                    s = parse_email_for_status(subject, snippet)
                    if s and s != "Applied":
                        snippet_status = s
                status = snippet_status or _regex_status or parse_email_for_status(subject, "")
                if not status:
                    print(f"[SKIP no-match] {subject[:60]}")
                    continue

            if not company:
                company = _regex_company or extract_company_from_email(sender, subject)
                # Unstop body fallback
                if not company and any(d in sender.lower() for d in ["unstop.com", "unstop.email", "unstop.events"]):
                    for pattern in [
                        r"(?:the\s+)?([A-Z][A-Za-z0-9 &\.]{1,60}?)\s+has decided to move",
                        r"(?:application to|at) ([A-Z][A-Za-z0-9 &\.]{1,60}?) (?:has been accepted)",
                        r"([A-Z][A-Za-z0-9 &\.]{1,60}?)\s+(?:has decided|have decided)",
                    ]:
                        m = re.search(pattern, full_text)
                        if m:
                            c = m.group(1).strip()
                            if c.lower() not in PLATFORM_COMPANY_NAMES and 1 < len(c) < 60:
                                company = c
                                break

            if not company:
                print(f"[SKIP no-company] {sender[:40]}")
                continue

            if not role:
                role = extract_role_from_text(subject, full_text)

            print(f"[FOUND] {company} | {status} | {subject[:50]}")
            parsed_results.append({
                "company":          company,
                "status":           status,
                "role":             role,
                "subject":          subject,
                "sender":           sender,
                "snippet":          snippet[:500],
                "email_date":       email_date,
                "gmail_message_id": msg_ref["id"],
            })

        except Exception as e:
            import traceback
            err_str = str(e)
            if any(x in err_str.lower() for x in ["getaddrinfo", "connection", "forcibly", "server at gmail"]):
                print(f"[ERROR-NET] {msg_ref['id']}: {err_str[:80]}")
            else:
                print(f"[ERROR] {msg_ref['id']}: {err_str}")
                print(traceback.format_exc()[:300])
            continue

    print(f"[gmail_parser] Done: {len(parsed_results)} matched out of {len(messages)} scanned")
    return parsed_results