import { render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it } from "vitest";

/**
 * `/w/[workspaceId]/layout.tsx` wraps `{children}` in `<div key={workspaceId}>`
 * specifically so that switching tenants unmounts and remounts the workbench
 * subtree, rather than letting React reconcile it in place and carry the
 * previous tenant's local state across -- which is what would let stale data
 * flash before a refetch completes. This exercises that exact mechanism
 * against a stand-in stateful child, independent of Next's server runtime.
 *
 * The child's state is seeded from `label` via the lazy `useState`
 * initializer -- which only ever runs on mount, never on a props update --
 * so if the surrounding `key` ever stopped forcing a remount, a switch would
 * leave the state exactly as it was instead of reseeding from the new label.
 */
function StatefulChild({ label }: { label: string }) {
  const [mountedFor] = useState(label);
  return <div data-testid="child-state">{mountedFor}</div>;
}

function Shell({ workspaceId }: { workspaceId: string }) {
  return (
    <div key={workspaceId}>
      <StatefulChild label={workspaceId} />
    </div>
  );
}

describe("tenant subtree keying", () => {
  it("resets child state when the workspace id key changes", () => {
    const { rerender } = render(<Shell workspaceId="ws-1" />);
    expect(screen.getByTestId("child-state")).toHaveTextContent("ws-1");

    rerender(<Shell workspaceId="ws-2" />);

    // A remount starts the child's state fresh -- it only ever sees the
    // workspace it was mounted for, never both in sequence.
    expect(screen.getByTestId("child-state")).toHaveTextContent("ws-2");
    expect(screen.getByTestId("child-state")).not.toHaveTextContent("ws-1");
  });
});
