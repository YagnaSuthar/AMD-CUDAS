import React, { useCallback, useState } from 'react';

import api from '../../../../../../utils/api';

function formatCategory(str) {
  return String(str || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bAnd\b/g, '&');
}

export default function AptitudeReport({ report, sessionId }) {
  if (!report) return null;

  const { score, total_questions, attempted, accuracy_percent, category_breakdown } = report;

  const [downloading, setDownloading] = useState(false);

  const downloadReport = useCallback(async () => {
    if (!sessionId) return;

    setDownloading(true);
    try {
      const res = await api.get(`/ai/aptitude/report/${sessionId}/download`, {
        responseType: 'blob',
      });

      const blob = res?.data;
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement('a');
      a.href = url;
      a.download = 'aptitude_report.pdf';
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } finally {
      setDownloading(false);
    }
  }, [sessionId]);

  return (
    <div style={styles.page}>
      <div style={styles.summaryCard}>
        <div style={styles.summaryHeader}>
          <div style={styles.summaryTitle}>Test Summary</div>
          <button
            style={styles.secondaryBtn}
            onClick={downloadReport}
            disabled={!sessionId || downloading}
          >
            {downloading ? 'Downloading...' : 'Download Report'}
          </button>
        </div>

        <div style={styles.summaryGrid}>
          <div style={styles.summaryMetric}>
            <div style={styles.metricLabel}>Score</div>
            <div style={styles.metricValue}>{score ?? 0}</div>
          </div>

          <div style={styles.summaryMetric}>
            <div style={styles.metricLabel}>Accuracy</div>
            <div style={styles.metricValue}>{accuracy_percent ?? 0}%</div>
          </div>

          <div style={styles.summaryMetric}>
            <div style={styles.metricLabel}>Time Taken</div>
            <div style={styles.metricValue}>-</div>
          </div>

          <div style={styles.summaryMetric}>
            <div style={styles.metricLabel}>Attempted</div>
            <div style={styles.metricValue}>{attempted ?? 0}/{total_questions ?? 0}</div>
          </div>
        </div>
      </div>

      {category_breakdown && Object.keys(category_breakdown).length ? (
        <div style={{ marginBottom: 20, ...styles.summaryCard }}>
          <div style={styles.questionsTitle}>Category Breakdown</div>

          <div style={{ display: 'grid', gap: 10, marginTop: 10 }}>
            {Object.entries(category_breakdown).map(([cat, v]) => (
              <div key={cat} style={styles.breakdownRow}>
                <div style={styles.breakdownCat}>{formatCategory(cat)}</div>
                <div style={styles.breakdownMeta}>
                  Attempted: {v.attempted ?? 0} | Correct: {v.correct ?? 0} | Accuracy: {v.accuracy_percent ?? 0}%
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      <div style={styles.questionsCard}>
        <div style={styles.questionsTitle}>Detailed Questions Review</div>

        {report.attempts && report.attempts.length ? (
          <div style={styles.questionsGrid}>
            {report.attempts.map((attempt, idx) => (
              <div key={idx} style={styles.questionCard}>
                <div style={styles.questionHeader}>
                  <div style={styles.questionNumber}>Q{idx + 1}</div>
                  <div style={styles.questionText}>{attempt.question}</div>
                </div>

                <div style={styles.answerHeader}>Your Answer</div>
                <div style={{ ...styles.answerText, ...(attempt.is_correct ? styles.correct : styles.incorrect) }}>
                  {attempt.your_answer || '-'}
                </div>

                <div style={styles.correctHeader}>Correct Answer</div>
                <div style={styles.correctText}>{attempt.correct_answer || '-'}</div>

                <div style={styles.explanationHeader}>Explanation</div>
                <div style={styles.explanationText}>{attempt.explanation || '-'}</div>
              </div>
            ))}
          </div>
        ) : (
          <div style={styles.noQuestions}>No question attempts available.</div>
        )}
      </div>

      <div style={styles.actionsRow}>
        <button style={styles.primaryBtn}>Retry Test</button>
        <button style={styles.secondaryBtn}>Back to Dashboard</button>
      </div>
    </div>
  );
}

const styles = {
  page: {
    padding: 28,
    width: '100%',
    maxWidth: 1100,
    margin: '0 auto',
    color: 'white',
  },
  summaryCard: {
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.10)',
    borderRadius: 16,
    padding: 20,
    marginBottom: 20,
  },
  summaryHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    gap: 12,
    marginBottom: 16,
  },
  summaryTitle: { fontSize: 20, fontWeight: 900 },
  summaryGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(2, 1fr)',
    gap: 16,
  },
  summaryMetric: {
    background: 'rgba(255,255,255,0.05)',
    border: '1px solid rgba(255,255,255,0.10)',
    borderRadius: 14,
    padding: 14,
  },
  metricLabel: { opacity: 0.85, fontSize: 13 },
  metricValue: { fontSize: 20, fontWeight: 900, marginTop: 6 },
  questionsCard: {
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.10)',
    borderRadius: 16,
    padding: 20,
  },
  questionsTitle: { fontSize: 16, fontWeight: 800, marginBottom: 16 },
  breakdownRow: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 12,
    padding: '10px 12px',
    borderRadius: 10,
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.08)',
  },
  breakdownCat: { fontWeight: 800 },
  breakdownMeta: { opacity: 0.9, fontSize: 12 },
  questionsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr',
    gap: 16,
    marginTop: 12,
  },
  questionCard: {
    background: 'rgba(255,255,255,0.04)',
    border: '1px solid rgba(255,255,255,0.08)',
    borderRadius: 12,
    padding: 14,
  },
  questionHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: 8,
  },
  questionNumber: {
    background: '#6C63FF',
    color: 'white',
    padding: '4px 8px',
    borderRadius: 8,
    fontWeight: 700,
    fontSize: 12,
  },
  questionText: {
    fontSize: 14,
    lineHeight: 1.4,
  },
  answerHeader: { fontWeight: 700, marginBottom: 6 },
  answerText: {
    padding: '10px 12px',
    borderRadius: 8,
    border: '1px solid rgba(255,255,255,0.12)',
    background: 'rgba(255,255,255,0.03)',
    fontSize: 13,
    lineHeight: 1.4,
  },
  correct: { color: '#50fa7b' },
  incorrect: { color: '#ff5555' },
  correctHeader: { fontWeight: 700, marginBottom: 6 },
  correctText: { fontSize: 13, lineHeight: 1.4 },
  explanationHeader: { fontWeight: 700, marginBottom: 6 },
  explanationText: { fontSize: 12, opacity: 0.85, lineHeight: 1.4 },
  noQuestions: { opacity: 0.85, textAlign: 'center', padding: 20 },
  actionsRow: {
    display: 'flex',
    gap: 12,
    marginTop: 24,
  },
  primaryBtn: {
    background: '#6C63FF',
    border: 'none',
    color: 'white',
    padding: '10px 14px',
    borderRadius: 12,
    fontWeight: 700,
    cursor: 'pointer',
  },
  secondaryBtn: {
    background: 'rgba(255,255,255,0.08)',
    border: '1px solid rgba(255,255,255,0.12)',
    color: 'white',
    padding: '10px 14px',
    borderRadius: 12,
    fontWeight: 700,
    cursor: 'pointer',
  },
};
