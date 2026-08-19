# Software Engineering

Use this skill to inspect, debug, and change an existing software system safely.

- Start with a bounded repository tree and search; read the relevant implementation, interfaces,
  configuration, and tests before proposing an edit.
- Identify the observable failure or requested behavior, likely ownership boundaries, input/output
  contracts, and the smallest relevant verification command.
- Make the smallest focused change that satisfies the request. Preserve compatibility unless the
  requested change explicitly alters it.
- Prefer existing conventions and utilities over introducing parallel abstractions.
- Use controlled repository writes only for deliberate changes. Inspect the changed-file list or
  read the edited file afterward; do not assume a write had the intended result.
- Run focused tests when available. Inspect a failure before changing the approach; do not loop on
  the same failing command or claim a test passed without its observation.
- Report changed files, validation performed, remaining risks, and anything not verified. Register
  generated reports or user-requested outputs as artifacts deliberately, not every source change.
