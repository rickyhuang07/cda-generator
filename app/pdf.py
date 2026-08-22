from __future__ import annotations

from io import BytesIO

from reportlab.lib.colors import HexColor, black
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models import Transaction, format_date, format_money, possessive

NAVY = HexColor("#1b365d")
RULE = HexColor("#c5a46e")
MUTED = HexColor("#4a5568")
LINE = HexColor("#d6d3cd")
LIGHT = HexColor("#f4f1ea")


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "CdaTitle",
            parent=base["Title"],
            fontName="Times-Bold",
            fontSize=16,
            textColor=NAVY,
            alignment=TA_CENTER,
            spaceAfter=2,
            leading=20,
        ),
        "section": ParagraphStyle(
            "CdaSection",
            parent=base["Heading2"],
            fontName="Times-Bold",
            fontSize=10.5,
            textColor=NAVY,
            spaceBefore=6,
            spaceAfter=2,
            leading=13,
        ),
        "label": ParagraphStyle(
            "CdaLabel",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=10,
            textColor=black,
            leading=13,
        ),
        "body": ParagraphStyle(
            "CdaBody",
            parent=base["Normal"],
            fontName="Times-Roman",
            fontSize=10,
            textColor=black,
            leading=13,
        ),
        "muted": ParagraphStyle(
            "CdaMuted",
            parent=base["Normal"],
            fontName="Times-Italic",
            fontSize=8.5,
            textColor=MUTED,
            leading=11,
        ),
        "right": ParagraphStyle(
            "CdaRight",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=10,
            alignment=TA_RIGHT,
            leading=13,
        ),
        "money": ParagraphStyle(
            "CdaMoney",
            parent=base["Normal"],
            fontName="Times-Bold",
            fontSize=11,
            alignment=TA_RIGHT,
            textColor=NAVY,
            leading=14,
        ),
    }


