#!/usr/bin/env python3
"""Convertidor sencillo de Markdown a PDF sin dependencias externas."""

import os
import sys
import textwrap
from typing import Iterable, List

PAGE_WIDTH = 595  # A4 en puntos (aprox.)
PAGE_HEIGHT = 842
MARGIN = 72
LINE_HEIGHT = 14
LINES_PER_PAGE = int((PAGE_HEIGHT - 2 * MARGIN) // LINE_HEIGHT)


def clean_inline(text: str) -> str:
    """Remueve marcadores simples de Markdown para texto plano."""
    replacements = {
        "**": "",
        "__": "",
        "`": "",
        "\\\\": "",
    }
    cleaned = text
    for old, new in replacements.items():
        cleaned = cleaned.replace(old, new)
    if cleaned.endswith("  "):
        cleaned = cleaned.rstrip()
    return cleaned


def parse_markdown(path: str) -> List[str]:
    lines: List[str] = []
    in_code = False

    with open(path, "r", encoding="utf-8") as infile:
        for raw_line in infile:
            line = raw_line.rstrip("\n")

            if line.strip().startswith("```"):
                if not in_code:
                    lines.append("")
                    in_code = True
                    continue
                in_code = False
                lines.append("")
                continue

            if in_code:
                lines.append("    " + line)
                continue

            stripped = line.strip()
            if not stripped:
                lines.append("")
                continue

            if stripped.startswith("#"):
                level = len(stripped) - len(stripped.lstrip("#"))
                heading = stripped[level:].strip()
                heading = clean_inline(heading)
                if level <= 2:
                    heading = heading.upper()
                lines.append(heading)
                lines.append("")
                continue

            if stripped.startswith(("- ", "* ")):
                content = clean_inline(stripped[2:].strip())
                wrapped = textwrap.wrap(content, width=90)
                if wrapped:
                    lines.append("• " + wrapped[0])
                    for extra in wrapped[1:]:
                        lines.append("  " + extra)
                else:
                    lines.append("•")
                continue

            if stripped and stripped[0].isdigit():
                prefix, sep, rest = stripped.partition(". ")
                if sep:
                    content = clean_inline(rest)
                    wrapped = textwrap.wrap(content, width=88)
                    if wrapped:
                        lines.append(f"{prefix}. " + wrapped[0])
                        for extra in wrapped[1:]:
                            lines.append("   " + extra)
                    else:
                        lines.append(f"{prefix}.")
                    continue

            paragraph = clean_inline(stripped)
            wrapped = textwrap.wrap(paragraph, width=95)
            lines.extend(wrapped if wrapped else [""])

    return lines


def escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def chunk_lines(lines: Iterable[str]) -> List[List[str]]:
    chunks: List[List[str]] = []
    current: List[str] = []
    count = 0
    for line in lines:
        if count >= LINES_PER_PAGE:
            chunks.append(current)
            current = []
            count = 0
        current.append(line)
        count += 1
    if current:
        chunks.append(current)
    return chunks


def build_content_stream(page_lines: List[str]) -> str:
    y_start = PAGE_HEIGHT - MARGIN
    content_parts = [
        "BT",
        "/F1 12 Tf",
        f"1 0 0 1 {MARGIN} {y_start} Tm",
        f"{LINE_HEIGHT} TL",
    ]

    first = True
    for line in page_lines:
        safe_text = escape_pdf_text(line.encode("latin-1", "replace").decode("latin-1"))
        if first:
            first = False
        else:
            content_parts.append("T*")
        if not safe_text:
            continue
        content_parts.append(f"({safe_text}) Tj")

    content_parts.append("ET")
    content_str = "\n".join(content_parts)
    length = len(content_str.encode("latin-1"))
    return f"<< /Length {length} >>\nstream\n{content_str}\nendstream"


def write_pdf(markdown_path: str, pdf_path: str) -> None:
    lines = parse_markdown(markdown_path)
    pages = chunk_lines(lines)

    objects: List[str] = []
    objects.append("<< /Type /Catalog /Pages 2 0 R >>")
    objects.append("")
    objects.append("<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    page_objects: List[str] = []
    content_objects: List[str] = []
    for page_lines in pages:
        content_stream = build_content_stream(page_lines)
        content_objects.append(content_stream)
        page_objects.append("")

    total_pages = len(pages)

    for index in range(total_pages):
        content_obj_number = 5 + index * 2
        page_objects[index] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {PAGE_WIDTH} {PAGE_HEIGHT}] "
            f"/Contents {content_obj_number} 0 R /Resources << /Font << /F1 3 0 R >> >> >>"
        )

    kids_refs = " ".join(f"{4 + i * 2} 0 R" for i in range(total_pages))
    pages_object = f"<< /Type /Pages /Count {total_pages} /Kids [{kids_refs}] >>"
    objects[1] = pages_object

    for page_obj in page_objects:
        objects.append(page_obj)
        objects.append("")

    base_index = 4
    for idx, content_obj in enumerate(content_objects):
        object_position = base_index + idx * 2
        objects[object_position] = content_obj

    pdf_bytes = bytearray()
    pdf_bytes.extend(b"%PDF-1.4\n")

    offsets: List[int] = []
    for obj_number, obj_content in enumerate(objects, start=1):
        offsets.append(len(pdf_bytes))
        pdf_bytes.extend(f"{obj_number} 0 obj\n".encode("latin-1"))
        pdf_bytes.extend(obj_content.encode("latin-1"))
        pdf_bytes.extend(b"\nendobj\n")

    xref_position = len(pdf_bytes)
    total_objects = len(objects)
    pdf_bytes.extend(f"xref\n0 {total_objects + 1}\n".encode("latin-1"))
    pdf_bytes.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        pdf_bytes.extend(f"{offset:010} 00000 n \n".encode("latin-1"))
    pdf_bytes.extend(b"trailer\n")
    pdf_bytes.extend(f"<< /Size {total_objects + 1} /Root 1 0 R >>\n".encode("latin-1"))
    pdf_bytes.extend(b"startxref\n")
    pdf_bytes.extend(f"{xref_position}\n".encode("latin-1"))
    pdf_bytes.extend(b"%%EOF\n")

    with open(pdf_path, "wb") as outfile:
        outfile.write(pdf_bytes)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: markdown_to_pdf.py <entrada.md> <salida.pdf>", file=sys.stderr)
        sys.exit(1)

    input_md, output_pdf = sys.argv[1:3]
    if not os.path.isfile(input_md):
        print(f"No se encontró el archivo: {input_md}", file=sys.stderr)
        sys.exit(1)

    write_pdf(input_md, output_pdf)
