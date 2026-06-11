# -*- coding: utf-8 -*-
"""Render a single User Story dict to a richly-styled Microsoft Word document.

Design goals: a clean, modern, enterprise look that is consistent across every
story — a coloured title band, a JIRA-style metadata grid, tinted callout boxes
for the description / acceptance criteria, and crisp test-case tables with a dark
header row and subtle zebra striping. All styling is done with low-level OOXML so
the result is self-contained (no external template needed).
"""

from __future__ import annotations

import datetime as _dt

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Emu
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.enum.section import WD_SECTION
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

import theme as T


# ---------------------------------------------------------------------------
# Low-level OOXML helpers
# ---------------------------------------------------------------------------
def _set_cell_bg(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    tcPr.append(shd)


def _set_cell_margins(cell, top=60, bottom=60, left=110, right=110):
    tcPr = cell._tc.get_or_add_tcPr()
    m = OxmlElement("w:tcMar")
    for tag, val in (("top", top), ("bottom", bottom), ("start", left), ("end", right),
                     ("left", left), ("right", right)):
        node = OxmlElement(f"w:{tag}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        m.append(node)
    tcPr.append(m)


def _set_cell_vertical_alignment(cell, value="center"):
    tcPr = cell._tc.get_or_add_tcPr()
    v = OxmlElement("w:vAlign")
    v.set(qn("w:val"), value)
    tcPr.append(v)


def _set_repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader")
    th.set(qn("w:val"), "true")
    trPr.append(th)


def _disable_autofit_fixed(table):
    """Force fixed table layout so column widths are honoured by Word."""
    tblPr = table._tbl.tblPr
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblPr.append(layout)


def _set_table_borders(table, color=T.BORDER, size=4, inner=True):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    edges = ["top", "left", "bottom", "right"]
    if inner:
        edges += ["insideH", "insideV"]
    for edge in edges:
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "single")
        e.set(qn("w:sz"), str(size))
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), color)
        borders.append(e)
    tblPr.append(borders)


def _no_table_borders(table):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ["top", "left", "bottom", "right", "insideH", "insideV"]:
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:val"), "none")
        e.set(qn("w:sz"), "0")
        e.set(qn("w:space"), "0")
        e.set(qn("w:color"), "auto")
        borders.append(e)
    tblPr.append(borders)


def _set_col_widths(table, widths_in):
    """Authoritatively fix column widths for a fixed-layout table.

    Sets per-cell widths AND rebuilds the table's <w:tblGrid> with explicit
    <w:gridCol> entries (twips), plus a fixed total <w:tblW>. Word honours the
    grid for fixed layout, so this prevents auto-expansion past the page.
    """
    table.autofit = False
    twips = [int(round(w * 1440)) for w in widths_in]
    total = sum(twips)

    tbl = table._tbl
    tblPr = tbl.tblPr

    # Fixed total table width
    for existing in tblPr.findall(qn("w:tblW")):
        tblPr.remove(existing)
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:w"), str(total))
    tblW.set(qn("w:type"), "dxa")
    tblPr.append(tblW)

    # Rebuild the grid
    for existing in tbl.findall(qn("w:tblGrid")):
        tbl.remove(existing)
    grid = OxmlElement("w:tblGrid")
    for tw in twips:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(tw))
        grid.append(gc)
    tblPr.addnext(grid)

    # Per-cell widths (dxa) for good measure
    for row in table.rows:
        for idx, tw in enumerate(twips):
            if idx < len(row.cells):
                cell = row.cells[idx]
                cell.width = Emu(int(tw * 635))  # 1 twip = 635 EMU
                tcPr = cell._tc.get_or_add_tcPr()
                for ex in tcPr.findall(qn("w:tcW")):
                    tcPr.remove(ex)
                tcW = OxmlElement("w:tcW")
                tcW.set(qn("w:w"), str(tw))
                tcW.set(qn("w:type"), "dxa")
                tcPr.append(tcW)


