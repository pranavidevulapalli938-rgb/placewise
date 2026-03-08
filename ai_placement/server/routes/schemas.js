// schemas.js
exports.evaluationSchema = {
  type: "OBJECT",
  properties: {
    score: { type: "NUMBER" },
    star_breakdown: { type: "OBJECT", properties: { situation: {type: "NUMBER"}, task: {type: "NUMBER"}, action: {type: "NUMBER"}, result: {type: "NUMBER"} } },
    feedback: { type: "STRING" },
    missing: { type: "STRING" },
    model_answer_tip: { type: "STRING" }
  },
  required: ["score", "star_breakdown", "feedback", "missing", "model_answer_tip"]
};

exports.resumeAnalysisSchema = {
  type: "OBJECT",
  properties: {
    match_score: { type: "NUMBER" },
    keyword_match: { type: "NUMBER" },
    experience_match: { type: "NUMBER" },
    skills_match: { type: "NUMBER" },
    matched_keywords: { type: "ARRAY", items: { type: "STRING" } },
    missing_keywords: { type: "ARRAY", items: { type: "STRING" } },
    strengths: { type: "ARRAY", items: { type: "STRING" } },
    gaps: { type: "ARRAY", items: { type: "STRING" } },
    suggestions: { type: "ARRAY", items: { type: "STRING" } }
  },
  required: ["match_score", "matched_keywords", "strengths", "suggestions"]
};