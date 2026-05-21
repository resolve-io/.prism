import { useMemo, type ReactNode } from "react";
import { Empty } from "@/components/ui";

/**
 * Lightweight markdown renderer for the onboarding analyzer output.
 *
 * Borrowed structure from Lum1104/Understand-Anything's LearnPanel
 * (which uses MarkdownIt); we keep it dependency-free by handling
 * only the subset our onboarding_writer prompt emits: H1/H2/H3,
 * paragraphs, unordered lists, inline `code` and **bold**.
 */
export default function OnboardingView({ text }: { text: string }) {
  const blocks = useMemo(() => parseMarkdown(text), [text]);
  if (!text.trim() || blocks.length === 0) {
    return <Empty>No onboarding doc yet.</Empty>;
  }
  return <div className="prose-like space-y-4 max-w-[840px]">{blocks}</div>;
}


function parseMarkdown(text: string): ReactNode[] {
  const lines = text.split(/\r?\n/);
  const blocks: ReactNode[] = [];
  let i = 0;
  let para: string[] = [];
  let listItems: string[] = [];

  const flushPara = () => {
    if (para.length === 0) return;
    blocks.push(
      <p key={`p${blocks.length}`} className="text-sm leading-relaxed opacity-85">
        {renderInline(para.join(" "))}
      </p>,
    );
    para = [];
  };
  const flushList = () => {
    if (listItems.length === 0) return;
    blocks.push(
      <ul key={`ul${blocks.length}`} className="text-sm leading-relaxed opacity-85 list-disc pl-5 space-y-1">
        {listItems.map((it, k) => (
          <li key={k}>{renderInline(it)}</li>
        ))}
      </ul>,
    );
    listItems = [];
  };

  while (i < lines.length) {
    const raw = lines[i];
    const line = raw.trim();
    if (!line) { flushPara(); flushList(); i++; continue; }

    const h1 = /^#\s+(.*)$/.exec(line);
    const h2 = /^##\s+(.*)$/.exec(line);
    const h3 = /^###\s+(.*)$/.exec(line);
    const bul = /^[-*]\s+(.*)$/.exec(line);

    if (h1) {
      flushPara(); flushList();
      blocks.push(
        <h1 key={`h${blocks.length}`} className="font-serif text-2xl tracking-tight">
          {h1[1]}
        </h1>,
      );
    } else if (h2) {
      flushPara(); flushList();
      blocks.push(
        <h2 key={`h${blocks.length}`} className="font-serif text-xl tracking-tight pt-2 border-t border-[color:var(--midground-base)]/10">
          {h2[1]}
        </h2>,
      );
    } else if (h3) {
      flushPara(); flushList();
      blocks.push(
        <h3 key={`h${blocks.length}`} className="font-serif text-base tracking-tight">
          {h3[1]}
        </h3>,
      );
    } else if (bul) {
      flushPara();
      listItems.push(bul[1]);
    } else {
      flushList();
      para.push(line);
    }
    i++;
  }
  flushPara(); flushList();
  return blocks;
}


function renderInline(text: string): ReactNode {
  // **bold**, `code`. Order matters: code first (so `**...**` inside backticks stays literal).
  const parts: ReactNode[] = [];
  let rest = text;
  let key = 0;
  while (rest.length > 0) {
    const code = /`([^`]+)`/.exec(rest);
    const bold = /\*\*([^*]+)\*\*/.exec(rest);
    const next = pickFirst(code, bold);
    if (!next) { parts.push(rest); break; }
    if (next.index > 0) parts.push(rest.slice(0, next.index));
    if (next === code) {
      parts.push(<code key={key++} className="text-[12px] font-mono px-1 py-0.5 rounded bg-[color:var(--midground-base)]/10">{next[1]}</code>);
    } else {
      parts.push(<strong key={key++} className="font-semibold">{next[1]}</strong>);
    }
    rest = rest.slice(next.index + next[0].length);
  }
  return parts;
}


function pickFirst(...matches: (RegExpExecArray | null)[]): RegExpExecArray | null {
  let best: RegExpExecArray | null = null;
  for (const m of matches) {
    if (m && (best === null || m.index < best.index)) best = m;
  }
  return best;
}
