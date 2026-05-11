import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import api from '../../../../../utils/api';

import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';

import QuestionCard from './components/QuestionCard';
import OptionList from './components/OptionList';
import ResultView from './components/ResultView';

function formatCategory(str) {
  return String(str || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
    .replace(/\bAnd\b/g, '&');
}

function AccuracyCircle({ value }) {
  const pct = Math.max(0, Math.min(100, Number(value || 0)));
  const data = useMemo(
    () => [
      { name: 'Correct', value: pct },
      { name: 'Incorrect', value: Math.max(0, 100 - pct) },
    ],
    [pct]
  );

  const COLORS = ['#22c55e', '#ef4444'];

  return (
    <div>
      <div
        style={{
          position: 'relative',
          width: '100%',
          height: 220,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              cx="50%"
              cy="50%"
              innerRadius={55}
              outerRadius={75}
              paddingAngle={3}
              dataKey="value"
              isAnimationActive={false}
            >
              {data.map((_, index) => (
                <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
              ))}
            </Pie>
          </PieChart>
        </ResponsiveContainer>

        <div style={{ position: 'absolute', textAlign: 'center', pointerEvents: 'none' }}>
          <div style={{ fontSize: 22, fontWeight: 900, color: 'var(--text-primary)' }}>{Math.round(pct)}%</div>
          <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>Accuracy</div>
        </div>
      </div>

      <div style={{ textAlign: 'center', marginTop: 6 }}>
        <div style={{ fontWeight: 800, fontSize: 14, color: 'var(--text-primary)' }}>Overall Accuracy</div>
        <div style={{ opacity: 0.8, fontSize: 12, marginTop: 4, color: 'var(--text-secondary)' }}>
          Based on attempted questions
        </div>
      </div>
    </div>
  );
}

export default function AptitudePractice() {
  const [sessionId, setSessionId] = useState(null);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [selectedOption, setSelectedOption] = useState('');
  const [result, setResult] = useState(null);
  const [showResult, setShowResult] = useState(false);
  const [questionIndex, setQuestionIndex] = useState(0);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [mode, setMode] = useState('practice');
  const [timeLimit, setTimeLimit] = useState(600);
  const [remainingTime, setRemainingTime] = useState(600);
  const [testStarted, setTestStarted] = useState(false);
  const [selectedNumber, setSelectedNumber] = useState(10);
  const [sessionCompleted, setSessionCompleted] = useState(false);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');
  const [downloadingReport, setDownloadingReport] = useState(false);
  const [expandedAttemptIndex, setExpandedAttemptIndex] = useState(null);

  const timerRef = useRef(null);

  const hasActiveSession = !!sessionId && !report;

  const formatTime = useCallback((sec) => {
    const s = Math.max(0, Number(sec || 0));
    const mm = String(Math.floor(s / 60)).padStart(2, '0');
    const ss = String(s % 60).padStart(2, '0');
    return `${mm}:${ss}`;
  }, []);

  const safeQuestionText = useMemo(() => {
    return currentQuestion?.question || '';
  }, [currentQuestion]);

  const bestWorstInsight = useMemo(() => {
    const breakdown = report?.category_breakdown;
    if (!breakdown || !Object.keys(breakdown).length) return null;

    const rows = Object.entries(breakdown)
      .map(([cat, v]) => ({
        cat,
        attempted: Number(v?.attempted ?? 0),
        accuracy: Number(v?.accuracy_percent ?? 0),
      }))
      .filter((x) => x.attempted > 0);

    if (!rows.length) return null;

    let best = rows[0];
    let worst = rows[0];
    for (const r of rows) {
      if (r.accuracy > best.accuracy) best = r;
      if (r.accuracy < worst.accuracy) worst = r;
    }

    return { best, worst };
  }, [report]);

  const fetchReport = useCallback(async (sid) => {
    if (!sid) return;

    // Stop timer as soon as we decide to show report.
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    try {
      const res = await api.get(`/ai/aptitude/report/${sid}`);
      setReport(res?.data || {});
    } catch (e) {
      setReport({});
      setErrorMessage(e?.response?.data?.detail || e?.message || 'Failed to fetch report');
    }
  }, []);

  const endByTimeout = useCallback(async () => {
    if (!sessionId) return;
    setErrorMessage('');
    setLoading(true);
    try {
      setSessionCompleted(true);
      await fetchReport(sessionId);
    } finally {
      setLoading(false);
    }
  }, [sessionId, fetchReport]);

  const startSession = useCallback(async () => {
    setLoading(true);
    setErrorMessage('');
    setReport(null);
    setShowResult(false);
    setResult(null);
    setSelectedOption('');
    setSessionCompleted(false);

    try {
      const res = await api.post('/ai/aptitude/start', {
        total_questions: selectedNumber,
      });

      const data = res?.data;
      if (!data?.session_id || !data?.question_id) {
        throw new Error('Invalid start response');
      }

      setSessionId(data.session_id);
      setCurrentQuestion(data);
      setQuestionIndex(Number(data.current_index || 1));
      setTotalQuestions(Number(data.total_questions || 0));
      setTestStarted(true);
      setRemainingTime(Number(timeLimit || 0));
    } catch (e) {
      setErrorMessage(e?.response?.data?.detail || e?.message || 'Failed to start session');
      setSessionId(null);
      setCurrentQuestion(null);
      setQuestionIndex(0);
      setTotalQuestions(0);
      setTestStarted(false);
    } finally {
      setLoading(false);
    }
  }, [selectedNumber, timeLimit]);

  const submitAnswer = useCallback(async ({ silent } = { silent: false }) => {
    if (!sessionId || !currentQuestion?.question_id || !selectedOption) return null;

    setLoading(true);
    setErrorMessage('');

    try {
      const res = await api.post('/ai/aptitude/answer', {
        session_id: sessionId,
        question_id: currentQuestion.question_id,
        selected_option: selectedOption,
      });

      const data = res?.data;
      if (!data) throw new Error('Empty answer response');

      if (!silent) {
        setResult({
          correct: !!data.correct,
          correct_answer: data.correct_answer,
          explanation: data.explanation,
        });
        setShowResult(true);
      }

      if (data.is_completed) {
        setSessionCompleted(true);
        await fetchReport(sessionId);
      }

      return data;
    } catch (e) {
      setErrorMessage(e?.response?.data?.detail || e?.message || 'Failed to submit answer');
      return null;
    } finally {
      setLoading(false);
    }
  }, [sessionId, currentQuestion, selectedOption, fetchReport]);

  const fetchNextQuestion = useCallback(async () => {
    if (!sessionId) return;

    setLoading(true);
    setErrorMessage('');

    try {
      const res = await api.get(`/ai/aptitude/next?session_id=${sessionId}`);
      const data = res?.data;

      console.log('Next question response:', data);

      if (!data?.question_id) {
        setSessionCompleted(true);
        await fetchReport(sessionId);
        return;
      }

      setCurrentQuestion(data);
      setSelectedOption('');
      setResult(null);
      setShowResult(false);
      setQuestionIndex(Number(data.current_index || questionIndex + 1));
      setTotalQuestions(Number(data.total_questions || totalQuestions));
    } catch (e) {
      const detail = e?.response?.data?.detail || e?.message || 'Failed to fetch next question';
      const status = e?.response?.status;

      // If backend indicates no more questions / completed session, treat as completion.
      if (status === 404 || status === 400) {
        setSessionCompleted(true);
        await fetchReport(sessionId);
        return;
      }

      setErrorMessage(detail);
    } finally {
      setLoading(false);
    }
  }, [sessionId, questionIndex, totalQuestions, fetchReport]);

  const handleTestNext = useCallback(async () => {
    if (!sessionId || !currentQuestion?.question_id) return;
    if (!selectedOption) return;

    const data = await submitAnswer({ silent: true });
    if (!data) return;

    setSelectedOption('');

    if (data.is_completed || (totalQuestions > 0 && questionIndex >= totalQuestions)) {
      setSessionCompleted(true);
      await fetchReport(sessionId);
      return;
    }

    await fetchNextQuestion();
  }, [sessionId, currentQuestion, selectedOption, submitAnswer, fetchNextQuestion, fetchReport, questionIndex, totalQuestions]);

  const resetAll = useCallback(() => {
    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    setSessionId(null);
    setCurrentQuestion(null);
    setSelectedOption('');
    setResult(null);
    setShowResult(false);
    setQuestionIndex(0);
    setTotalQuestions(0);
    setTestStarted(false);
    setSessionCompleted(false);
    setRemainingTime(Number(timeLimit || 0));
    setReport(null);
    setErrorMessage('');
  }, [timeLimit]);

  const handleDownloadReport = useCallback(async () => {
    if (!sessionId) return;

    setDownloadingReport(true);
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
    } catch (err) {
      console.error('Download failed:', err);
    } finally {
      setDownloadingReport(false);
    }
  }, [sessionId]);

  // Timer lifecycle
  useEffect(() => {
    if (!testStarted) return;
    if (mode !== 'test') return;
    if (report) return;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }

    timerRef.current = setInterval(() => {
      setRemainingTime((prev) => {
        const next = Number(prev || 0) - 1;
        return next;
      });
    }, 1000);

    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [testStarted, mode, report]);

  // Auto end on timeout
  useEffect(() => {
    if (!testStarted) return;
    if (mode !== 'test') return;
    if (report) return;
    if (remainingTime > 0) return;

    if (timerRef.current) {
      clearInterval(timerRef.current);
      timerRef.current = null;
    }
    endByTimeout();
  }, [remainingTime, testStarted, mode, report, endByTimeout]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, []);

  const canSubmit = hasActiveSession && !loading && !!selectedOption && !showResult;
  const canNextPractice = hasActiveSession && !loading && showResult && !report;
  const canNextTest = hasActiveSession && !loading && !!selectedOption && !report;

  return (
    <div style={styles.page}>
      <div style={styles.headerRow}>
        <div>
          <div style={styles.title}>Aptitude Practice</div>
          <div style={styles.subtitle}>Answer one question at a time and review your result instantly.</div>
        </div>
        <div style={styles.headerActions}>
          {testStarted && mode === 'test' && !report ? (
            <div style={styles.timerPill}>
              ⏱️ {formatTime(remainingTime)} remaining
            </div>
          ) : null}
          <button style={styles.secondaryBtn} onClick={resetAll} disabled={loading}>
            Reset
          </button>
        </div>
      </div>

      {(!loading && !report && !currentQuestion?.question && testStarted && !sessionCompleted && errorMessage) ? (
        <div style={styles.error}>{errorMessage}</div>
      ) : null}

      {!testStarted && !report ? (
        <div style={styles.configCard}>
          <div style={styles.configTitle}>Test Configuration</div>

          <div style={styles.configGrid}>
            <div style={styles.configField}>
              <div style={styles.configLabel}>Number of Questions</div>
              <select
                value={selectedNumber}
                onChange={(e) => setSelectedNumber(Number(e.target.value))}
                style={styles.select}
                disabled={loading}
              >
                {[5, 10, 15, 20].map((n) => (
                  <option key={n} value={n}>{n}</option>
                ))}
              </select>
            </div>

            <div style={styles.configField}>
              <div style={styles.configLabel}>Mode</div>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value)}
                style={styles.select}
                disabled={loading}
              >
                <option value="practice">Practice Mode (no timer)</option>
                <option value="test">Test Mode (timer enabled)</option>
              </select>
            </div>

            <div style={styles.configField}>
              <div style={styles.configLabel}>Time Limit</div>
              <select
                value={timeLimit}
                onChange={(e) => {
                  const v = Number(e.target.value);
                  setTimeLimit(v);
                  setRemainingTime(v);
                }}
                style={styles.select}
                disabled={loading || mode !== 'test'}
              >
                <option value={300}>5 min</option>
                <option value={600}>10 min</option>
                <option value={900}>15 min</option>
              </select>
            </div>
          </div>

          <div style={styles.actionsRow}>
            <button style={styles.primaryBtn} onClick={startSession} disabled={loading}>
              {loading ? 'Starting...' : 'Start Test'}
            </button>
          </div>
        </div>
      ) : null}

      {testStarted && sessionId && !report && !!currentQuestion?.question ? (
        <div style={styles.grid}>
          <div style={styles.left}>
            <QuestionCard
              question={{ question: safeQuestionText }}
              index={questionIndex || 1}
              total={totalQuestions || 0}
            />

            <OptionList
              options={currentQuestion?.options}
              selectedOption={selectedOption}
              setSelectedOption={setSelectedOption}
              disabled={loading || (mode === 'practice' && showResult)}
            />

            <div style={styles.actionsRow}>
              {mode === 'practice' ? (
                <button style={styles.primaryBtn} onClick={() => submitAnswer({ silent: false })} disabled={!canSubmit}>
                  {loading ? 'Submitting...' : 'Submit'}
                </button>
              ) : null}

              <button
                style={styles.secondaryBtn}
                onClick={mode === 'test' ? handleTestNext : fetchNextQuestion}
                disabled={mode === 'test' ? !canNextTest : !canNextPractice}
              >
                {loading ? 'Loading...' : 'Next'}
              </button>
            </div>

            {mode === 'practice' && showResult ? (
              <ResultView
                result={result?.correct}
                correctAnswer={result?.correct_answer}
                explanation={result?.explanation}
              />
            ) : null}
          </div>

          <div style={styles.right}>
            <div style={styles.sideCard}>
              <div style={styles.sideTitle}>Session</div>
              <div style={styles.sideRow}>
                <div style={styles.sideLabel}>Progress</div>
                <div style={styles.sideValue}>{questionIndex}/{totalQuestions || '-'}</div>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {report ? (
        <div style={styles.reportCard}>
          <div style={styles.reportTitle}>Final Report</div>

          <div style={styles.reportGrid}>
            <div style={styles.reportMetric}>
              <div style={styles.metricLabel}>Score</div>
              <div style={styles.metricValue}>{report.score ?? 0}</div>
            </div>
            <div style={styles.reportMetric}>
              <div style={styles.metricLabel}>Accuracy</div>
              <div style={styles.metricValue}>{report.accuracy_percent ?? 0}%</div>
            </div>
            <div style={styles.reportMetric}>
              <div style={styles.metricLabel}>Attempted</div>
              <div style={styles.metricValue}>{report.attempted ?? 0}/{report.total_questions ?? 0}</div>
            </div>
          </div>

          {report.category_breakdown && Object.keys(report.category_breakdown).length ? (
            <div style={{ display: 'grid', gridTemplateColumns: '0.55fr 1.45fr', gap: 16, marginTop: 14 }}>
              <div style={styles.sideCard}>
                <AccuracyCircle value={report.accuracy_percent ?? 0} />
              </div>

              <div style={styles.sideCard}>
                <div style={styles.sideTitle}>Category Accuracy</div>
                <div style={{ width: '100%', height: 240, marginTop: 10 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart
                      data={Object.entries(report.category_breakdown).map(([cat, v]) => ({
                        category: formatCategory(cat),
                        accuracy: Number(v?.accuracy_percent ?? 0),
                      }))}
                      margin={{ top: 10, right: 10, left: 0, bottom: 10 }}
                    >
                      <CartesianGrid stroke="rgba(255,255,255,0.08)" vertical={false} />
                      <XAxis
                        dataKey="category"
                        tick={{ fill: 'rgba(255,255,255,0.8)', fontSize: 12 }}
                        axisLine={{ stroke: 'rgba(255,255,255,0.12)' }}
                        tickLine={false}
                      />
                      <YAxis
                        domain={[0, 100]}
                        tick={{ fill: 'rgba(255,255,255,0.8)', fontSize: 12 }}
                        axisLine={{ stroke: 'rgba(255,255,255,0.12)' }}
                        tickLine={false}
                      />
                      <Tooltip
                        contentStyle={{
                          background: 'rgba(15, 15, 20, 0.95)',
                          border: '1px solid rgba(255,255,255,0.12)',
                          borderRadius: 10,
                          color: 'white',
                        }}
                        formatter={(val) => [`${Number(val).toFixed(2)}%`, 'Accuracy']}
                      />
                      <Bar dataKey="accuracy" fill="#6C63FF" radius={[8, 8, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          ) : null}

          {bestWorstInsight ? (
            <div style={{ marginTop: 14, ...styles.sideCard }}>
              <div style={styles.sideTitle}>Insights</div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginTop: 10 }}>
                <div style={styles.insightBox}>
                  <div style={styles.insightLabel}>Best Performing</div>
                  <div style={styles.insightValue}>{formatCategory(bestWorstInsight.best.cat)}</div>
                  <div style={styles.insightMeta}>{bestWorstInsight.best.accuracy}% accuracy</div>
                </div>

                <div style={styles.insightBox}>
                  <div style={styles.insightLabel}>Needs Improvement</div>
                  <div style={styles.insightValue}>{formatCategory(bestWorstInsight.worst.cat)}</div>
                  <div style={styles.insightMeta}>{bestWorstInsight.worst.accuracy}% accuracy</div>
                </div>
              </div>
            </div>
          ) : null}

          <div style={{ marginTop: 14, ...styles.sideCard }}>
            <div style={styles.sideTitle}>Category Breakdown</div>
            {report.category_breakdown && Object.keys(report.category_breakdown).length ? (
              <div style={{ display: 'grid', gap: 10, marginTop: 10 }}>
                {Object.entries(report.category_breakdown).map(([cat, v]) => (
                  <div key={cat} style={styles.breakdownRow}>
                    <div style={styles.breakdownCat}>{formatCategory(cat)}</div>
                    <div style={styles.breakdownMeta}>
                      Attempted: {v.attempted ?? 0} | Correct: {v.correct ?? 0} | Accuracy: {v.accuracy_percent ?? 0}%
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ opacity: 0.85, marginTop: 8 }}>No breakdown available.</div>
            )}
          </div>

          <div style={styles.actionsRow}>
            <button style={styles.primaryBtn} onClick={resetAll} disabled={loading}>
              Start New Session
            </button>

            <button
              onClick={handleDownloadReport}
              disabled={!sessionId || downloadingReport}
              style={styles.secondaryBtn}
            >
              {downloadingReport ? 'Downloading...' : 'Download Report (PDF)'}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

const styles = {
  page: {
    padding: 28,
    width: '100%',
    maxWidth: 1100,
    margin: '0 auto',
    color: 'var(--text-primary)',
  },
  headerRow: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 16,
    marginBottom: 16,
  },
  title: { fontSize: 22, fontWeight: 800, color: 'var(--text-primary)' },
  subtitle: { opacity: 0.8, marginTop: 6, color: 'var(--text-secondary)' },
  headerActions: { display: 'flex', gap: 10 },
  timerPill: {
    padding: '10px 12px',
    borderRadius: 12,
    background: 'var(--card-bg)',
    border: '1px solid var(--border-color)',
    fontWeight: 700,
    whiteSpace: 'nowrap',
    color: 'var(--text-primary)',
  },

  grid: {
    display: 'grid',
    gridTemplateColumns: '1.3fr 0.7fr',
    gap: 16,
    marginTop: 12,
  },
  left: {},
  right: {},

  centerCard: {
    marginTop: 14,
    background: 'var(--card-bg)',
    border: '1px solid var(--border-color)',
    borderRadius: 16,
    padding: 20,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 16,
  },
  centerText: { fontWeight: 600, color: 'var(--text-primary)' },

  configCard: {
    marginTop: 14,
    background: 'var(--card-bg)',
    border: '1px solid var(--border-color)',
    borderRadius: 16,
    padding: 20,
  },
  configTitle: { fontSize: 16, fontWeight: 900, marginBottom: 14, color: 'var(--text-primary)' },
  configGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, minmax(0, 1fr))',
    gap: 12,
  },
  configField: {
    display: 'grid',
    gap: 8,
  },
  configLabel: { fontSize: 13, opacity: 0.85, fontWeight: 700, color: 'var(--text-secondary)' },
  select: {
    width: '100%',
    padding: '10px 12px',
    borderRadius: 12,
    background: 'var(--bg-input)',
    border: '1px solid var(--border-color)',
    color: 'var(--text-primary)',
    outline: 'none',
  },

  actionsRow: {
    display: 'flex',
    gap: 10,
    marginTop: 14,
  },

  primaryBtn: {
    background: 'var(--accent)',
    border: 'none',
    color: '#fff',
    padding: '10px 14px',
    borderRadius: 12,
    fontWeight: 700,
    cursor: 'pointer',
  },
  secondaryBtn: {
    background: 'var(--card-bg)',
    border: '1px solid var(--border-color)',
    color: 'var(--text-primary)',
    padding: '10px 14px',
    borderRadius: 12,
    fontWeight: 700,
    cursor: 'pointer',
  },

  insightBox: {
    background: 'var(--card-bg)',
    border: '1px solid var(--border-color)',
    borderRadius: 12,
    padding: 12,
  },
  insightLabel: { opacity: 0.85, fontSize: 12, fontWeight: 800, color: 'var(--text-secondary)' },
  insightValue: { marginTop: 6, fontSize: 14, fontWeight: 900, color: 'var(--text-primary)' },
  insightMeta: { marginTop: 4, opacity: 0.8, fontSize: 12, color: 'var(--text-secondary)' },

  attemptCard: {
    borderRadius: 12,
    background: 'var(--card-bg)',
    overflow: 'hidden',
  },
  attemptHeaderBtn: {
    width: '100%',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 12,
    padding: 12,
    background: 'transparent',
    border: 'none',
    color: 'var(--text-primary)',
    cursor: 'pointer',
    textAlign: 'left',
  },
  attemptHeaderLeft: { display: 'flex', gap: 10, alignItems: 'flex-start', flex: 1 },
  attemptHeaderRight: { display: 'flex', gap: 10, alignItems: 'center' },
  attemptQNum: {
    background: 'var(--accent)',
    border: '1px solid var(--accent)',
    padding: '4px 8px',
    borderRadius: 10,
    fontWeight: 900,
    fontSize: 12,
    whiteSpace: 'nowrap',
    color: '#fff',
  },
  attemptQText: { fontSize: 13, lineHeight: 1.45, opacity: 0.95, color: 'var(--text-primary)' },
  attemptBadge: {
    padding: '4px 8px',
    borderRadius: 999,
    fontSize: 12,
    fontWeight: 900,
    border: '1px solid var(--border-color)',
    whiteSpace: 'nowrap',
  },
  correctBadge: { background: 'var(--success)', color: 'var(--success-text)', borderColor: 'var(--success-border)' },
  wrongBadge: { background: 'var(--error)', color: 'var(--error-text)', borderColor: 'var(--error-border)' },
  attemptChevron: { opacity: 0.85, fontSize: 18, fontWeight: 900, minWidth: 18, textAlign: 'center', color: 'var(--text-secondary)' },
  attemptBody: {
    borderTop: '1px solid var(--border-color)',
    padding: 12,
    display: 'grid',
    gap: 10,
  },
  attemptRow: { display: 'grid', gap: 4 },
  attemptLabel: { opacity: 0.85, fontSize: 12, fontWeight: 800, color: 'var(--text-secondary)' },
  attemptValue: { fontSize: 13, lineHeight: 1.45, color: 'var(--text-primary)' },
  correctText: { color: 'var(--success-text)', fontWeight: 800 },
  wrongText: { color: 'var(--error-text)', fontWeight: 800 },

  error: {
    background: 'var(--error)',
    border: '1px solid var(--error-border)',
    padding: '10px 12px',
    borderRadius: 12,
    marginTop: 10,
    marginBottom: 10,
    color: 'var(--error-text)',
  },

  sideCard: {
    background: 'var(--card-bg)',
    border: '1px solid var(--border-color)',
    borderRadius: 14,
    padding: 16,
  },
  sideTitle: { fontWeight: 800, marginBottom: 10, color: 'var(--text-primary)' },
  sideRow: {
    display: 'grid',
    gridTemplateColumns: '120px 1fr',
    gap: 10,
    padding: '8px 0',
    borderTop: '1px solid var(--border-color)',
  },
  sideLabel: { opacity: 0.85, fontSize: 13, color: 'var(--text-secondary)' },
  sideValue: { fontSize: 13, color: 'var(--text-primary)' },

  reportCard: {
    marginTop: 14,
    background: 'var(--card-bg)',
    border: '1px solid var(--border-color)',
    borderRadius: 16,
    padding: 20,
  },
  reportTitle: { fontSize: 18, fontWeight: 900, color: 'var(--text-primary)' },
  reportGrid: {
    marginTop: 14,
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 12,
  },
  reportMetric: {
    background: 'var(--card-bg)',
    border: '1px solid var(--border-color)',
    borderRadius: 14,
    padding: 14,
  },
  metricLabel: { opacity: 0.85, fontSize: 13, color: 'var(--text-secondary)' },
  metricValue: { fontSize: 20, fontWeight: 900, marginTop: 6, color: 'var(--text-primary)' },

  breakdownRow: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: 12,
    background: 'var(--card-bg)',
    border: '1px solid var(--border-color)',
    borderRadius: 12,
    padding: '10px 12px',
  },
  breakdownCat: { fontWeight: 800, color: 'var(--text-primary)' },
  breakdownMeta: { opacity: 0.85, color: 'var(--text-secondary)' },
};
