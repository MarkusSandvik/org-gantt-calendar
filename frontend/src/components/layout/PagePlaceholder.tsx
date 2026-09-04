import type { PropsWithChildren } from "react";

interface PagePlaceholderProps {
  title: string;
  phaseNote: string;
}

export function PagePlaceholder({
  title,
  phaseNote,
  children,
}: PropsWithChildren<PagePlaceholderProps>) {
  return (
    <div className="page">
      <h1>{title}</h1>
      <p className="page__phase-note">{phaseNote}</p>
      {children}
    </div>
  );
}
