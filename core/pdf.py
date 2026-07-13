"""
PDF generator pentru programul de terapie.
"""
from datetime import date, time
from io import BytesIO

from reportlab.lib.pagesizes import landscape, A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, KeepTogether, PageBreak, Flowable
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from django.utils.text import slugify

from core.models import Therapy, Centru, Therapist


class AlignedTableRow(Flowable):
    """Flowable that aligns multiple tables to the same height."""
    
    def __init__(self, tables, col_widths, row_spacing=3*mm):
        super().__init__()
        self.tables = tables
        self.col_widths = col_widths
        self.row_spacing = row_spacing
        self.width = sum(col_widths)
        self.height = 0
        
    def wrap(self, width, height):
        # Calculate heights of all tables
        max_height = 0
        table_heights = []
        
        for table in self.tables:
            w, h = table.wrap(self.col_widths[self.tables.index(table)], height)
            table_heights.append(h)
            max_height = max(max_height, h)
        
        # Set all tables to max height by adding padding
        for i, table in enumerate(self.tables):
            # Add padding to shorter tables
            padding_needed = max_height - table_heights[i]
            if padding_needed > 0:
                # Wrap table in a container with padding
                pass  # We'll handle this in draw
        
        self.height = max_height
        return self.width, self.height
    
    def draw(self):
        # Draw all tables side by side
        x = 0
        for table in self.tables:
            table.drawOn(self.canv, x, 0)
            x += self.col_widths[self.tables.index(table)]


