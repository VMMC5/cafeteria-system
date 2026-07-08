from io import BytesIO

from openpyxl import Workbook
from weasyprint import HTML


def to_xlsx(sheet_title, headers, rows, total_row):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]  # límite de Excel
    ws.append(headers)
    for row in rows:
        ws.append(row)
    if rows and total_row is not None:
        ws.append(total_row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_pdf(html_string):
    return HTML(string=html_string).write_pdf()
