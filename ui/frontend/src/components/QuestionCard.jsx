import { useMemo, useState } from "react";
import { ChevronLeft, ChevronRight, Pencil, X } from "lucide-react";

const OPEN_ENDED_OPTION = "Something else (please specify)";
const SKIPPED = "Skipped";

function formatAnswerString(items, answersById) {
  return items
    .map((it, i) => {
      const key = `${it.interruptId}:${it.qIdx}`;
      const answer = answersById[key] ?? SKIPPED;
      return `Q${i + 1}. ${it.question.question}\n${answer}`;
    })
    .join("\n\n");
}

export default function QuestionCard({ pendingInterrupts, onSubmit, onCancel }) {
  // Flatten every question across every interrupt into a single paginated list.
  // Each entry remembers its parent interrupt id so we can partition answers
  // back into a per-interrupt resume map on submit.
  const flat = useMemo(
    () =>
      pendingInterrupts.flatMap((it) =>
        (it.value ?? []).map((q, qIdx) => ({ interruptId: it.id, qIdx, question: q }))
      ),
    [pendingInterrupts]
  );

  const [page, setPage] = useState(0);
  const [answers, setAnswers] = useState({}); // `${interruptId}:${qIdx}` → string
  const [custom, setCustom] = useState({}); // same key → custom text for "other"

  if (flat.length === 0) return null;
  const current = flat[page];
  const key = `${current.interruptId}:${current.qIdx}`;
  const options = current.question.options ?? [];
  const isCustomSelected = answers[key] === OPEN_ENDED_OPTION;

  function choose(option) {
    setAnswers((prev) => ({ ...prev, [key]: option }));
  }

  function skip() {
    setAnswers((prev) => {
      const next = { ...prev };
      delete next[key];
      return next;
    });
    advance();
  }

  function advance() {
    if (page < flat.length - 1) setPage(page + 1);
    else submit();
  }

  function submit() {
    // Group answers back by parent interrupt id and format one string per id.
    const byInterrupt = {};
    for (const item of flat) {
      const k = `${item.interruptId}:${item.qIdx}`;
      let answer = answers[k];
      if (answer === OPEN_ENDED_OPTION) answer = (custom[k] ?? "").trim() || SKIPPED;
      (byInterrupt[item.interruptId] ||= []).push({ ...item, answer: answer ?? SKIPPED });
    }
    const resumeMap = Object.fromEntries(
      Object.entries(byInterrupt).map(([id, items]) => [
        id,
        formatAnswerString(items, Object.fromEntries(items.map((it) => [`${it.interruptId}:${it.qIdx}`, it.answer]))),
      ])
    );
    onSubmit(resumeMap);
  }

  return (
    <div className="question-card">
      <div className="question-card-header">
        <div className="question-card-title">{current.question.question}</div>
        <div className="question-card-nav">
          <button
            type="button"
            className="qc-chevron"
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            title="Previous"
          >
            <ChevronLeft size={14} />
          </button>
          <span className="qc-counter">
            {page + 1} of {flat.length}
          </span>
          <button
            type="button"
            className="qc-chevron"
            onClick={() => setPage((p) => Math.min(flat.length - 1, p + 1))}
            disabled={page === flat.length - 1}
            title="Next"
          >
            <ChevronRight size={14} />
          </button>
          {onCancel && (
            <button type="button" className="qc-chevron" onClick={onCancel} title="Close">
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {options.length > 0 && (
        <ul className="question-card-options">
          {options.map((opt, i) => {
            const selected = answers[key] === opt;
            return (
              <li
                key={i}
                className={`qc-option ${selected ? "selected" : ""}`}
                onClick={() => choose(opt)}
              >
                <span className="qc-option-num">{i + 1}</span>
                <span className="qc-option-label">{opt}</span>
              </li>
            );
          })}
        </ul>
      )}

      <div className="question-card-input">
        <Pencil size={13} className="qc-input-icon" />
        <input
          type="text"
          placeholder={
            options.length > 0 ? OPEN_ENDED_OPTION : "Type your answer..."
          }
          value={custom[key] ?? ""}
          onChange={(e) => {
            setCustom((prev) => ({ ...prev, [key]: e.target.value }));
            if (options.length > 0) choose(OPEN_ENDED_OPTION);
            else setAnswers((prev) => ({ ...prev, [key]: e.target.value }));
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              advance();
            }
          }}
        />
        <button type="button" className="qc-skip" onClick={skip}>
          Skip
        </button>
        <button
          type="button"
          className="qc-advance"
          onClick={advance}
          disabled={!answers[key] && !(isCustomSelected && (custom[key] ?? "").trim())}
        >
          {page === flat.length - 1 ? "Submit" : "Next"}
        </button>
      </div>
    </div>
  );
}
