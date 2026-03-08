const jwt = require('jsonwebtoken');

/**
 * Middleware: verifies the JWT issued by the FastAPI backend.
 * Both backends share the same SECRET_KEY from .env.
 * Attach this to any Express route that should be authenticated.
 *
 * Usage: router.post('/evaluate', authMiddleware, async (req, res) => { ... })
 */
function authMiddleware(req, res, next) {
  const authHeader = req.headers['authorization'];
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid Authorization header' });
  }

  const token = authHeader.split(' ')[1];

  try {
    // Verify using the same secret as the FastAPI backend
    const payload = jwt.verify(token, process.env.SECRET_KEY, { algorithms: ['HS256'] });
    req.userId = payload.user_id;  // attach user_id to request for downstream use
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
}

module.exports = authMiddleware;