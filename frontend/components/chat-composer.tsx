"use client";

import { FormEvent, KeyboardEvent, useState } from "react";

export function ChatComposer({
  onSubmit,
  disabled,
}: {
  onSubmit: (message: string) => void;
  disabled: boolean;
}) {
  const [value, setValue] = useState("");
  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    const message = value.trim();
    if (!message || disabled) return;
    onSubmit(message);
    setValue("");
  };
  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };
  return (
    <form className="composer" onSubmit={submit}>
      <textarea
        aria-label="Ask about your data"
        placeholder="Ask about your data…"
        value={value}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={onKeyDown}
        rows={1}
      />
      <button type="submit" disabled={disabled || !value.trim()}>
        {disabled ? "Analyzing" : "Analyze"}
      </button>
    </form>
  );
}
