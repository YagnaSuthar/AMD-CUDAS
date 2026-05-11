import React from 'react';

export default function OptionList({ options, selectedOption, setSelectedOption, disabled }) {
  const safeOptions = Array.isArray(options) ? options : [];

  return (
    <div style={styles.wrap}>
      {safeOptions.map((opt) => (
        <label key={opt} style={{ ...styles.option, ...(disabled ? styles.optionDisabled : {}) }}>
          <input
            type="radio"
            name="aptitude-option"
            value={opt}
            checked={selectedOption === opt}
            onChange={() => setSelectedOption(opt)}
            disabled={disabled}
            style={styles.radio}
          />
          <span>{opt}</span>
        </label>
      ))}
    </div>
  );
}

const styles = {
  wrap: {
    display: 'grid',
    gridTemplateColumns: '1fr',
    gap: 10,
    marginTop: 14,
  },
  option: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    padding: '12px 12px',
    borderRadius: 12,
    border: '1px solid rgba(255,255,255,0.10)',
    background: 'rgba(255,255,255,0.04)',
    cursor: 'pointer',
    userSelect: 'none',
  },
  optionDisabled: {
    opacity: 0.7,
    cursor: 'not-allowed',
  },
  radio: {
    width: 16,
    height: 16,
  },
};
