from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.platypus import (
    HRFlowable,
    Image as PlatypusImage,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _clean_bullet_text(text: str) -> str:
    """Strips leading bullet symbols, dashes, and asterisks from item strings."""
    t = str(text).strip()
    while t and t[0] in ("•", "-", "*", " "):
        t = t[1:].strip()
    return t


class NumberedCanvas(canvas.Canvas):
    """Canvas that performs a two-pass calculation to draw accurate 'Page X of Y' footers."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states: List[Dict[str, Any]] = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_footer(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(HexColor("#64748b"))

        # Footer divider line
        self.setStrokeColor(HexColor("#e2e8f0"))
        self.setLineWidth(0.5)
        self.line(36, 32, self._pagesize[0] - 36, 32)

        # Footer text
        self.drawString(36, 20, "TruthLens Multimodal Forensics Platform — Chain-of-Custody Report")
        page_str = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(self._pagesize[0] - 36, 20, page_str)
        self.restoreState()


def resolve_local_path(url_or_path: Optional[str]) -> Optional[Path]:
    """Resolves an absolute file path or static /storage/ URL to a valid disk Path."""
    if not url_or_path:
        return None
    p = Path(url_or_path)
    if p.exists() and p.is_file():
        return p

    base_dir = Path(__file__).resolve().parent.parent
    if str(url_or_path).startswith("/storage/"):
        target = base_dir / str(url_or_path).lstrip("/")
        if target.exists() and target.is_file():
            return target
    return None


def generate_forensic_pdf(case_record: Dict[str, Any], output_path: str) -> str:
    """Generates a professional forensic PDF report from a case record."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=42,
    )

    styles = getSampleStyleSheet()

    # Custom Forensic Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=18,
        leading=22,
        textColor=HexColor("#0f172a"),
    )
    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=HexColor("#1e3a8a"),
    )
    section_heading = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=4,
        keepWithNext=True,
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=styles["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=8.5,
        leading=11,
        textColor=HexColor("#7c2d12"),
    )
    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=HexColor("#1e293b"),
    )
    bold_body = ParagraphStyle(
        "BoldBody",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=HexColor("#0f172a"),
    )
    table_cell = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=HexColor("#1e293b"),
    )
    table_header = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )
    hash_cell = ParagraphStyle(
        "HashCell",
        parent=styles["Normal"],
        fontName="Courier",
        fontSize=6.5,
        leading=8,
        textColor=HexColor("#334155"),
    )
    caption_label = ParagraphStyle(
        "ThumbCaption",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8,
        leading=10,
        alignment=1,  # Centered
        textColor=HexColor("#334155"),
    )

    story: List[Any] = []

    case_id = case_record.get("case_id") or case_record.get("id", "TL-UNKNOWN")
    created_at = case_record.get("created_at", "N/A")
    result: Dict[str, Any] = case_record.get("result") or {}

    overall_risk = result.get("overall_risk_band", "Needs Review")
    conf = result.get("calibrated_confidence", 0.0)
    review_status = case_record.get("review_status", "needs_review")
    review_notes = case_record.get("review_notes", "")

    # Risk Band Color Coding
    if "High" in overall_risk:
        risk_color = HexColor("#dc2626")
        risk_bg = HexColor("#fef2f2")
    elif "Low" in overall_risk:
        risk_color = HexColor("#059669")
        risk_bg = HexColor("#ecfdf5")
    else:
        risk_color = HexColor("#d97706")
        risk_bg = HexColor("#fffbeb")

    # 1. Header Banner
    header_table_data = [
        [
            Paragraph("TRUTHLENS FORENSIC INTELLIGENCE", subtitle_style),
            Paragraph(f"<b>CASE REF:</b> {case_id}", ParagraphStyle("Ref", parent=table_cell, alignment=2)),
        ],
        [
            Paragraph("Digital Media Authentication & Forensic Audit Report", title_style),
            Paragraph(f"<b>Analysis Date:</b> {created_at[:19]} UTC", ParagraphStyle("Date", parent=table_cell, alignment=2)),
        ],
    ]
    header_table = Table(header_table_data, colWidths=[360, 180])
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
            ]
        )
    )
    story.append(header_table)
    story.append(Spacer(1, 6))

    # Assessment Card (Overall Risk + Confidence + Disclaimer Banner)
    assessment_data = [
        [
            Paragraph(f"<b>OVERALL RISK BAND:</b> <font color='{risk_color}'><b>{overall_risk.upper()}</b></font>", bold_body),
            Paragraph(f"<b>CALIBRATED CONFIDENCE:</b> {conf * 100:.1f}%", bold_body),
            Paragraph(f"<b>HUMAN AUDIT STATUS:</b> {review_status.replace('_', ' ').upper()}", bold_body),
        ],
        [
            Paragraph(
                "<b>CRITICAL NOTICE:</b> Automated forensic scores reflect probabilistic digital indicators, "
                "not definitive proof of authenticity or manipulation. Results must be evaluated in conjunction "
                "with human verification of source provenance and physical context.",
                disclaimer_style,
            ),
            "",
            "",
        ],
    ]
    assessment_table = Table(assessment_data, colWidths=[180, 180, 180])
    assessment_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), risk_bg),
                ("BOX", (0, 0), (-1, -1), 1, risk_color),
                ("INNERGRID", (0, 0), (-1, 0), 0.5, HexColor("#cbd5e1")),
                ("SPAN", (0, 1), (2, 1)),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(assessment_table)
    story.append(Spacer(1, 10))

    # 2. Executive Summary
    story.append(Paragraph("1. Executive Summary", section_heading))
    summary_text = result.get("summary") or "Forensic analysis completed across submitted evidence."
    story.append(Paragraph(summary_text, body_style))
    if case_record.get("caption_text"):
        story.append(Spacer(1, 4))
        story.append(
            Paragraph(
                f"<b>Ingested Caption / Context Claims:</b> <i>\"{case_record['caption_text']}\"</i>",
                table_cell,
            )
        )
    story.append(Spacer(1, 8))

    # 3. Source Evidence & SHA-256 Traceability Table
    story.append(Paragraph("2. Evidence Chain-of-Custody & SHA-256 Hashes", section_heading))
    files = case_record.get("files", [])
    ev_rows = [
        [
            Paragraph("Filename", table_header),
            Paragraph("Media Type", table_header),
            Paragraph("Size (Bytes)", table_header),
            Paragraph("Cryptographic Hash (SHA-256)", table_header),
        ]
    ]
    if files:
        for f in files:
            orig_name = f.get("original_filename", "unnamed")
            m_type = f.get("media_type", "unknown")
            size_b = f"{f.get('file_size_bytes', 0):,}"
            sha = f.get("sha256_hash", "N/A")
            ev_rows.append(
                [
                    Paragraph(orig_name, table_cell),
                    Paragraph(m_type.upper(), table_cell),
                    Paragraph(size_b, table_cell),
                    Paragraph(sha, hash_cell),
                ]
            )
    else:
        ev_rows.append([Paragraph("No file attachments (text-only case)", table_cell), "", "", ""])

    ev_style = [
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f8fafc")]),
    ]
    if not files:
        ev_style.append(("SPAN", (0, 1), (-1, 1)))

    ev_table = Table(ev_rows, colWidths=[120, 70, 70, 280])
    ev_table.setStyle(TableStyle(ev_style))
    story.append(ev_table)
    story.append(Spacer(1, 10))

    # 4. Modality Analysis Breakdown
    story.append(Paragraph("3. Multimodal Analysis Breakdown", section_heading))
    modalities = result.get("modalities", {})
    mod_rows = [
        [
            Paragraph("Modality", table_header),
            Paragraph("Score", table_header),
            Paragraph("Risk Band", table_header),
            Paragraph("Model Engine", table_header),
            Paragraph("Key Forensic Indicators", table_header),
        ]
    ]

    mod_dict = modalities if isinstance(modalities, dict) else {f"mod_{i}": m for i, m in enumerate(modalities)}
    for mod_name, mod_info in mod_dict.items():
        m_type = mod_info.get("media_type") if isinstance(mod_info, dict) else getattr(mod_info, "media_type", "")
        m_score = mod_info.get("calibrated_score") if isinstance(mod_info, dict) else getattr(mod_info, "calibrated_score", 0.0)
        m_risk = mod_info.get("risk_band") if isinstance(mod_info, dict) else getattr(mod_info, "risk_band", "")
        m_meta = mod_info.get("metadata") if isinstance(mod_info, dict) else getattr(mod_info, "metadata", {})
        m_model = m_meta.get("model_mode", "Standard Engine")
        m_inds = mod_info.get("indicators") if isinstance(mod_info, dict) else getattr(mod_info, "indicators", [])

        if m_inds:
            cleaned_inds = [_clean_bullet_text(ind) for ind in m_inds[:3]]
            inds_p = Paragraph("<br/>".join([f"• {ind}" for ind in cleaned_inds]), table_cell)
        else:
            inds_p = Paragraph("Baseline parameters normal", table_cell)

        mod_rows.append(
            [
                Paragraph(f"<b>{mod_name.upper()}</b>", table_cell),
                Paragraph(f"{float(m_score):.2f}", table_cell),
                Paragraph(m_risk, table_cell),
                Paragraph(m_model, table_cell),
                inds_p,
            ]
        )

    mod_table = Table(mod_rows, colWidths=[70, 45, 105, 90, 230])
    mod_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#1e293b")),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f8fafc")]),
            ]
        )
    )
    story.append(mod_table)
    story.append(Spacer(1, 10))

    # 5. Visual Forensic Evidence (Thumbnails Side-by-Side)
    story.append(Paragraph("4. Visual Forensic Artifacts (Thermal & Activation Overlays)", section_heading))
    thumb_cells: List[Any] = []

    # Check for original image, ELA, and Grad-CAM
    # Gather possible artifact paths
    artifact_candidates: List[Tuple[str, Optional[str]]] = []
    # 1. Original image
    if files:
        for f in files:
            if f.get("media_type") == "image":
                artifact_candidates.append(("Original Evidence", f.get("saved_path")))
                break

    # 2. Key artifacts from modalities
    for m in mod_dict.values():
        urls = m.get("artifact_urls") if isinstance(m, dict) else getattr(m, "artifact_urls", {})
        if "ela" in urls:
            artifact_candidates.append(("ELA Compression Heatmap", urls["ela"]))
        if "gradcam" in urls:
            artifact_candidates.append(("Grad-CAM Neural Focus", urls["gradcam"]))
        for k, u in urls.items():
            if "gradcam" in k and ("Grad-CAM Neural Focus", u) not in artifact_candidates:
                artifact_candidates.append(("Video Keyframe Grad-CAM", u))
            if "ela" in k and ("ELA Compression Heatmap", u) not in artifact_candidates:
                artifact_candidates.append(("Video Keyframe ELA", u))

    valid_thumbs = []
    for label, path_or_url in artifact_candidates[:3]:
        disk_path = resolve_local_path(path_or_url)
        if disk_path and disk_path.exists():
            try:
                img_elem = PlatypusImage(str(disk_path), width=2.1 * inch, height=1.6 * inch)
                valid_thumbs.append((label, img_elem))
            except Exception:
                pass

    if valid_thumbs:
        row_images = [vt[1] for vt in valid_thumbs]
        row_labels = [Paragraph(vt[0], caption_label) for vt in valid_thumbs]
        col_w = 540 / len(valid_thumbs)
        thumbs_table = Table([row_images, row_labels], colWidths=[col_w] * len(valid_thumbs))
        thumbs_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 2),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(thumbs_table)
    else:
        story.append(Paragraph("<i>No visual image/heatmap artifacts available for thumbnail generation.</i>", table_cell))
    story.append(Spacer(1, 10))

    # 6. Flagged Evidence Table
    story.append(Paragraph("5. Flagged Evidence & Spatial/Temporal Hotspots", section_heading))
    flagged = result.get("flagged_evidence", [])
    fe_rows = [
        [
            Paragraph("Modality", table_header),
            Paragraph("Location / Timestamp", table_header),
            Paragraph("Indicator Flag", table_header),
            Paragraph("Severity", table_header),
            Paragraph("Forensic Observation & Rationale", table_header),
        ]
    ]

    if flagged:
        for fe in flagged:
            m_t = fe.get("media_type") if isinstance(fe, dict) else getattr(fe, "media_type", "")
            loc = fe.get("location_or_timestamp") if isinstance(fe, dict) else getattr(fe, "location_or_timestamp", "")
            ind = fe.get("indicator") if isinstance(fe, dict) else getattr(fe, "indicator", "")
            sev = fe.get("severity") if isinstance(fe, dict) else getattr(fe, "severity", "")
            exp = fe.get("explanation") if isinstance(fe, dict) else getattr(fe, "explanation", "")

            sev_color = HexColor("#dc2626") if "high" in sev.lower() else (HexColor("#d97706") if "mod" in sev.lower() else HexColor("#059669"))
            fe_rows.append(
                [
                    Paragraph(m_t.upper(), table_cell),
                    Paragraph(loc, table_cell),
                    Paragraph(ind, table_cell),
                    Paragraph(f"<font color='{sev_color}'><b>{sev.upper()}</b></font>", table_cell),
                    Paragraph(exp, table_cell),
                ]
            )
    else:
        fe_rows.append([Paragraph("No elevated manipulation indicators flagged.", table_cell), "", "", "", ""])

    fe_style = [
        ("BACKGROUND", (0, 0), (-1, 0), HexColor("#0f172a")),
        ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#ffffff"), HexColor("#f8fafc")]),
    ]
    if not flagged:
        fe_style.append(("SPAN", (0, 1), (-1, 1)))

    fe_table = Table(fe_rows, colWidths=[60, 110, 120, 60, 190])
    fe_table.setStyle(TableStyle(fe_style))
    story.append(fe_table)
    story.append(Spacer(1, 10))

    # 7. Cross-Modal Correlation
    story.append(Paragraph("6. Cross-Modal Evidence Correlation", section_heading))
    cm = result.get("cross_modal_correlation") or {}
    cm_status = cm.get("status") if isinstance(cm, dict) else getattr(cm, "status", "single_modality")
    cm_summary = cm.get("summary") if isinstance(cm, dict) else getattr(cm, "summary", "N/A")
    cm_details = cm.get("details") if isinstance(cm, dict) else getattr(cm, "details", [])

    story.append(Paragraph(f"<b>Cross-Modal Status:</b> <b>{str(cm_status).upper()}</b>", bold_body))
    story.append(Spacer(1, 2))
    story.append(Paragraph(cm_summary, body_style))
    if cm_details:
        story.append(Spacer(1, 4))
        for d in cm_details:
            story.append(Paragraph(f"• {_clean_bullet_text(d)}", table_cell))
    story.append(Spacer(1, 10))

    # 8. Limitations, Alternative Explanations & Recommended Human Checks
    sec7_heading = Paragraph("7. Scientific Uncertainty, Limitations & Alternative Explanations", section_heading)
    limits = result.get("limitations_and_caveats", [])
    alts = result.get("alternative_explanations", [])
    recs = result.get("recommended_human_checks", [])

    limits_cleaned = [_clean_bullet_text(l) for l in limits[:4]]
    alts_cleaned = [_clean_bullet_text(a) for a in alts[:4]]
    recs_cleaned = [_clean_bullet_text(r) for r in recs[:4]]

    limits_text = "<br/>".join([f"• {l}" for l in limits_cleaned]) if limits_cleaned else "Standard constraints apply."
    alts_text = "<br/>".join([f"• {a}" for a in alts_cleaned]) if alts_cleaned else "None identified."
    recs_text = "<br/>".join([f"• {r}" for r in recs_cleaned]) if recs_cleaned else "Standard chain-of-custody audit."

    unc_data = [
        [
            Paragraph("<b>Limitations & Caveats:</b>", bold_body),
            Paragraph("<b>Plausible Alternative Explanations:</b>", bold_body),
        ],
        [
            Paragraph(limits_text, table_cell),
            Paragraph(alts_text, table_cell),
        ],
        [
            Paragraph("<b>Recommended Human Verification Checks:</b>", bold_body),
            "",
        ],
        [
            Paragraph(recs_text, table_cell),
            "",
        ],
    ]
    unc_table = Table(unc_data, colWidths=[270, 270], repeatRows=1)
    unc_table.setStyle(
        TableStyle(
            [
                ("SPAN", (0, 2), (1, 2)),
                ("SPAN", (0, 3), (1, 3)),
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 0), (-1, 0), HexColor("#f1f5f9")),
                ("BACKGROUND", (0, 2), (-1, 2), HexColor("#f1f5f9")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(KeepTogether([sec7_heading, unc_table]))
    story.append(Spacer(1, 10))

    # 9. Human Investigator Audit Sign-Off
    story.append(Paragraph("8. Human Forensic Auditor Sign-Off", section_heading))
    sign_off_data = [
        [
            Paragraph("<b>Final Investigator Determination:</b>", bold_body),
            Paragraph(f"<b>{review_status.replace('_', ' ').upper()}</b>", bold_body),
        ],
        [
            Paragraph("<b>Audit Notes / Decision Justification:</b>", bold_body),
            Paragraph(review_notes or "<i>No manual investigator notes recorded. Case awaiting final triage.</i>", table_cell),
        ],
    ]
    sign_off_table = Table(sign_off_data, colWidths=[180, 360])
    sign_off_table.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                ("BACKGROUND", (0, 0), (0, -1), HexColor("#f8fafc")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(sign_off_table)

    # Build PDF with NumberedCanvas
    doc.build(story, canvasmaker=NumberedCanvas)
    return str(output_path)
