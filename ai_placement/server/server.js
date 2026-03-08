require('dotenv').config();
const express = require('express');
const cors    = require('cors');

const technicalRoutes = require('./routes/technical');
const hrRoutes        = require('./routes/hr');
const resumeRoutes    = require('./routes/resume');

const app = express();

// FIX: restrict CORS to known origins only (not wildcard in production)
const allowedOrigins = [
  process.env.FRONTEND_URL || 'http://localhost:5173',
  'http://localhost:3000',
];

app.use(cors({
  origin: (origin, callback) => {
    // Allow requests with no origin (e.g. mobile apps, curl, extension)
    if (!origin || allowedOrigins.includes(origin)) return callback(null, true);
    callback(new Error('Not allowed by CORS'));
  },
  credentials: true,
}));

app.use(express.json({ limit: '1mb' }));  // FIX: cap body size

// Routes
app.use('/api/technical', technicalRoutes);
app.use('/api/hr',        hrRoutes);
app.use('/api/resume',    resumeRoutes);

// Health check
app.get('/', (req, res) => {
  res.json({ status: 'InterviewAI backend running ✅', version: '1.0.0' });
});

// Global error handler
app.use((err, req, res, next) => {
  console.error('[Server Error]', err.message);
  res.status(500).json({ error: 'Internal server error' });
});

const PORT = process.env.PORT || 3001;
app.listen(PORT, () => {
  console.log(`InterviewAI server running → http://localhost:${PORT}`);
});