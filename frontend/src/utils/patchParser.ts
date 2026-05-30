import type { CodeLine } from "../types/review";

export const parsePatchToCodeLines = (patch: string | null | undefined): CodeLine[] => {
  if (!patch) return [];

  const codeLines: CodeLine[] = [];
  let oldLine = 0;
  let newLine = 0;

  for (const rawLine of patch.split("\n")) {
    const hunk = /^@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@ ?(.*)$/.exec(rawLine);
    if (hunk) {
      oldLine = Number(hunk[1]);
      newLine = Number(hunk[2]);
      codeLines.push({
        line: newLine,
        mark: " ",
        code: rawLine,
      });
      continue;
    }

    const mark = rawLine.startsWith("+") ? "+" : rawLine.startsWith("-") ? "-" : " ";
    const code = rawLine.startsWith("+") || rawLine.startsWith("-") || rawLine.startsWith(" ")
      ? rawLine.slice(1)
      : rawLine;

    if (mark === "+") {
      codeLines.push({ line: newLine, mark, code });
      newLine += 1;
    } else if (mark === "-") {
      codeLines.push({ line: oldLine, mark, code });
      oldLine += 1;
    } else {
      codeLines.push({ line: newLine, mark, code });
      oldLine += 1;
      newLine += 1;
    }
  }

  return codeLines;
};
