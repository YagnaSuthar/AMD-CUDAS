import React from 'react';

export default function ResultView({ result, correctAnswer, explanation }) {
  const isCorrect = !!result;

  return (
    <div style={styles.card}>
      <div style={{ ...styles.title, ...(isCorrect ? styles.correct : styles.incorrect) }}>
        {isCorrect ? 'Correct' : 'Incorrect'}
      </div>

      <div style={styles.row}>
        <div style={styles.label}>Correct Answer</div>
        <div style={styles.value}>{correctAnswer || '-'}</div>
      </div>

      <div style={styles.row}>
        <div style={styles.label}>Explanation</div>
        <div style={styles.value}>{explanation || '-'}</div>
      </div>
    </div>
  );
}

const styles = {
  card: {
    marginTop: 14,
    background: 'rgba(255,255,255,0.06)',
    border: '1px solid rgba(255,255,255,0.10)',
    borderRadius: 14,
    padding: 16,
  },
  title: {
    fontWeight: 700,
    fontSize: 14,
    marginBottom: 10,
  },
  correct: {
    color: '#50fa7b',
  },
  incorrect: {
    color: '#ff5555',
  },
  row: {
    display: 'grid',
    gridTemplateColumns: '140px 1fr',
    gap: 10,
    padding: '8px 0',
    borderTop: '1px solid rgba(255,255,255,0.08)',
  },
  label: {
    opacity: 0.85,
    fontSize: 13,
  },
  value: {
    fontSize: 13,
    lineHeight: 1.5,
  },
};
