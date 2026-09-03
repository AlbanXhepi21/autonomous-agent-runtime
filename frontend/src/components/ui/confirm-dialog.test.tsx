import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ConfirmDialog } from "./confirm-dialog";

describe("ConfirmDialog accessibility and behavior", () => {
  it("exposes itself as an alert dialog labelled by its title", () => {
    render(
      <ConfirmDialog
        title="Remove this member?"
        description="They lose access immediately."
        confirmLabel="Remove"
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );

    const dialog = screen.getByRole("alertdialog");
    expect(dialog).toHaveAttribute("aria-modal", "true");
    expect(dialog).toHaveAccessibleName("Remove this member?");
  });

  it("calls onCancel when Escape is pressed", () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        title="Remove this member?"
        description="They lose access immediately."
        confirmLabel="Remove"
        onConfirm={() => {}}
        onCancel={onCancel}
      />,
    );

    fireEvent.keyDown(document, { key: "Escape" });

    expect(onCancel).toHaveBeenCalled();
  });

  it("calls onCancel when the backdrop is clicked, but not when the dialog itself is", () => {
    const onCancel = vi.fn();
    render(
      <ConfirmDialog
        title="Remove this member?"
        description="They lose access immediately."
        confirmLabel="Remove"
        onConfirm={() => {}}
        onCancel={onCancel}
      />,
    );

    fireEvent.click(screen.getByRole("alertdialog"));
    expect(onCancel).not.toHaveBeenCalled();

    fireEvent.click(screen.getByRole("alertdialog").parentElement!);
    expect(onCancel).toHaveBeenCalled();
  });

  it("keeps the confirm button disabled until the required text is typed exactly", () => {
    const onConfirm = vi.fn();
    render(
      <ConfirmDialog
        title="Deactivate this organization?"
        description="Every member loses access."
        confirmLabel="Deactivate"
        confirmText="Acme"
        onConfirm={onConfirm}
        onCancel={() => {}}
      />,
    );

    const confirmButton = screen.getByRole("button", { name: "Deactivate" });
    expect(confirmButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/Type/), { target: { value: "acme" } });
    expect(confirmButton).toBeDisabled();

    fireEvent.change(screen.getByLabelText(/Type/), { target: { value: "Acme" } });
    expect(confirmButton).not.toBeDisabled();

    fireEvent.click(confirmButton);
    expect(onConfirm).toHaveBeenCalled();
  });

  it("disables cancel and shows a working label while busy", () => {
    render(
      <ConfirmDialog
        title="Remove this member?"
        description="They lose access immediately."
        confirmLabel="Remove"
        busy
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );

    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Working…" })).toBeDisabled();
  });

  it("renders a supplied error message", () => {
    render(
      <ConfirmDialog
        title="Remove this member?"
        description="They lose access immediately."
        confirmLabel="Remove"
        error="This member could not be removed."
        onConfirm={() => {}}
        onCancel={() => {}}
      />,
    );

    expect(screen.getByRole("alert")).toHaveTextContent("This member could not be removed.");
  });
});
