function escapePdfText(text: string): string {
  return text.replace(/\\/g, "\\\\").replace(/\(/g, "\\(").replace(/\)/g, "\\)");
}

export function buildSimpleReceiptPdf(lines: string[]): Blob {
  const safeLines = lines.map((line) => escapePdfText(line));
  const contentParts: string[] = ["BT", "/F1 12 Tf", "50 780 Td"];
  safeLines.forEach((line, index) => {
    if (index > 0) {
      contentParts.push("0 -18 Td");
    }
    contentParts.push(`(${line}) Tj`);
  });
  contentParts.push("ET");
  const stream = contentParts.join("\n");

  const objects = [
    "1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
    "2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
    "3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
    "4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
    `5 0 obj\n<< /Length ${stream.length} >>\nstream\n${stream}\nendstream\nendobj\n`,
  ];

  let body = "";
  const offsets: number[] = [0];
  for (const object of objects) {
    offsets.push(body.length);
    body += object;
  }

  const xrefStart = body.length;
  const xrefEntries = ["0000000000 65535 f "];
  for (let i = 1; i < offsets.length; i += 1) {
    xrefEntries.push(`${String(offsets[i]).padStart(10, "0")} 00000 n `);
  }

  const pdf = `%PDF-1.4\n${body}xref\n0 ${objects.length + 1}\n${xrefEntries.join(
    "\n",
  )}\ntrailer\n<< /Size ${objects.length + 1} /Root 1 0 R >>\nstartxref\n${xrefStart}\n%%EOF`;

  return new Blob([pdf], { type: "application/pdf" });
}