def _left_accent_border(cell, hex_color, size=24):
    """Thick coloured left border to create a 'callout bar' effect."""
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement("w:tcBorders")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "single")
    left.set(qn("w:sz"), str(size))
    left.set(qn("w:space"), "0")
    left.set(qn("w:color"), hex_color)
    borders.append(left)
    tcPr.append(borders)


def _shade_paragraph(paragraph, hex_fill):
    pPr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_fill)
    pPr.append(shd)


def _add_bottom_rule(paragraph, hex_color, size=12):
    pPr = paragraph._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), str(size))
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), hex_color)
    pbdr.append(bottom)
    pPr.append(pbdr)


def _field(run_parent, instr):
    """Insert a Word field code (used for page numbers)."""
    fldBegin = OxmlElement("w:fldChar")
    fldBegin.set(qn("w:fldCharType"), "begin")
    instrText = OxmlElement("w:instrText")
    instrText.set(qn("xml:space"), "preserve")
    instrText.text = instr
    fldEnd = OxmlElement("w:fldChar")
    fldEnd.set(qn("w:fldCharType"), "end")
    r1 = run_parent.add_run()
    r1._r.append(fldBegin)
    r2 = run_parent.add_run()
    r2._r.append(instrText)
    r3 = run_parent.add_run()
    r3._r.append(fldEnd)


# ---------------------------------------------------------------------------
# Higher-level building blocks
# ---------------------------------------------------------------------------
def _rgb(hexstr):
    return RGBColor(int(hexstr[0:2], 16), int(hexstr[2:4], 16), int(hexstr[4:6], 16))


def _style_base(doc):
    normal = doc.styles["Normal"]
    normal.font.name = T.FONT_BODY
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = _rgb("23272F")
    pf = normal.paragraph_format
    pf.space_after = Pt(6)
    pf.line_spacing = 1.12


def _title_band(doc, story):
    """Full-width coloured banner table holding the story id + title."""
    band = doc.add_table(rows=1, cols=1)
    band.alignment = WD_TABLE_ALIGNMENT.CENTER
    _no_table_borders(band)
    _disable_autofit_fixed(band)
    cell = band.rows[0].cells[0]
    _set_cell_bg(cell, T.PRIMARY)
    _set_cell_margins(cell, top=180, bottom=180, left=220, right=220)

    p_kicker = cell.paragraphs[0]
    p_kicker.paragraph_format.space_after = Pt(2)
    r = p_kicker.add_run("USER STORY  \u2022  {}".format(story["id"]))
    r.font.size = Pt(10)
    r.font.bold = True
    r.font.color.rgb = _rgb("AEB9DA")
    r.font.name = T.FONT_HEAD

    p_title = cell.add_paragraph()
    p_title.paragraph_format.space_before = Pt(0)
    p_title.paragraph_format.space_after = Pt(2)
    rt = p_title.add_run(story["title"])
    rt.font.size = Pt(18)
    rt.font.bold = True
    rt.font.color.rgb = _rgb("FFFFFF")
    rt.font.name = T.FONT_HEAD

    p_epic = cell.add_paragraph()
    p_epic.paragraph_format.space_before = Pt(0)
    re = p_epic.add_run("Epic: {}   |   {}".format(story["epic"], "DXV Feedback (Quarantine Export)"))
    re.font.size = Pt(9.5)
    re.font.color.rgb = _rgb("C9D2EC")
    re.italic = True
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def _chip_run(paragraph, text, fill, textcolor):
    """Render a coloured 'chip' using a shaded single-cell look via run shading."""
    run = paragraph.add_run("  {}  ".format(text))
    run.font.size = Pt(8.5)
    run.font.bold = True
    run.font.color.rgb = _rgb(textcolor)
    # run-level shading
    rPr = run._r.get_or_add_rPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    rPr.append(shd)
    return run


