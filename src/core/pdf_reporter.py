"""RF Imperium — PDF Reporter (raporty sesji)"""
from datetime import datetime
from pathlib import Path

REPORTS_DIR = Path.home() / ".rf_imperium" / "reports"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class PDFReporter:
    def __init__(self):
        self.entries = []
        self.session_name = "RF Session"
        self.operator = ""

    def set_session(self, name: str, operator=""):
        self.session_name = name
        self.operator = operator

    def add_info(self, title: str, data: dict):
        self.entries.append({"type": "info", "title": title, "data": data})

    def add_signals_table(self, signals: list, columns: list):
        self.entries.append({
            "type": "table", "title": "Tabela Odebranych Sygnałów",
            "rows": signals, "columns": columns
        })

    def add_text(self, title: str, text: str):
        self.entries.append({"type": "text", "title": title, "text": text})

    def generate(self, filename=None) -> str:
        if filename is None:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = str(REPORTS_DIR / f"report_{ts}.pdf")
        try:
            return self._pdf(filename)
        except ImportError:
            return self._txt(filename)

    def _pdf(self, filename: str) -> str:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table,
            TableStyle, HRFlowable,
        )
        from reportlab.lib.enums import TA_CENTER

        doc = SimpleDocTemplate(
            filename, pagesize=A4,
            leftMargin=2 * cm, rightMargin=2 * cm,
            topMargin=2 * cm, bottomMargin=2 * cm,
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "rfi_title", parent=styles["Heading1"],
            alignment=TA_CENTER, fontSize=18,
            textColor=colors.HexColor("#0066CC"),
        )
        story = [
            Paragraph("RF IMPERIUM — Raport Sesji RF", title_style),
            Spacer(1, 0.2 * cm),
            Paragraph(
                f"Sesja: {self.session_name}  |  "
                f"Operator: {self.operator or '—'}  |  "
                f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                styles["Normal"],
            ),
            HRFlowable(width="100%", thickness=1, color=colors.grey),
            Spacer(1, 0.4 * cm),
        ]

        for entry in self.entries:
            story.append(Paragraph(entry["title"], styles["Heading2"]))
            if entry["type"] == "info":
                rows = [["Parametr", "Wartość"]] + [
                    [str(k), str(v)] for k, v in entry["data"].items()
                ]
                t = Table(rows, colWidths=[6 * cm, 11 * cm])
                t.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1a2e")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.whitesmoke, colors.white]),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                ]))
                story.append(t)
            elif entry["type"] == "table":
                cols = entry["columns"]
                rows_data = entry["rows"][:100]
                table_rows = [cols] + [[str(x) for x in r] for r in rows_data]
                if table_rows:
                    col_w = 17 * cm / max(len(cols), 1)
                    t = Table(table_rows, colWidths=[col_w] * len(cols))
                    t.setStyle(TableStyle([
                        ("BACKGROUND", (0, 0), (-1, 0),
                         colors.HexColor("#1a1a2e")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("FONTSIZE", (0, 0), (-1, -1), 7),
                        ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
                         [colors.whitesmoke, colors.white]),
                    ]))
                    story.append(t)
            elif entry["type"] == "text":
                story.append(Paragraph(
                    entry["text"].replace("\n", "<br/>"),
                    styles["Normal"],
                ))
            story.append(Spacer(1, 0.4 * cm))

        doc.build(story)
        return filename

    def _txt(self, filename: str) -> str:
        """Fallback TXT gdy reportlab niedostępny"""
        txt_path = filename.replace(".pdf", ".txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"RF IMPERIUM — Raport\n")
            f.write(f"Sesja: {self.session_name}  |  {datetime.now()}\n")
            f.write("=" * 60 + "\n\n")
            for entry in self.entries:
                f.write(f"### {entry['title']}\n")
                if entry["type"] == "info":
                    for k, v in entry["data"].items():
                        f.write(f"  {k}: {v}\n")
                elif entry["type"] == "text":
                    f.write(entry["text"] + "\n")
                f.write("\n")
        return txt_path

    def clear(self):
        self.entries = []