def generate_therapy_pdf(selected_date: date) -> bytes:
    """
    Generate PDF with therapy schedule.
    
    Format:
    - A4 Landscape
    - Header: Date (top-left) and Centre name
    - Tables: Therapist tables arranged in a grid (max 6 per row)
    - Grouped by centre
    - Only populated rows (no empty time slots)
    - Tables aligned by height within each row
    
    Args:
        selected_date: Date to generate schedule for
        
    Returns:
        PDF as bytes
    """
    buffer = BytesIO()
    
    # A4 landscape: width ~297mm, height ~210mm
    page_width, page_height = landscape(A4)
    
    # Margins
    left_margin = 8 * mm
    right_margin = 8 * mm
    top_margin = 15 * mm
    bottom_margin = 8 * mm
    
    # Usable area
    usable_width = page_width - left_margin - right_margin
    usable_height = page_height - top_margin - bottom_margin
    
    # Create PDF
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=left_margin,
        rightMargin=right_margin,
        topMargin=top_margin,
        bottomMargin=bottom_margin,
    )
    
    # Fetch all therapies for this date
    therapies = Therapy.objects.filter(date=selected_date).select_related('therapist', 'child', 'therapist__centru', 'centru')
    
    # Build therapies_by_therapist map from existing therapies
    therapies_by_therapist = {}
    for therapy in therapies:
        t = therapy.therapist
        if t.id not in therapies_by_therapist:
            therapies_by_therapist[t.id] = {
                'therapist': t,
                'therapies': [],
                'has_sessions': True,
            }
        therapies_by_therapist[t.id]['therapies'].append(therapy)
    
    # Fetch ALL therapists and add those without sessions
    all_therapists = Therapist.objects.select_related('centru').order_by('last_name', 'first_name')
    for therapist in all_therapists:
        if therapist.id not in therapies_by_therapist:
            therapies_by_therapist[therapist.id] = {
                'therapist': therapist,
                'therapies': [],
                'has_sessions': False,
            }
    
    # Group by centre — use snapshotted centru from therapy, fall back to therapist.centru
    centres = {}
    for t_id, data in therapies_by_therapist.items():
        therapist = data['therapist']
        
        # Determine centre: from therapy snapshot if has sessions, else from therapist
        if data['has_sessions']:
            first_therapy = data['therapies'][0]
            centre = first_therapy.centru if first_therapy.centru_id else therapist.centru
        else:
            centre = therapist.centru
        
        if centre not in centres:
            centres[centre] = []
        centres[centre].append(data)
    
    # Generate story (content)
    story = []
    
    # Styles
    date_style = ParagraphStyle(
        'DateStyle',
        fontSize=14,
        textColor=colors.black,
        spaceAfter=3,
    )
    
    centre_style = ParagraphStyle(
        'CentreStyle',
        fontSize=12,
        textColor=colors.black,
        spaceAfter=8,
        fontName='Helvetica-Bold',
    )
    
    # For each centre (sorted alphabetically by name)
    is_first_page = True
    for centre, therapists_data in sorted(centres.items(), key=lambda x: x[0].name.lower()):
        if not is_first_page:
            story.append(PageBreak())
        is_first_page = False
        
        # Header: Date and Centre
        date_str = selected_date.strftime('%d.%m.%Y')
        story.append(Paragraph(f"<b>Data:</b> {date_str}", date_style))
        
        story.append(Paragraph(f"<b>{centre.name}</b>", centre_style))
        
        # Generate tables for this centre's therapists
        all_tables = []
        
        for therapist_data in sorted(therapists_data, key=lambda x: (x['therapist'].last_name.lower(), x['therapist'].first_name.lower())):
            therapist = therapist_data['therapist']
            therapies_list = therapist_data['therapies']
            has_sessions = therapist_data['has_sessions']
            
            # Sort therapies by start time
            therapies_list = sorted(therapies_list, key=lambda x: x.start_time)
            
            # Build therapist table
            table_data = []
            
            # Header row: therapist name (will span 2 columns)
            therapist_name = f"{therapist.last_name} {therapist.first_name}"
            table_data.append([therapist_name, ''])  # 2 columns, second is empty for spanning
            
            # If therapist has sessions: add only the populated rows
            # If therapist has NO sessions: add 4 empty time slots (8-10, 10-12, 12-14, 14-16)
            if has_sessions:
                for therapy in therapies_list:
                    start_time = therapy.start_time
                    end_time = time((start_time.hour + 2) % 24, 0)
                    interval = f"{start_time.strftime('%H:%M')}-{end_time.strftime('%H:%M')}"
                    child_name = f"{therapy.child.first_name} {therapy.child.last_name}"
                    table_data.append([interval, child_name])
            else:
                # Add 4 empty slots
                empty_slots = ['08:00', '10:00', '12:00', '14:00']
                for slot in empty_slots:
                    h = int(slot.split(':')[0])
                    end_h = h + 2
                    interval = f"{slot}-{end_h:02d}:00"
                    table_data.append([interval, ''])
            
            # Create table with 2 columns: time and child
            # Keep columns small so multiple tables fit on a row
            col_widths = [18*mm, 22*mm]  # Total: 40mm per table
            row_heights = [4*mm] * len(table_data)
            
            table = Table(
                table_data,
                colWidths=col_widths,
                rowHeights=row_heights,
            )
            
            # Style table
            table.setStyle(TableStyle([
                # Header row styling (spans 2 columns)
                ('SPAN', (0, 0), (1, 0)),  # Merge header across both columns
                ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#0066cc')),
                ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (1, 0), 'CENTER'),  # Center header text
                ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (1, 0), 8),
                ('TOPPADDING', (0, 0), (1, 0), 2),
                ('BOTTOMPADDING', (0, 0), (1, 0), 2),
                # Data rows styling
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 1), (-1, -1), 6),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f8f8')]),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cccccc')),
                ('LEFTPADDING', (0, 0), (-1, -1), 2),
                ('RIGHTPADDING', (0, 0), (-1, -1), 2),
                ('TOPPADDING', (0, 1), (-1, -1), 1),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 1),
            ]))
            
            all_tables.append(table)
        
        # Layout tables in grid: max 6 per row
        tables_per_row = 6
        row_spacing = 8 * mm
        
        # Build rows
        for row_idx in range(0, len(all_tables), tables_per_row):
            row_tables = all_tables[row_idx:row_idx + tables_per_row]
            num_in_row = len(row_tables)
            
            # Calculate width available per table column
            spacing_total = (num_in_row - 1) * 2 * mm  # 2mm space between tables
            available = usable_width - spacing_total
            col_width = available / num_in_row
            
            # Create row container
            row_table = Table(
                [row_tables],
                colWidths=[col_width] * num_in_row,
                rowHeights=None,  # Auto height
                hAlign='LEFT',
            )
            
            row_table.setStyle(TableStyle([
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 1*mm),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ]))
            
            story.append(row_table)
            story.append(Spacer(1, row_spacing))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