def _metadata_grid(doc, story):
    rows = [
        ("Story Key", story["id"], "Priority", story["priority"]),
        ("Epic", story["epic"], "Story Points", str(story["story_points"])),
        ("Components", ", ".join(story["components"]), "Issue Type", "Story"),
        ("Labels", ", ".join(story["labels"]), "Status", "Ready for Test"),
    ]
    table = doc.add_table(rows=len(rows), cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _disable_autofit_fixed(table)
    _set_table_borders(table, color="FFFFFF", size=8)
    widths = [1.35, 3.0, 1.35, 1.45]
    _set_col_widths(table, widths)

    for r_idx, (k1, v1, k2, v2) in enumerate(rows):
        cells = table.rows[r_idx].cells
        for c_idx, (label, value, is_label) in enumerate([
            (k1, None, True), (None, v1, False), (k2, None, True), (None, v2, False)
        ]):
            cell = cells[c_idx]
            _set_cell_margins(cell, top=60, bottom=60, left=120, right=120)
            _set_cell_vertical_alignment(cell, "center")
            para = cell.paragraphs[0]
            para.paragraph_format.space_after = Pt(0)
            if is_label:
                _set_cell_bg(cell, T.PRIMARY_LIGHT)
                run = para.add_run(label)
                run.font.bold = True
                run.font.size = Pt(9)
                run.font.color.rgb = _rgb("FFFFFF")
            else:
                _set_cell_bg(cell, T.ZEBRA_FILL if r_idx % 2 == 0 else "F6F8FC")
                # priority / status as chips where relevant
                if c_idx == 3 and r_idx == 0 and value in T.PRIORITY:
                    fill, tcol = T.PRIORITY[value]
                    _chip_run(para, value, fill, tcol)
                else:
                    run = para.add_run(value if value is not None else "")
                    run.font.size = Pt(9.5)
                    run.font.color.rgb = _rgb("23272F")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def _section_heading(doc, text, color=T.PRIMARY_LIGHT):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.font.size = Pt(13)
    run.font.bold = True
    run.font.color.rgb = _rgb(color)
    run.font.name = T.FONT_HEAD
    _add_bottom_rule(p, T.BORDER, size=10)
    return p


def _callout(doc, lines, fill, bar, bold_first=False, heading=None):
    """A tinted box with a coloured left accent bar, built from a 1x1 table."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    _no_table_borders(tbl)
    _disable_autofit_fixed(tbl)
    _set_col_widths(tbl, [7.15])
    cell = tbl.rows[0].cells[0]
    _set_cell_bg(cell, fill)
    _left_accent_border(cell, bar, size=24)
    _set_cell_margins(cell, top=120, bottom=120, left=180, right=160)

    first_para = cell.paragraphs[0]
    first_para.paragraph_format.space_after = Pt(0)

    if heading:
        hp = first_para
        hr = hp.add_run(heading)
        hr.font.bold = True
        hr.font.size = Pt(10.5)
        hr.font.color.rgb = _rgb(bar)
        body_start = cell.add_paragraph()
    else:
        body_start = first_para

    for i, line in enumerate(lines):
        para = body_start if i == 0 else cell.add_paragraph()
        para.paragraph_format.space_after = Pt(4 if i < len(lines) - 1 else 0)
        run = para.add_run(line)
        run.font.size = Pt(10)
        run.font.color.rgb = _rgb("2A2F3A")
        if bold_first and i == 0:
            run.font.bold = True
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def _bulleted_callout(doc, items, fill, bar, heading, numbered=False):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    _no_table_borders(tbl)
    _disable_autofit_fixed(tbl)
    _set_col_widths(tbl, [7.15])
    cell = tbl.rows[0].cells[0]
    _set_cell_bg(cell, fill)
    _left_accent_border(cell, bar, size=24)
    _set_cell_margins(cell, top=120, bottom=130, left=180, right=160)

    hp = cell.paragraphs[0]
    hp.paragraph_format.space_after = Pt(6)
    hr = hp.add_run(heading)
    hr.font.bold = True
    hr.font.size = Pt(10.5)
    hr.font.color.rgb = _rgb(bar)

    for i, item in enumerate(items):
        para = cell.add_paragraph()
        para.paragraph_format.space_after = Pt(3)
        para.paragraph_format.left_indent = Inches(0.18)
        para.paragraph_format.first_line_indent = Inches(-0.18)
        marker = "{}.  ".format(i + 1) if numbered else "\u2022  "
        mrun = para.add_run(marker)
        mrun.font.bold = True
        mrun.font.size = Pt(10)
        mrun.font.color.rgb = _rgb(bar)
        run = para.add_run(item)
        run.font.size = Pt(10)
        run.font.color.rgb = _rgb("2A2F3A")
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def _definition_table(doc, pairs):
    table = doc.add_table(rows=len(pairs), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _disable_autofit_fixed(table)
    _set_table_borders(table, color=T.BORDER, size=4)
    _set_col_widths(table, [2.3, 4.85])
    for i, (term, desc) in enumerate(pairs):
        c0, c1 = table.rows[i].cells
        _set_cell_bg(c0, "E8ECF6" if i % 2 == 0 else "F2F5FB")
        _set_cell_bg(c1, "FFFFFF" if i % 2 == 0 else "FAFBFE")
        for c in (c0, c1):
            _set_cell_margins(c, top=50, bottom=50, left=120, right=120)
            _set_cell_vertical_alignment(c, "center")
        p0 = c0.paragraphs[0]; p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(term); r0.font.bold = True; r0.font.size = Pt(9.5)
        r0.font.color.rgb = _rgb(T.SECONDARY)
        p1 = c1.paragraphs[0]; p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(desc); r1.font.size = Pt(9.5)
        if any(ch in desc for ch in ("{", "_", "/", "(", ".", "=")) and len(desc) < 90:
            r1.font.name = T.FONT_MONO
            r1.font.size = Pt(9)
    doc.add_paragraph().paragraph_format.space_after = Pt(0)


def _test_case_header(doc, tc):
    """A coloured strip introducing each test case with id, title and type chip."""
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    _no_table_borders(tbl)
    _disable_autofit_fixed(tbl)
    _set_col_widths(tbl, [7.15])
    cell = tbl.rows[0].cells[0]
    _set_cell_bg(cell, "EDF0F7")
    _left_accent_border(cell, T.PRIMARY, size=30)
    _set_cell_margins(cell, top=90, bottom=90, left=160, right=150)

    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(2)
    r_id = p.add_run("{}  ".format(tc["id"]))
    r_id.font.bold = True
    r_id.font.size = Pt(11)
    r_id.font.color.rgb = _rgb(T.PRIMARY)
    r_title = p.add_run(tc["title"])
    r_title.font.bold = True
    r_title.font.size = Pt(11)
    r_title.font.color.rgb = _rgb("23272F")

    # chips line
    p2 = cell.add_paragraph()
    p2.paragraph_format.space_before = Pt(2)
    p2.paragraph_format.space_after = Pt(0)
    ttype = tc.get("type", "Happy Path")
    fill, tcol = T.CHIP.get(ttype, ("E6E6E6", "333333"))
    _chip_run(p2, ttype.upper(), fill, tcol)
    pr = tc.get("priority")
    if pr in T.PRIORITY:
        pf, pc = T.PRIORITY[pr]
        sep = p2.add_run("   ")
        sep.font.size = Pt(8.5)
        _chip_run(p2, "PRIORITY: " + pr.upper(), pf, pc)

    if tc.get("objective"):
        p3 = cell.add_paragraph()
        p3.paragraph_format.space_before = Pt(4)
        p3.paragraph_format.space_after = Pt(0)
        lab = p3.add_run("Objective:  ")
        lab.font.bold = True
        lab.font.size = Pt(9)
        lab.font.color.rgb = _rgb(T.MUTED)
        val = p3.add_run(tc["objective"])
        val.font.size = Pt(9.5)
        val.italic = True
        val.font.color.rgb = _rgb("3A3F4A")


def _preconditions_line(doc, items):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(2)
    lab = p.add_run("Preconditions:  ")
    lab.font.bold = True
    lab.font.size = Pt(9)
    lab.font.color.rgb = _rgb(T.WARN_BAR)
    run = p.add_run("  ".join("\u2022 " + it for it in items))
    run.font.size = Pt(9)
    run.font.color.rgb = _rgb("4A4F5A")


def _steps_table(doc, steps):
    table = doc.add_table(rows=1, cols=4)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    _disable_autofit_fixed(table)
    _set_table_borders(table, color=T.BORDER, size=4)
    widths = [0.42, 2.35, 2.15, 2.23]
    _set_col_widths(table, widths)

    headers = ["#", "Test Step / Action", "Test Data (format / value)", "Expected Result"]
    hdr = table.rows[0]
    _set_repeat_header(hdr)
    for i, h in enumerate(headers):
        cell = hdr.cells[i]
        _set_cell_bg(cell, T.HEADER_FILL)
        _set_cell_margins(cell, top=60, bottom=60, left=100, right=100)
        _set_cell_vertical_alignment(cell, "center")
        para = cell.paragraphs[0]
        para.paragraph_format.space_after = Pt(0)
        para.alignment = WD_ALIGN_PARAGRAPH.LEFT if i else WD_ALIGN_PARAGRAPH.CENTER
        run = para.add_run(h)
        run.font.bold = True
        run.font.size = Pt(9)
        run.font.color.rgb = _rgb(T.HEADER_TEXT)

    for idx, st in enumerate(steps, start=1):
        row = table.add_row()
        zebra = T.ZEBRA_FILL if idx % 2 == 1 else "FFFFFF"
        cells = row.cells
        for c in cells:
            _set_cell_bg(c, zebra)
            _set_cell_margins(c, top=55, bottom=55, left=100, right=100)
            _set_cell_vertical_alignment(c, "top")

        # number
        p0 = cells[0].paragraphs[0]
        p0.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p0.paragraph_format.space_after = Pt(0)
        r0 = p0.add_run(str(idx))
        r0.font.bold = True
        r0.font.size = Pt(9.5)
        r0.font.color.rgb = _rgb(T.PRIMARY_LIGHT)

        # action
        p1 = cells[1].paragraphs[0]
        p1.paragraph_format.space_after = Pt(0)
        r1 = p1.add_run(st["action"])
        r1.font.size = Pt(9)

        # data (mono)
        p2 = cells[2].paragraphs[0]
        p2.paragraph_format.space_after = Pt(0)
        r2 = p2.add_run(st["data"])
        r2.font.size = Pt(8.5)
        r2.font.name = T.FONT_MONO
        r2.font.color.rgb = _rgb("394150")

        # expected
        p3 = cells[3].paragraphs[0]
        p3.paragraph_format.space_after = Pt(0)
        r3 = p3.add_run(st["expected"])
        r3.font.size = Pt(9)
        r3.font.color.rgb = _rgb("1E3A24")
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def _postconditions_line(doc, items, label="Postconditions"):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(6)
    lab = p.add_run("{}:  ".format(label))
    lab.font.bold = True
    lab.font.size = Pt(9)
    lab.font.color.rgb = _rgb(T.AC_BAR)
    run = p.add_run("  ".join("\u2022 " + it for it in items))
    run.font.size = Pt(9)
    run.font.color.rgb = _rgb("4A4F5A")


def _header_footer(doc, story):
    section = doc.sections[0]
    # Footer
    footer = section.footer
    footer.is_linked_to_previous = False
    fp = footer.paragraphs[0]
    fp.text = ""
    fp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _add_top_rule(fp, T.BORDER, size=6)
    run = fp.add_run("{}  \u2022  {}   ".format(story["id"], story["title"]))
    run.font.size = Pt(8)
    run.font.color.rgb = _rgb(T.MUTED)
    run2 = fp.add_run("        Page ")
    run2.font.size = Pt(8)
    run2.font.color.rgb = _rgb(T.MUTED)
    _field(fp, "PAGE")
    run3 = fp.add_run(" of ")
    run3.font.size = Pt(8)
    run3.font.color.rgb = _rgb(T.MUTED)
    _field(fp, "NUMPAGES")

    # Header
    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = hp.add_run("DXV \u2014 Data Exchange Vault   |   Feedback (Quarantine Export) Test Suite")
    hr.font.size = Pt(8)
    hr.font.color.rgb = _rgb("9AA3B2")
    hr.italic = True


def _add_top_rule(paragraph, hex_color, size=6):
    pPr = paragraph._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr")
    top = OxmlElement("w:top")
    top.set(qn("w:val"), "single")
    top.set(qn("w:sz"), str(size))
    top.set(qn("w:space"), "4")
    top.set(qn("w:color"), hex_color)
    pbdr.append(top)
    pPr.append(pbdr)


def _summary_counts(story):
    by_type = {}
    for tc in story["tests"]:
        by_type[tc["type"]] = by_type.get(tc["type"], 0) + 1
    return by_type


def _test_summary_strip(doc, story):
    counts = _summary_counts(story)
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(8)
    lead = p.add_run("Coverage:  ")
    lead.font.bold = True
    lead.font.size = Pt(9.5)
    lead.font.color.rgb = _rgb(T.SECONDARY)
    total = sum(counts.values())
    tot = p.add_run("{} test case(s)   ".format(total))
    tot.font.size = Pt(9.5)
    tot.font.color.rgb = _rgb("23272F")
    for ttype, n in counts.items():
        fill, tcol = T.CHIP.get(ttype, ("E6E6E6", "333"))
        _chip_run(p, "{} x{}".format(ttype, n), fill, tcol)
        p.add_run(" ").font.size = Pt(8)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------
def build_docx(story, out_path):
    doc = Document()

    # Page geometry — comfortable margins
    section = doc.sections[0]
    section.page_width = Inches(8.5)
    section.page_height = Inches(11)
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.7)
    section.left_margin = Inches(0.65)
    section.right_margin = Inches(0.65)

    _style_base(doc)
    _header_footer(doc, story)

    # --- Title band + metadata ---------------------------------------------
    _title_band(doc, story)
    _metadata_grid(doc, story)

    # --- User story statement ----------------------------------------------
    _section_heading(doc, "User Story")
    _callout(
        doc,
        [
            "As a {}".format(story["persona"]),
            "I want {}".format(story["want"]),
            "so that {}.".format(story["benefit"].rstrip(".")),
        ],
        T.INFO_FILL, T.INFO_BAR, bold_first=False,
    )

    # --- Description --------------------------------------------------------
    _section_heading(doc, "Description")
    for para_text in story["description"]:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(6)
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = p.add_run(para_text)
        run.font.size = Pt(10.5)

    # --- Key terms ----------------------------------------------------------
    if story.get("context"):
        _section_heading(doc, "Key Terms & Behaviour")
        _definition_table(doc, story["context"])

    # --- Acceptance criteria ------------------------------------------------
    _section_heading(doc, "Acceptance Criteria")
    _bulleted_callout(doc, story["acceptance"], T.AC_FILL, T.AC_BAR,
                      "Definition of Done", numbered=True)

    # --- Recommended test data ---------------------------------------------
    if story.get("test_data"):
        _section_heading(doc, "Recommended Test Data")
        _definition_table(doc, story["test_data"])

    # --- Global preconditions ----------------------------------------------
    if story.get("preconditions"):
        _section_heading(doc, "Global Preconditions")
        _bulleted_callout(doc, story["preconditions"], T.WARN_FILL, T.WARN_BAR,
                          "Environment & Setup", numbered=False)

    # --- Test cases ---------------------------------------------------------
    _section_heading(doc, "Test Cases", color=T.PRIMARY)
    _test_summary_strip(doc, story)

    for tc in story["tests"]:
        _test_case_header(doc, tc)
        if tc.get("preconditions"):
            _preconditions_line(doc, tc["preconditions"])
        _steps_table(doc, tc["steps"])
        if tc.get("postconditions"):
            _postconditions_line(doc, tc["postconditions"])

    # --- Footer note --------------------------------------------------------
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(10)
    _add_top_rule(p, T.BORDER, size=6)
    note = p.add_run(
        "Generated for the DXV Feedback (Quarantine Export) integration test suite "
        "\u2014 {}.".format(_dt.date.today().isoformat())
    )
    note.font.size = Pt(8)
    note.italic = True
    note.font.color.rgb = _rgb(T.MUTED)

    doc.save(out_path)
    return out_path
