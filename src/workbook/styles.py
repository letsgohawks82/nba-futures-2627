"""Institutional formatting helpers (Arial 10; blue inputs / black formulas / green cross-sheet links / red flags; navy headers; no merged cells)."""
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

FONT = "Arial"
NAVY = "1F3864"
BLUE, BLACK, GREEN, RED = "0000FF", "000000", "008000", "FF0000"
ORANGE = "FFC000"
FMT = dict(pct="0.0%", pct2="0.00%", amer='+0;-0', money="$#,##0", dec="0.00", int="0", num1="0.0", num2="0.00", num3="0.000", text="@", gen="General", date="yyyy-mm-dd")
THIN = Side(style="thin"); DOUBLE = Side(style="double")


def font(color=BLACK, bold=False, italic=False, size=10):
    return Font(name=FONT, size=size, bold=bold, italic=italic, color=color)


def put(ws, ref, value, kind="formula", fmt=None, bold=False, align=None, wrap=False, italic=False):
    """kind: input (blue), formula (black), link (green: cross-sheet), text (black), header (white on navy), flag (red)"""
    c = ws[ref]; c.value = value
    color = {"input": BLUE, "formula": BLACK, "link": GREEN, "text": BLACK, "header": "FFFFFF", "flag": RED}[kind]
    c.font = font(color, bold=bold or kind == "header", italic=italic)
    if kind == "header":
        c.fill = PatternFill("solid", fgColor=NAVY); c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    else:
        c.alignment = Alignment(horizontal=align, wrap_text=wrap, vertical="center" if wrap else None)
    if fmt:
        c.number_format = FMT.get(fmt, fmt)
    return c


def sheet_header(ws, name, project="NBA 2026-27 Futures Model", version="v1 | 2026-10-15", span=8):
    ws.sheet_view.showGridLines = False
    put(ws, "A1", project, "text", bold=True); ws["A1"].font = font(NAVY, bold=True, size=12)
    put(ws, "A2", name, "text", bold=True); put(ws, "A3", f"Version: {version}", "text", italic=True)
    ws.row_dimensions[4].height = 6
    for r in (1, 2, 3):
        ws.row_dimensions[r].height = 15
    # center-across-selection title band (no merged cells)
    for col in range(1, span + 1):
        ws.cell(row=1, column=col).alignment = Alignment(horizontal="centerContinuous" if col > 1 else "centerContinuous")
    ws["A1"].alignment = Alignment(horizontal="centerContinuous")


def headers(ws, row, labels, start_col=1, height=30):
    for i, lab in enumerate(labels):
        put(ws, f"{get_column_letter(start_col + i)}{row}", lab, "header")
    ws.row_dimensions[row].height = height


def widths(ws, spec):
    for col, w in spec.items():
        ws.column_dimensions[col].width = w


def finish(ws, first_data_row=5, label_cols=("A",), min_label=24, min_num=14):
    """Default widths >= spec minimums, data row height 15 (spec), Arial everywhere."""
    for col in range(1, ws.max_column + 1):
        L = get_column_letter(col)
        cur = ws.column_dimensions[L].width or 0
        ws.column_dimensions[L].width = max(cur, min_label if L in label_cols else min_num)


def subtotal_border(ws, row, c1, c2):
    for col in range(c1, c2 + 1):
        ws.cell(row=row, column=col).border = Border(bottom=THIN)


def total_border(ws, row, c1, c2):
    for col in range(c1, c2 + 1):
        ws.cell(row=row, column=col).border = Border(top=DOUBLE, bottom=DOUBLE)
