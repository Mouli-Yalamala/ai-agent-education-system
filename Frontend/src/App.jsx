import { useState } from 'react'
import './App.css'

function App() {
  const [grade, setGrade] = useState(5)
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  const handleGenerate = async () => {
    if (!grade || isNaN(parseInt(grade)) || grade < 1 || grade > 12) {
      setError('Please enter a valid Grade Level (1-12).');
      return;
    }
    if (!topic.trim()) {
      setError('Please enter a topic!');
      return;
    }
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

      const response = await fetch(`${API_BASE_URL}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grade: parseInt(grade), topic: topic.trim() })
      });

      const data = await response.json();

      if (!response.ok) {
        let errorMsg = data.error || 'API Error';
        if (data.detail) {
          if (typeof data.detail === 'string') {
            errorMsg = data.detail;
          } else if (Array.isArray(data.detail)) {
            errorMsg = data.detail.map(err => err.msg).join(', ');
          }
        }
        throw new Error(errorMsg);
      }

      setResult(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const renderContent = (content) => {
    if (!content) return null;
    return (
      <div className="content-box">
        <h4>Lesson Explanation</h4>
        <p className="explanation">{content.explanation.text}</p>
        
        <h4>Multiple Choice Questions</h4>
        <div className="mcq-list">
          {content.mcqs.map((mcq, idx) => (
            <div key={idx} className="mcq-item">
              <p className="question"><strong>Q{idx + 1}:</strong> {mcq.question}</p>
              <ul>
                {mcq.options.map((opt, i) => (
                  <li key={i} className={i === mcq.correct_index ? 'correct-option' : ''}>{opt}</li>
                ))}
              </ul>
              <p className="answer"><strong>Correct Answer:</strong> {mcq.options[mcq.correct_index]}</p>
            </div>
          ))}
        </div>

        {content.teacher_notes && (
          <div className="teacher-notes">
            <h4>👨‍🏫 Teacher's Guide</h4>
            <p><strong>Learning Objective:</strong> {content.teacher_notes.learning_objective}</p>
            {content.teacher_notes.common_misconceptions?.length > 0 && (
              <>
                <p><strong>Common Misconceptions:</strong></p>
                <ul>
                  {content.teacher_notes.common_misconceptions.map((misc, i) => (
                    <li key={i}>{misc}</li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>✨ AI Study Buddy ✨</h1>
        <p>Your interactive, safely governed learning assistant</p>
      </header>

      <main className="main-content">
        <section className="input-section card">
          <h2>What do you want to learn today?</h2>
          <div className="form-group">
            <label>Grade Level (1-12)</label>
            <input
              type="number"
              min="1"
              max="12"
              value={grade}
              onChange={(e) => setGrade(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label>Topic</label>
            <input
              type="text"
              placeholder="e.g., The Water Cycle"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
            />
          </div>
          {error && <div className="error-banner">{error}</div>}
          <button
            className="generate-btn"
            onClick={handleGenerate}
            disabled={loading}
          >
            {loading ? 'Thinking...' : 'Generate Magic!'}
          </button>
        </section>

        {loading && (
          <div className="loading-card card">
            <div className="spinner"></div>
            <p>The AI pipeline is writing, reviewing, and scaling your lesson...</p>
          </div>
        )}

        {result && !loading && (
          <div className="results-container">
            {/* The Final Product */}
            <section className="result-section card final-content">
              <h3>{result.final.status === 'approved' ? '✨ Your Generated Lesson' : '❌ Pipeline Rejected'}</h3>
              
              {/* Tags Section */}
              {result.tags && (
                <div className="tags-container">
                  <span className="tag-pill subject">{result.tags.subject}</span>
                  <span className="tag-pill difficulty">{result.tags.difficulty}</span>
                  <span className="tag-pill blooms">{result.tags.blooms_level}</span>
                </div>
              )}

              {result.final.content ? renderContent(result.final.content) : 
                <p className="error-banner">The AI could not generate mathematically safe educational content within 3 refinement attempts. Please try a different topic.</p>
              }
            </section>

            {/* Audit Trail / Behind the Scenes */}
            <section className="result-section card audit-trail">
              <h3>🔍 Behind the Scenes: AI Evaluation Pipeline</h3>
              <p className="trail-desc">Watch how the AI recursively critiqued and refined this content:</p>
              
              <div className="attempts-list">
                {result.attempts.map((attempt, index) => (
                  <div key={index} className={`attempt-card ${attempt.review.pass ? 'pass' : 'fail'}`}>
                    <div className="attempt-header">
                      <h4>Attempt {attempt.attempt}</h4>
                      <span className="status-badge">{attempt.review.pass ? '✅ PASSED' : '❌ FAILED'}</span>
                    </div>
                    
                    <div className="score-bars">
                      <div className={`score-item s-${attempt.review.scores.age_appropriateness}`}>Age Match: {attempt.review.scores.age_appropriateness}/5</div>
                      <div className={`score-item s-${attempt.review.scores.correctness}`}>Correctness: {attempt.review.scores.correctness}/5</div>
                      <div className={`score-item s-${attempt.review.scores.clarity}`}>Clarity: {attempt.review.scores.clarity}/5</div>
                      <div className={`score-item s-${attempt.review.scores.coverage}`}>Coverage: {attempt.review.scores.coverage}/5</div>
                    </div>

                    {!attempt.review.pass && attempt.review.feedback && attempt.review.feedback.length > 0 && (
                       <div className="feedback-errors">
                          <p><strong>Errors to Refine:</strong></p>
                          <ul>
                            {attempt.review.feedback.map((fb, fidx) => (
                              <li key={fidx}><code>{fb.field}</code>: {fb.issue}</li>
                            ))}
                          </ul>
                       </div>
                    )}
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}
      </main>
    </div>
  )
}

export default App
