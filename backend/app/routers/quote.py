import os
from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from app.schemas.quote import QuoteRequest
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

router = APIRouter(prefix="/api/quotations", tags=["Quotations"])

PDF_DIR = os.path.join("storage", "pdf")
os.makedirs(PDF_DIR, exist_ok=True)

@router.post("/generate-pdf")
def generate_quote_pdf(data: QuoteRequest, db: Session = Depends(get_db)):
    filename = f"quotation_{data.company_name.lower().replace(' ', '_')}.pdf"
    filepath = os.path.join(PDF_DIR, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Title'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#1c1917"),
        alignment=0
    )

    body_style = ParagraphStyle(
        'InvoiceBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#44403c")
    )

    elements.append(Paragraph("<b>MARBLE AI INDUSTRIAL B2B QUOTATION</b>", title_style))
    elements.append(Spacer(1, 10))

    meta_text = f"<b>Client Contact:</b> {data.client_name}<br/><b>Company / Project:</b> {data.company_name}<br/><b>Document Type:</b> Official Commercial Tax Estimate"
    elements.append(Paragraph(meta_text, body_style))
    elements.append(Spacer(1, 15))

    table_data = [["Material & Tile Description", "SKU", "Qty", "Size (cm)", "Area (m²)", "Rate/m²", "Total ($)"]]
    subtotal = 0.0

    for item in data.items:
        area_per_piece = (item.length_cm * item.width_cm) / 10000.0
        total_sqm = round(area_per_piece * item.quantity, 2)
        item_base_total = round(total_sqm * item.price_per_sqm, 2)
        subtotal += item_base_total

        table_data.append([
            f"{item.material} - {item.tile_name}",
            item.sku,
            str(item.quantity),
            f"{int(item.length_cm)}x{int(item.width_cm)}",
            f"{total_sqm:.1f} m²",
            f"${item.price_per_sqm:.2f}",
            f"${item_base_total:.2f}"
        ])

    gst_amount = round(subtotal * 0.18, 2)
    grand_total = round(subtotal + gst_amount, 2)

    table_data.append(["", "", "", "", "", "Subtotal:", f"${subtotal:.2f}"])
    table_data.append(["", "", "", "", "", "GST (18%):", f"${gst_amount:.2f}"])
    table_data.append(["", "", "", "", "", "Grand Total:", f"${grand_total:.2f}"])

    t = Table(table_data, colWidths=[150, 70, 40, 55, 60, 65, 90])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1c1917")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -4), 0.5, colors.HexColor("#d6d3d1")),
        ('LINEBELOW', (0, -4), (-1, -1), 0.5, colors.HexColor("#d6d3d1")),
        ('BACKGROUND', (5, -3), (-1, -1), colors.HexColor("#fafaf9")),
        ('FONTNAME', (5, -3), (-1, -1), 'Helvetica-Bold'),
        ('ALIGN', (5, -3), (5, -1), 'RIGHT'),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 20))

    terms_text = "<b>Terms & Conditions:</b><br/>1. Validity: This quotation is valid for 15 days from issuance.<br/>2. Freight & Transit Insurance: Extra as per actual delivery location.<br/>3. Natural Variation: Natural marble and stone slabs possess inherent geological variations in veining and shade."
    elements.append(Paragraph(terms_text, body_style))

    # --- SAVE TO DATABASE ---
    try:
        db.execute(
            text("INSERT INTO quotations_history (client_name, company_name, total_amount) VALUES (:c, :comp, :t)"),
            {"c": data.client_name, "comp": data.company_name, "t": grand_total}
        )
        db.commit()
        print(f"[SUCCESS] Saved quotation to DB for {data.company_name}: ${grand_total}")
    except Exception as e:
        db.rollback()
        print(f"[DATABASE ERROR] Failed to save quote: {e}")
    # ------------------------

    doc.build(elements)

    return FileResponse(filepath, media_type='application/pdf', filename=filename)