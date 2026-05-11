import React from 'react';

export default function QuestionCard({ question, index, total }) {
  if (!question) return null;

  return (
    <div style={styles.card}>
      <div style={styles.meta}>Question {index}/{total}</div>
      <div style={styles.question}>{question.question}</div>
    </div>
  );
}

const styles = {
  card: {
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.10)',
    borderRadius: 14,
    padding: 18,
  },
  meta: {
    fontSize: 13,
    opacity: 0.85,
    marginBottom: 10,
  },
  question: {
    fontSize: 16,
    fontWeight: 600,
    lineHeight: 1.4,
  },
};
