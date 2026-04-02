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
      // If VITE_API_URL exists in the environment (like on Vercel), use it. Otherwise, assume local testing on 8000.
      const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

      const response = await fetch(`${API_BASE_URL}/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ grade: parseInt(grade), topic: topic.trim() })
      });

      const data = await response.json();

      if (!response.ok) {
        let errorMsg = data.error || 'API Error';
        // Handle FastAPI Pydantic Validation [object Object] errors gracefully
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
        <h4>Explanation</h4>
        <p className="explanation">{content.explanation}</p>
        <h4>Multiple Choice Questions</h4>
        <div className="mcq-list">
          {content.mcqs.map((mcq, idx) => (
            <div key={idx} className="mcq-item">
              <p className="question"><strong>Q{idx + 1}:</strong> {mcq.question}</p>
              <ul>
                {mcq.options.map((opt, i) => (
                  <li key={i}>{opt}</li>
                ))}
              </ul>
              <p className="answer"><strong>Correct Answer:</strong> {mcq.answer}</p>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="app-container">
      <header className="header">
        <h1>✨ AI Study Buddy ✨</h1>
        <p>Your interactive learning assistant</p>
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
            <p>The AI is writing your lesson...</p>
          </div>
        )}

        {result && !loading && (
          <div className="results-container">
            <section className="result-section card initial-content">
              <h3>Step 1: Generated Lesson</h3>
              {renderContent(result.initial_content)}
            </section>

            <section className={`result-section card review-content ${result.review?.status === 'pass' ? 'pass' : 'fail'}`}>
              <h3>Step 2: AI Reviewer</h3>
              <div className="status-badge">
                Status: {result.review?.status === 'pass' ? '✅ PASS' : '❌ NEEDS IMPROVEMENT'}
              </div>
              {result.review?.status === 'fail' && (
                <div className="feedback-list">
                  <p><strong>Feedback:</strong></p>
                  <ul>
                    {result.review?.feedback.map((fb, idx) => (
                      <li key={idx}>{fb}</li>
                    ))}
                  </ul>
                </div>
              )}
              {result.review?.status === 'pass' && (
                <p className="pass-text">Perfect! This lesson is ready for you!</p>
              )}
            </section>

            {result.refined_content && (
              <section className="result-section card refined-content">
                <h3>Step 3: Improved Lesson</h3>
                <p className="refined-intro">The generator fixed the lesson based on the reviewer's feedback!</p>
                {renderContent(result.refined_content)}
              </section>
            )}
          </div>
        )}
      </main>
    </div>
  )
}

export default App
