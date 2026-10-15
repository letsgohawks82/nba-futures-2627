import os, tempfile, xlwings as xw
p = os.path.join(tempfile.gettempdir(), "xl_smoke.xlsx")
app = xw.App(visible=False, add_book=False)
try:
    wb = app.books.add()
    ws = wb.sheets[0]
    ws["A1"].value = 2; ws["A2"].formula = "=A1*21"
    app.calculate()
    v = ws["A2"].value
    wb.save(p); wb.close()
    print("Excel version:", app.version, "| A2 =", v, "| OK" if v == 42 else "| FAIL")
finally:
    app.quit()
