# -*- coding: utf-8 -*-
"""Shared visual theme + small helpers used by both the Word and Markdown
renderers so the two output formats stay visually and structurally aligned.

Palette is a calm, professional "fin-crime / enterprise" scheme:
    - Deep indigo primary for banners and headings
    - Slate secondary for sub-headings
    - Soft tints for table headers and callout backgrounds
    - A restrained accent set for priority / status chips
"""

# ---------------------------------------------------------------------------
# Brand palette (hex, no leading '#')
# ---------------------------------------------------------------------------
PRIMARY = "1F2A56"        # deep indigo  - title band
PRIMARY_LIGHT = "2E3C74"  # indigo       - H1 rule / accents
SECONDARY = "3C4A66"      # slate        - H2 text
MUTED = "6B7280"          # grey         - meta labels, captions

HEADER_FILL = "1F2A56"    # table header background (dark)
HEADER_TEXT = "FFFFFF"    # table header text (white)

ZEBRA_FILL = "EEF1F8"     # subtle row striping
BORDER = "C9D0E0"         # light table borders

# Callout box tints
INFO_FILL = "EAF1FB"      # info / description box
INFO_BAR = "2E6FD6"       # info left accent bar
AC_FILL = "ECF7EE"        # acceptance criteria box
AC_BAR = "2E9E4F"         # acceptance criteria left accent bar
WARN_FILL = "FDF3E7"      # note / preconditions box
WARN_BAR = "D9822B"       # note left accent bar

# Test-type chips
CHIP = {
    "Happy Path":   ("E6F4EA", "1E7E34"),
    "Negative":     ("FCE9E9", "B3261E"),
    "Boundary":     ("FFF4E5", "B26A00"),
    "Non-Functional": ("EAEFFB", "2E3C74"),
    "Security":     ("F3E9FB", "6A1B9A"),
}

# Priority chips (JIRA-style)
PRIORITY = {
    "Highest": ("FCE9E9", "B3261E"),
    "High":    ("FFF1E6", "C2410C"),
    "Medium":  ("FFF8E1", "8D6E00"),
    "Low":     ("E8F5E9", "2E7D32"),
}

FONT_BODY = "Calibri"
FONT_MONO = "Consolas"
FONT_HEAD = "Calibri"

# Markdown emoji used for test-type badges (renders nicely in JIRA + GitHub)
MD_TYPE_BADGE = {
    "Happy Path": "\U0001F7E2",       # green circle
    "Negative": "\U0001F534",          # red circle
    "Boundary": "\U0001F7E0",          # orange circle
    "Non-Functional": "\U0001F535",    # blue circle
    "Security": "\U0001F7E3",          # purple circle
}
