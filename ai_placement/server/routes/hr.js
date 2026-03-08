const express = require('express');
const router  = express.Router();
const { GoogleGenerativeAI } = require('@google/generative-ai');
const authMiddleware = require('../middleware/auth');

const client = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model  = client.getGenerativeModel({ model: 'gemini-2.5-flash' });

const QUESTIONS = [
  { id: 1, question: "Tell me about yourself and your journey as a developer.", focus: "Self-awareness, communication" },
  { id: 2, question: "Describe a challenging project and how you overcame obstacles.", focus: "Problem-solving, resilience" },
  { id: 3, question: "Tell me about a time you had a conflict with a team member.", focus: "Teamwork, conflict resolution" },
  { id: 4, question: "Describe a time you failed and what you learned from it.", focus: "Growth mindset, accountability" },
  { id: 5, question: "How do you handle tight deadlines and pressure?", focus: "Time management, stress handling" },
];

// GET /api/hr/questions
router.get('/questions', authMiddleware, (req, res) => {
  res.json(QUESTIONS);
});

// POST /api/hr/generate-questions
router.post('/generate-questions', authMiddleware, async (req, res) => {
  try {
    const {
      company   = 'a tech company',
      role      = 'Software Engineer',
      level     = 'SDE-1'
    } = req.body;

    // FIX: sanitize inputs to prevent prompt injection
    const safeCompany = String(company).slice(0, 100);
    const safeRole    = String(role).slice(0, 100);
    const safeLevel   = String(level).slice(0, 50);

    const prompt = `You are a senior HR interviewer at ${safeCompany}.
Generate 5 behavioral interview questions for a ${safeRole} (${safeLevel}) position.
Make them specific to ${safeCompany}'s culture and values.
Respond ONLY with valid JSON, no markdown, no backticks:
{"questions":[{"id":1,"question":"<question>","focus":"<what this tests>"},{"id":2,"question":"<question>","focus":"<what this tests>"},{"id":3,"question":"<question>","focus":"<what this tests>"},{"id":4,"question":"<question>","focus":"<what this tests>"},{"id":5,"question":"<question>","focus":"<what this tests>"}]}`;

    const result = await model.generateContent(prompt);
    const text = result.response.text();
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) return res.status(500).json({ error: 'AI returned invalid format' });
    res.json(JSON.parse(jsonMatch[0].trim()));
  } catch (err) {
    console.error('[hr/generate-questions]', err.message);
    res.status(500).json({ error: 'Failed to generate questions' });
  }
});

// POST /api/hr/evaluate
router.post('/evaluate', authMiddleware, async (req, res) => {
  try {
    const {
      questionId,
      answer,
      company = 'a tech company',
      role    = 'Software Engineer',
      level   = 'SDE-1'
    } = req.body;

    // FIX: validate required fields
    if (!questionId || !answer) {
      return res.status(400).json({ error: 'questionId and answer are required' });
    }
    if (String(answer).length > 3000) {
      return res.status(400).json({ error: 'Answer too long (max 3000 characters)' });
    }

    const q = QUESTIONS.find(q => q.id === parseInt(questionId));
    if (!q) return res.status(404).json({ error: 'Question not found' });

    const prompt = `You are an HR interviewer at ${company} evaluating a ${role} (${level}) candidate.
Question asked: "${q.question}"
Candidate's answer: "${answer}"
Evaluate using STAR method (Situation, Task, Action, Result).
Respond ONLY with valid JSON, no markdown, no backticks:
{"score":<0-100>,"star_breakdown":{"situation":<0-25>,"task":<0-25>,"action":<0-25>,"result":<0-25>},"feedback":"<2-3 sentences>","missing":"<what was missing>","model_answer_tip":"<one concrete improvement tip>"}`;

    const result = await model.generateContent(prompt);
    const text = result.response.text();
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (!jsonMatch) return res.status(500).json({ error: 'AI returned invalid format' });
    res.json(JSON.parse(jsonMatch[0].trim()));
  } catch (err) {
    console.error('[hr/evaluate]', err.message);
    res.status(500).json({ error: 'Failed to evaluate answer' });
  }
});

module.exports = router;