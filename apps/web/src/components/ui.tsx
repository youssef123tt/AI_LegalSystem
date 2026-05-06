import React from "react";
import clsx from "clsx";

export function Card(props: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      {...props}
      className={clsx(
        "rounded-xl bg-white/70 shadow-card ring-1 ring-black/5 backdrop-blur",
        props.className
      )}
    />
  );
}

export function Button(
  props: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "solid" | "ghost" }
) {
  const { variant = "solid", ...rest } = props;
  return (
    <button
      {...rest}
      className={clsx(
        "inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition",
        "disabled:cursor-not-allowed disabled:opacity-50",
        variant === "solid" &&
          "bg-ink-900 text-paper hover:bg-ink-800 active:bg-ink-900/90",
        variant === "ghost" && "bg-transparent text-ink-900 hover:bg-black/5 active:bg-black/10",
        props.className
      )}
    />
  );
}

export const Input = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(
  function Input(props, ref) {
    return (
      <input
        {...props}
        ref={ref}
        className={clsx(
          "w-full rounded-lg border border-black/10 bg-white/80 px-3 py-2 text-sm",
          "focus:outline-none focus:ring-2 focus:ring-accent-300/70",
          props.className
        )}
      />
    );
  }
);

export function Label(props: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      {...props}
      className={clsx("text-xs font-bold uppercase tracking-wide text-ink-700", props.className)}
    />
  );
}

export function Badge({
  tone = "neutral",
  children
}: {
  tone?: "neutral" | "ok" | "warn" | "bad" | "info";
  children: React.ReactNode;
}) {
  const styles =
    tone === "ok"
      ? "bg-emerald-100 text-emerald-900 ring-emerald-200"
      : tone === "warn"
        ? "bg-amber-100 text-amber-900 ring-amber-200"
        : tone === "bad"
          ? "bg-rose-100 text-rose-900 ring-rose-200"
          : tone === "info"
            ? "bg-sky-100 text-sky-900 ring-sky-200"
            : "bg-black/5 text-ink-900 ring-black/10";
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ring-1",
        styles
      )}
    >
      {children}
    </span>
  );
}
