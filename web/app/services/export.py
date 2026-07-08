from io import BytesIO

from openpyxl import Workbook
from openpyxl.chart import BarChart, Reference
from weasyprint import HTML


def to_xlsx(sheet_title, headers, rows, total_row, chart=False):
    """Genera un XLSX con tabla tipada + fila de totales opcional.

    `chart=True` (usado solo para Estado de Resultados) añade un gráfico de
    barras nativo (Ventas/Gastos por periodo) referenciando las celdas de la
    hoja; no aplica a los demás tipos de reporte (firma retrocompatible).
    """
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_title[:31]  # límite de Excel
    ws.append(headers)
    for row in rows:
        ws.append(row)
    if rows and total_row is not None:
        ws.append(total_row)
    if chart and rows:
        bar = BarChart()
        bar.type = "col"
        bar.grouping = "clustered"
        bar.title = "Ventas vs Gastos por periodo"
        max_row = 1 + len(rows)
        data = Reference(ws, min_col=2, max_col=3, min_row=1, max_row=max_row)
        cats = Reference(ws, min_col=1, min_row=2, max_row=max_row)
        bar.add_data(data, titles_from_data=True)
        bar.set_categories(cats)
        ws.add_chart(bar, "H2")
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_pdf(html_string):
    return HTML(string=html_string).write_pdf()
