"""Export selected .docx files to PDF via Word COM, then render page images
with PyMuPDF for visual inspection. Cleans up the Word instance it creates.
"""
import os
import sys
import glob

import pythoncom  # noqa
import win32com.client as win32

HERE = os.path.dirname(os.path.abspath(__file__))
WD_FORMAT_PDF = 17

targets = [
    "DXV-FRE-000_Test-Suite-Overview.docx",
    "DXV-FRE-005_Envelope-Flag-File-Generation-and-Semantics.docx",
]

pythoncom.CoInitialize()
word = win32.DispatchEx("Word.Application")  # dedicated instance
word.Visible = False
word.DisplayAlerts = False
pdfs = []
try:
    for name in targets:
        src = os.path.join(HERE, name)
        dst = os.path.splitext(src)[0] + ".preview.pdf"
        doc = word.Documents.Open(src, ReadOnly=True)
        doc.SaveAs(dst, FileFormat=WD_FORMAT_PDF)
        doc.Close(False)
        pdfs.append(dst)
        print("PDF:", os.path.basename(dst))
finally:
    word.Quit()
    pythoncom.CoUninitialize()

# Render page images
import fitz
for pdf in pdfs:
    d = fitz.open(pdf)
    base = os.path.splitext(os.path.basename(pdf))[0].replace(".preview", "")
    for i in range(min(2, d.page_count)):
        page = d.load_page(i)
        pix = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6))
        out = os.path.join(HERE, "_preview_{}_p{}.png".format(base, i + 1))
        pix.save(out)
        print("IMG:", os.path.basename(out), pix.width, "x", pix.height)
    d.close()
print("DONE")
