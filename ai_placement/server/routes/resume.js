const express = require('express');
const router  = express.Router();
const { GoogleGenerativeAI } = require('@google/generative-ai');
const authMiddleware = require('../middleware/auth');

const client = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model  = client.getGenerativeModel({ model: 'gemini-2.5-flash' });

// POST /api/resume/analyze
router.post('/analyze', authMiddleware, async (req, res) => {
  try {
    const { resume, jobDescription } = req.body;

    if (!resume || !jobDescription) {
      return res.status(400).json({ error: 'Both resume and jobDescription are required' });
    }

    // FIX: cap input size to prevent token abuse
    if (resume.length > 8000) {
      return res.status(400).json({ error: 'Resume too long (max 8000 characters)' });
    }
    if (jobDescription.length > 4000) {
      return res.status(400).json({ error: 'Job description too long (max 4000 characters)' });
    }

    const prompt = `You are a senior ATS system and career coach.
Analyze this resume against the job description and provide actionable feedback.
RESUME:
${resume}
JOB DESCRIPTION:
${jobDescription}
Respond ONLY with valid JSON, no markdown, no backticks:
{"match_score":<0-100>,"keyword_match":<0-100>,"experience_match":<0-100>,"skills_match":<0-100>,"matched_keywords":["<k1>","<k2>","<k3>","<k4>","<k5>"],"missing_keywords":["<k1>","<k2>","<k3>","<k4>"],"strengths":["<s1>","<s2>","<s3>"],"gaps":["<g1>","<g2>"],"suggestions":["<sug1>","<sug2>","<sug3>"]}`;

    const result = await model.generateContent(prompt);
    const raw = result.response.text().replace(/```json|```/g, '').trim();
    res.json(JSON.parse(raw));
  } catch (err) {
    console.error('[resume/analyze]', err.message);
    res.status(500).json({ error: 'Failed to analyze resume' });
  }
});

module.exports = router;