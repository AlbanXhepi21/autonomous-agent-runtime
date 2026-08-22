"use client";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <main className="boundary">
      <h1>The Workbench stopped unexpectedly</h1>
      <p>Reloading starts a new session. Saved conversations are unaffected.</p>
      <button onClick={reset}>Reload the Workbench</button>
    </main>
  );
}
