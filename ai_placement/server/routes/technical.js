const express = require('express');
const router  = express.Router();
const { GoogleGenerativeAI } = require('@google/generative-ai');
const authMiddleware = require('../middleware/auth');

const client = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);
const model  = client.getGenerativeModel({ model: 'gemini-2.5-flash' });

const PROBLEMS = [
  {
    id: 1, title: "Two Sum", difficulty: "Easy", topic: "Arrays",
    description: "Given an array of integers and a target, return indices of the two numbers that add up to target. You may not use the same element twice.",
    examples: "Input: nums=[2,7,11,15], target=9 → Output: [0,1]",
    constraints: "2 ≤ nums.length ≤ 10⁴ | -10⁹ ≤ nums[i] ≤ 10⁹ | Exactly one solution exists",
    starter: "def two_sum(nums, target):\n    # your solution here\n    pass"
  },
  {
    id: 2, title: "Valid Parentheses", difficulty: "Easy", topic: "Stack",
    description: "Given a string with '()[]{}', determine if it is valid. Brackets must close in correct order and each open bracket must have a corresponding close bracket.",
    examples: "Input: '()[]{}' → true | Input: '([)]' → false | Input: '{[]}' → true",
    constraints: "1 ≤ s.length ≤ 10⁴ | s consists of '()[]{}'",
    starter: "def is_valid(s):\n    # your solution here\n    pass"
  },
  {
    id: 3, title: "Longest Substring Without Repeating Characters", difficulty: "Medium", topic: "Sliding Window",
    description: "Given a string s, find the length of the longest substring without repeating characters.",
    examples: "Input: 'abcabcbb' → 3 ('abc') | Input: 'bbbbb' → 1 | Input: 'pwwkew' → 3",
    constraints: "0 ≤ s.length ≤ 5×10⁴ | s consists of English letters, digits, symbols and spaces",
    starter: "def length_of_longest_substring(s):\n    # your solution here\n    pass"
  },
  {
    id: 4, title: "Binary Tree Level Order Traversal", difficulty: "Medium", topic: "BFS / Trees",
    description: "Given the root of a binary tree, return the level order traversal of its node values (i.e., left to right, level by level).",
    examples: "Input: [3,9,20,null,null,15,7] → [[3],[9,20],[15,7]]",
    constraints: "0 ≤ number of nodes ≤ 2000 | -1000 ≤ Node.val ≤ 1000",
    starter: "def level_order(root):\n    # your solution here\n    pass"
  },
  {
    id: 5, title: "Word Break", difficulty: "Hard", topic: "Dynamic Programming",
    description: "Given string s and a dictionary wordDict, return true if s can be segmented into a space-separated sequence of one or more dictionary words.",
    examples: "Input: s='leetcode', wordDict=['leet','code'] → true | Input: s='applepenapple', wordDict=['apple','pen'] → true",
    constraints: "1 ≤ s.length ≤ 300 | 1 ≤ wordDict.length ≤ 1000",
    starter: "def word_break(s, word_dict):\n    # your solution here\n    pass"
  }
];

// GET /api/technical/problems
router.get('/problems', authMiddleware, (req, res) => {
  const { difficulty, topic } = req.query;
  let result = PROBLEMS;
  if (difficulty) result = result.filter(p => p.difficulty === difficulty);
  if (topic)      result = result.filter(p => p.topic === topic);
  res.json(result);
});

// GET /api/technical/problems/:id
router.get('/problems/:id', authMiddleware, (req, res) => {
  const problem = PROBLEMS.find(p => p.id === parseInt(req.params.id));
  if (!problem) return res.status(404).json({ error: 'Problem not found' });
  res.json(problem);
});

// POST /api/technical/generate-problem
router.post('/generate-problem', authMiddleware, async (req, res) => {
  try {
    const { topic = 'Arrays', difficulty = 'Medium' } = req.body;

    // Input validation
    const validDifficulties = ['Easy', 'Medium', 'Hard'];
    if (!validDifficulties.includes(difficulty)) {
      return res.status(400).json({ error: 'difficulty must be Easy, Medium, or Hard' });
    }

    const prompt = `You are a technical interviewer. Generate a unique coding problem about ${topic} at ${difficulty} difficulty.
Respond ONLY with valid JSON, no markdown, no backticks:
{"title":"<title>","difficulty":"${difficulty}","topic":"${topic}","description":"<description>","examples":"<2 examples>","constraints":"<constraints>","starter":"<python starter code>"}`;

    const result = await model.generateContent(prompt);
    const raw = result.response.text().replace(/```json|```/g, '').trim();
    res.json(JSON.parse(raw));
  } catch (err) {
    console.error('[technical/generate-problem]', err.message);
    res.status(500).json({ error: 'Failed to generate problem' });
  }
});

// POST /api/technical/hint
router.post('/hint', authMiddleware, async (req, res) => {
  try {
    const { problemId, code, message } = req.body;

    // FIX: validate required fields
    if (!problemId || !message) {
      return res.status(400).json({ error: 'problemId and message are required' });
    }

    const problem = PROBLEMS.find(p => p.id === parseInt(problemId));
    if (!problem) return res.status(404).json({ error: 'Problem not found' });

    const prompt = `You are a senior technical interviewer helping a student.
Problem: "${problem.title}" — ${problem.description}
Candidate's current code:
\`\`\`python
${code || 'No code written yet'}
\`\`\`
Candidate says: "${message}"
Give a helpful hint without revealing the full solution. Ask about time/space complexity. Point out edge cases. Be concise — max 120 words.`;

    const result = await model.generateContent(prompt);
    res.json({ reply: result.response.text() });
  } catch (err) {
    console.error('[technical/hint]', err.message);
    res.status(500).json({ error: 'Failed to generate hint' });
  }
});

// POST /api/technical/evaluate
router.post('/evaluate', authMiddleware, async (req, res) => {
  try {
    const { problemId, code } = req.body;

    if (!problemId || !code) {
      return res.status(400).json({ error: 'problemId and code are required' });
    }

    const problem = PROBLEMS.find(p => p.id === parseInt(problemId));
    if (!problem) return res.status(404).json({ error: 'Problem not found' });

    const prompt = `Evaluate this coding solution for "${problem.title}".
Description: ${problem.description}
Submitted code:
\`\`\`python
${code}
\`\`\`
Respond ONLY with valid JSON, no markdown, no backticks:
{"score":<0-100>,"time_complexity":"<big-O>","space_complexity":"<big-O>","correctness":"correct|partial|incorrect","feedback":"<2-3 sentences>","strengths":["<s1>","<s2>"],"improvements":["<i1>","<i2>"],"optimal_hint":"<brief hint if suboptimal>"}`;

    const result = await model.generateContent(prompt);
    const raw = result.response.text().replace(/```json|```/g, '').trim();
    res.json(JSON.parse(raw));
  } catch (err) {
    console.error('[technical/evaluate]', err.message);
    res.status(500).json({ error: 'Failed to evaluate solution' });
  }
});

module.exports = router;