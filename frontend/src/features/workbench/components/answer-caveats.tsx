/**
 * The limitations the analysis stated about itself.
 *
 * Written by the model when it finished the run and stored with it, so these
 * are shown exactly as recorded — read-only. A reader may republish them but
 * never rewrite them, because a caveat qualifies the figures beside it and
 * editing one would change what the report claims without changing the numbers
 * it claims it about.
 *
 * A published PDF or DOCX prints the same list under Limitations, alongside a
 * deterministic notice the runtime adds there. That notice is not repeated here
 * — the Workbench already says what a citation does and does not prove, under
 * the evidence chips.
 */
export function AnswerCaveats({ caveats }: { caveats: string[] }) {
  if (!caveats.length) return null;
  return (
    <aside className="answer-caveats" aria-label="Limitations this analysis stated">
      <p className="answer-caveats-lead">Limitations</p>
      <ul>
        {caveats.map((caveat) => (
          <li key={caveat}>{caveat}</li>
        ))}
      </ul>
    </aside>
  );
}
