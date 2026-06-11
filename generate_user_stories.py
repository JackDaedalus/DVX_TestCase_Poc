#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DXV Feedback (Quarantine Export) — User Story & Test Case generator.

Reads a structured, in-script catalogue of User Stories (decomposed from
``feedback-quarantine-export.md``) and renders, for every story, TWO artefacts
into the same folder as this script:

    1. A richly-styled Microsoft Word (.docx) document.
    2. A parallel Markdown (.md) document with identical content, formatted for
       downstream ingestion into Atlassian JIRA Cloud by another agent.

The content lives in ``stories.py`` (single source of truth) so the Word and
Markdown renderers can never drift apart.

Usage:
    python generate_user_stories.py
"""

from __future__ import annotations

import os
import sys

# Local imports (same directory)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from stories import STORIES, SUITE  # noqa: E402
from render_docx import build_docx  # noqa: E402
from render_md import build_markdown  # noqa: E402
from render_index import build_index_docx, build_index_md  # noqa: E402


OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    written: list[str] = []

    # Per-story artefacts
    for story in STORIES:
        base = story["filename"]
        docx_path = os.path.join(OUTPUT_DIR, base + ".docx")
        md_path = os.path.join(OUTPUT_DIR, base + ".md")

        build_docx(story, docx_path)
        build_markdown(story, md_path)

        written.append(docx_path)
        written.append(md_path)

    # Suite-level index / overview (epic summary)
    idx_docx = os.path.join(OUTPUT_DIR, "DXV-FRE-000_Test-Suite-Overview.docx")
    idx_md = os.path.join(OUTPUT_DIR, "DXV-FRE-000_Test-Suite-Overview.md")
    build_index_docx(SUITE, STORIES, idx_docx)
    build_index_md(SUITE, STORIES, idx_md)
    written.append(idx_docx)
    written.append(idx_md)

    print("Generated {} files:".format(len(written)))
    for path in written:
        print("  - {}".format(os.path.basename(path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
