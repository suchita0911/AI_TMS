"""Render a completion certificate as a PDF with an embedded QR code."""
from __future__ import annotations

import io

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def _qr_image(data: str) -> ImageReader:
    img = qrcode.make(data)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return ImageReader(buf)


def build_certificate_pdf(
    *,
    employee_name: str,
    course_name: str,
    completion_date: str,
    certificate_number: str,
    score: float | None,
    verify_url: str,
) -> bytes:
    buf = io.BytesIO()
    width, height = landscape(A4)
    c = canvas.Canvas(buf, pagesize=landscape(A4))

    # Border
    c.setStrokeColor(colors.HexColor("#4F46E5"))
    c.setLineWidth(4)
    c.rect(15 * mm, 15 * mm, width - 30 * mm, height - 30 * mm)
    c.setLineWidth(1)
    c.setStrokeColor(colors.HexColor("#A5B4FC"))
    c.rect(18 * mm, 18 * mm, width - 36 * mm, height - 36 * mm)

    center = width / 2

    c.setFillColor(colors.HexColor("#4F46E5"))
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(center, height - 55 * mm, "Certificate of Completion")

    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 14)
    c.drawCentredString(center, height - 75 * mm, "This is proudly presented to")

    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(center, height - 92 * mm, employee_name)

    c.setFont("Helvetica", 14)
    c.setFillColor(colors.HexColor("#334155"))
    c.drawCentredString(center, height - 108 * mm, "for successfully completing the course")

    c.setFillColor(colors.HexColor("#1E293B"))
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(center, height - 122 * mm, course_name)

    if score is not None:
        c.setFont("Helvetica", 12)
        c.setFillColor(colors.HexColor("#059669"))
        c.drawCentredString(center, height - 134 * mm, f"Score: {score}%")

    # Footer details
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 11)
    c.drawString(30 * mm, 30 * mm, f"Certificate No: {certificate_number}")
    c.drawString(30 * mm, 24 * mm, f"Date: {completion_date}")

    # QR code (verification)
    qr = _qr_image(verify_url)
    c.drawImage(qr, width - 55 * mm, 22 * mm, 30 * mm, 30 * mm)
    c.setFont("Helvetica", 8)
    c.drawCentredString(width - 40 * mm, 19 * mm, "Scan to verify")

    c.showPage()
    c.save()
    return buf.getvalue()