def _kv_table(pairs: list[tuple[str, str]], styles: dict[str, ParagraphStyle], cols: int = 2) -> Table:
    cells: list[list] = []
    row: list = []
    for label, value in pairs:
        block = [
            Paragraph(label, styles["label"]),
            Paragraph(value or "—", styles["body"]),
        ]
        inner = Table([[block[0]], [block[1]]], colWidths=[3.35 * inch])
        inner.setStyle(
            TableStyle(
                [
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 0),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        row.append(inner)
        if len(row) == cols:
            cells.append(row)
            row = []
    if row:
        while len(row) < cols:
            row.append("")
        cells.append(row)
    table = Table(cells, colWidths=[3.5 * inch, 3.5 * inch])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _money_row(label: str, amount: str, styles: dict[str, ParagraphStyle], emphasis: bool = False) -> Table:
    left = Paragraph(label, styles["label"] if emphasis else styles["body"])
    right = Paragraph(amount, styles["money"] if emphasis else styles["right"])
    table = Table([[left, right]], colWidths=[5.4 * inch, 1.6 * inch])
    cmds = [
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if emphasis:
        cmds.append(("BACKGROUND", (0, 0), (-1, -1), LIGHT))
    table.setStyle(TableStyle(cmds))
    return table


def build_cda_pdf(tx: Transaction) -> bytes:
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.95 * inch,
        title="Commission Disbursement Authorization",
        author=tx.brokerage_name or "RealtyOne Plus, LLC",
    )

    title_company = (tx.title_company or "").replace(" / ", ", ")
    agent = tx.selling_agent or "Selling Agent"
    
    story = [
        Paragraph("Commission Disbursement Authorization", styles["title"]),
        HRFlowable(width="100%", thickness=2, color=NAVY, spaceAfter=1),
        HRFlowable(width="100%", thickness=0.75, color=RULE, spaceBefore=0, spaceAfter=4),
        
        # Escrow Section
        Paragraph("Escrow Info:", styles["section"]),
        _kv_table(
            [
                ("Escrow Agent:", tx.closer),
                ("Title Company:", title_company),
                ("Phone:", tx.closer_phone),
                ("Email:", tx.closer_email),
            ],
            styles,
        ),
        
        # Transaction Section
        Paragraph("Transaction Info:", styles["section"]),
        _kv_table(
            [
                ("Escrow No:", tx.escrow_no),
                ("Gross Commission:", format_money(tx.gross_commission)),
                ("MLS:", tx.mls),
                ("Sale Price:", format_money(tx.sale_price)),
                ("Close Date:", format_date(tx.close_date)),
                ("Property:", tx.property_address),
                ("Seller:", tx.seller),
                ("Buyer:", tx.buyer),
                ("Selling Agent:", tx.selling_agent),
            ],
            styles,
        ),
        
        # Commission Breakdown Section
        Paragraph("Commission Breakdown", styles["section"]),
        _money_row("Brokerage Gross Commission", format_money(tx.gross_commission), styles, emphasis=True),
        Spacer(1, 4),
        
        Paragraph("Selling Agent Commission", styles["section"]),
        _money_row(f"{possessive(agent)} Commission", format_money(tx.gross_commission), styles),
        Spacer(1, 4),
        
        Paragraph("Additional Agent Closing Fees", styles["section"]),
        Paragraph(
            "*These fees are paid to the brokerage and are reflected in the Net Amount Due to Brokerage line item below",
            styles["muted"],
        ),
        Spacer(1, 2),
        _money_row("Closing Fee", f"({format_money(tx.broker_process_fees)})", styles),
        Spacer(1, 4),
        
        Paragraph("Final Selling Agent Commission", styles["section"]),
        _money_row(f"{possessive(agent)} Commission", format_money(tx.net_due_agent), styles, emphasis=True),
        Spacer(1, 4),
        
        Paragraph("Final Commission Breakdown", styles["section"]),
        _money_row("Total Due to Brokerage", format_money(tx.gross_commission), styles),
        Spacer(1, 6),
        _money_row("Net Amount Due to Brokerage:", format_money(tx.net_due_brokerage), styles, emphasis=True),
        Paragraph(
            f"Please mail check to {tx.brokerage_name or 'RealtyOne Plus, LLC'}, {tx.brokerage_mail_address}",
            styles["muted"],
        ),
        Spacer(1, 4),
        _money_row(f"Net Amount Due to {agent}:", format_money(tx.net_due_agent), styles, emphasis=True),
        Paragraph(
            f"Please mail check to {tx.agent_payee_address or '[agent mailing address]'}",
            styles["muted"],
        ),
        Spacer(1, 14),
    ]

    # Signature Block
    sig_image = Image("static/signature.png", width=120, height=35)
    sig_image.hAlign = 'LEFT'
    sig = Table(
        [
            [
                sig_image,
                "",
            ],
            [
                Paragraph("______________________", styles["body"]),
                Paragraph("______________________", styles["body"]),
            ],
            [
                Paragraph(f"Broker – {tx.broker_name or 'Jinglin Xu'}", styles["body"]),
                Paragraph("Date", styles["body"]),
            ],
            [
                "",
                Paragraph(format_date(tx.today), styles["body"]),
            ],
        ],
        colWidths=[3.5 * inch, 3.5 * inch],
    )
    sig.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "BOTTOM"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(sig)

    # Footer Drawing Handler
    def _footer(canvas, _doc):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(0.7 * inch, 0.82 * inch, 7.8 * inch, 0.82 * inch)
        canvas.setFillColor(MUTED)
        canvas.setFont("Times-Roman", 8.5)
        y = 0.66 * inch
        for line in (
            tx.brokerage_name or "RealtyOne Plus, LLC",
            tx.brokerage_mail_address or "3130 Grants Lake BLVD #17272, Sugar Land, TX 77496",
            f"{tx.brokerage_email or 'RealtyOnePlus@hotmail.com'}   {tx.brokerage_phone or '(281) 410-8725'}",
        ):
            if line:
                canvas.drawString(0.7 * inch, y, line)
                y -= 11
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()