# -*- coding: utf-8 -*-
"""Render a single User Story dict to a Markdown document that mirrors the Word
output and is friendly for downstream ingestion into Atlassian JIRA Cloud.

Structure:
    - YAML front matter (machine-readable fields for the import agent)
    - H1 title + metadata table
    - User story statement (blockquote)
    - Description paragraphs
    - Key terms table
    - Acceptance criteria (numbered)
    - Recommended test data table
    - Global preconditions
    - Test cases, each with a step table
"""

from __future__ import annotations

import datetime as _dt

import theme as T


def _esc(text):
    """Escape pipe characters so Markdown tables don't break."""
    if text is None:
        return ""
    return str(text).replace("|", "\\|").replace("\n", " ")


def _yaml_list(items):
    return "[" + ", ".join('"{}"'.format(str(i).replace('"', "'")) for i in items) + "]"


def _front_matter(story):
    by_type = {}
    for tc in story["tests"]:
        by_type[tc["type"]] = by_type.get(tc["type"], 0) + 1
    lines = ["---"]
    lines.append('jira_issue_type: "Story"')
    lines.append('story_key: "{}"'.format(story["id"]))
    lines.append('summary: "{}"'.format(story["title"].replace('"', "'")))
    lines.append('epic: "{}"'.format(story["epic"].replace('"', "'")))
    lines.append('priority: "{}"'.format(story["priority"]))
    lines.append("story_points: {}".format(story["story_points"]))
    lines.append("components: {}".format(_yaml_list(story["components"])))
    lines.append("labels: {}".format(_yaml_list(story["labels"])))
    lines.append('status: "Ready for Test"')
    lines.append("test_case_count: {}".format(len(story["tests"])))
    lines.append("test_type_breakdown: {{{}}}".format(
        ", ".join('"{}": {}'.format(k, v) for k, v in by_type.items())))
    lines.append("---")
    return "\n".join(lines)


def _metadata_table(story):
    rows = [
        ("Field", "Value"),
        ("Story Key", "`{}`".format(story["id"])),
        ("Issue Type", "Story"),
        ("Epic", story["epic"]),
        ("Priority", "**{}**".format(story["priority"])),
        ("Story Points", str(story["story_points"])),
        ("Components", ", ".join("`{}`".format(c) for c in story["components"])),
        ("Labels", " ".join("`{}`".format(l) for l in story["labels"])),
        ("Status", "Ready for Test"),
    ]
    out = []
    out.append("| {} | {} |".format(rows[0][0], rows[0][1]))
    out.append("| --- | --- |")
    for k, v in rows[1:]:
        out.append("| **{}** | {} |".format(k, v))
    return "\n".join(out)


def _badge(ttype):
    return T.MD_TYPE_BADGE.get(ttype, "")


def build_markdown(story, out_path):
    L = []
    L.append(_front_matter(story))
    L.append("")
    L.append("# {} \u2014 {}".format(story["id"], story["title"]))
    L.append("")
    L.append("> **Epic:** {}  |  **Product:** DXV \u2014 Data Exchange Vault  |  "
             "**Pipeline:** `failed-record-export`".format(story["epic"]))
    L.append("")

    # Metadata
    L.append("## Story Details")
    L.append("")
    L.append(_metadata_table(story))
    L.append("")

    # User story statement
    L.append("## User Story")
    L.append("")
    L.append("> **As a** {}  ".format(story["persona"]))
    L.append("> **I want** {}  ".format(story["want"]))
    L.append("> **so that** {}.".format(story["benefit"].rstrip(".")))
    L.append("")

    # Description
    L.append("## Description")
    L.append("")
    for para in story["description"]:
        L.append(para)
        L.append("")

    # Key terms
    if story.get("context"):
        L.append("## Key Terms & Behaviour")
        L.append("")
        L.append("| Term | Behaviour / Definition |")
        L.append("| --- | --- |")
        for term, desc in story["context"]:
            L.append("| **{}** | {} |".format(_esc(term), _esc(desc)))
        L.append("")

    # Acceptance criteria
    L.append("## Acceptance Criteria")
    L.append("")
    L.append("**Definition of Done**")
    L.append("")
    for i, ac in enumerate(story["acceptance"], start=1):
        L.append("{}. {}".format(i, ac))
    L.append("")

    # Recommended test data
    if story.get("test_data"):
        L.append("## Recommended Test Data")
        L.append("")
        L.append("| Artefact | Example Value / Format |")
        L.append("| --- | --- |")
        for art, val in story["test_data"]:
            L.append("| **{}** | `{}` |".format(_esc(art), _esc(val)))
        L.append("")

    # Global preconditions
    if story.get("preconditions"):
        L.append("## Global Preconditions")
        L.append("")
        for pc in story["preconditions"]:
            L.append("- {}".format(pc))
        L.append("")

    # Test cases
    L.append("## Test Cases")
    L.append("")
    by_type = {}
    for tc in story["tests"]:
        by_type[tc["type"]] = by_type.get(tc["type"], 0) + 1
    coverage = "  ".join("{} {} \u00d7 {}".format(_badge(k), k, v) for k, v in by_type.items())
    L.append("**Coverage:** {} test case(s) \u2014 {}".format(len(story["tests"]), coverage))
    L.append("")

    for tc in story["tests"]:
        L.append("---")
        L.append("")
        L.append("### {} {} \u2014 {}".format(_badge(tc["type"]), tc["id"], tc["title"]))
        L.append("")
        meta_bits = ["**Type:** {}".format(tc["type"])]
        if tc.get("priority"):
            meta_bits.append("**Priority:** {}".format(tc["priority"]))
        L.append("  |  ".join(meta_bits))
        L.append("")
        if tc.get("objective"):
            L.append("**Objective:** {}".format(tc["objective"]))
            L.append("")
        if tc.get("preconditions"):
            L.append("**Preconditions:**")
            for pc in tc["preconditions"]:
                L.append("- {}".format(pc))
            L.append("")
        # Steps table
        L.append("| # | Test Step / Action | Test Data (format / value) | Expected Result |")
        L.append("| :---: | --- | --- | --- |")
        for idx, st in enumerate(tc["steps"], start=1):
            L.append("| {} | {} | `{}` | {} |".format(
                idx, _esc(st["action"]), _esc(st["data"]), _esc(st["expected"])))
        L.append("")
        if tc.get("postconditions"):
            L.append("**Postconditions:**")
            for pc in tc["postconditions"]:
                L.append("- {}".format(pc))
            L.append("")

    L.append("---")
    L.append("")
    L.append("_Generated for the DXV Feedback (Quarantine Export) integration test suite "
             "\u2014 {}._".format(_dt.date.today().isoformat()))
    L.append("")

    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
    return out_path
