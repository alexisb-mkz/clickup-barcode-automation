from datetime import datetime
from zoneinfo import ZoneInfo
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
import io
import logging
from shared.utils.helpers import translate_text, parse_quill_delta

from shared.pdf.components import ScaledImageGrid

class MaintenanceRequestTemplate:
    """Template for maintenance request PDFs"""
    
    def __init__(self, styles, layout):
        self.styles = styles
        self.layout = layout
    
    @staticmethod
    def normalize_address(text):
    # Map fullwidth ASCII variants (！ to ～, Unicode block FF01-FF5E)
        # back to their ASCII equivalents
        result = []
        for ch in text:
            cp = ord(ch)
            if 0xFF01 <= cp <= 0xFF5E:
                result.append(chr(cp - 0xFEE0))
            elif ch == '\u3000':
                result.append(' ')
            elif ch == '\u3002':
                result.append('. ')
            elif ch == '\u300C' or ch == '\u300D':
                result.append('"' if ch == '\u300C' else '"')
            else:
                result.append(ch)
        return ''.join(result)
        
    def build_header(self, property_address, unit_name, start_date, start_buffer, qr_code, translate_fn=None):
        """Build the header section with property info and QR code"""
        elements = []
        
        t = translate_fn if translate_fn else (lambda x: x)
        
        # Current date/time
        est_tz = ZoneInfo("US/Eastern")
        current_datetime = datetime.now(est_tz).strftime('%B %d, %Y at %I:%M %p')
        elements.append(Paragraph(t(f"Sent on {current_datetime}"), self.styles.date))
        elements.append(Spacer(1, 0.05 * inch))
        
        sanitized_address = self.normalize_address(t(property_address))
        
        addr_len = len(sanitized_address)
        if addr_len <= 35:
            title_font_size = self.styles.title.fontSize
        elif addr_len <= 55:
            title_font_size = max(self.styles.title.fontSize - 3, 11)
        else:
            title_font_size = max(self.styles.title.fontSize - 5, 9)

        from reportlab.lib.styles import ParagraphStyle
        address_style = ParagraphStyle(
            "address_header",
            parent=self.styles.title,
            fontSize=title_font_size,
            leading=title_font_size * 1.25,
            spaceAfter=2,
        )
        
        start_date_str = t("Please set an expected arrival date and time range by scanning the QR code")
        
        if start_date:
            timestamp_s = float(start_date) / 1000.0
            est_tz = ZoneInfo("US/Eastern")
            start_dt = datetime.fromtimestamp(timestamp_s, tz=est_tz)
            end_dt   = datetime.fromtimestamp(timestamp_s + start_buffer * 60 * 60, tz=est_tz)
            start_date_fmt = start_dt.strftime('%B %d, %Y at %I:%M %p')
            w_buffer_fmt   = end_dt.strftime('%I:%M %p')
            start_date_str = t(
                f"Expected arrival time range: {start_date_fmt} - {w_buffer_fmt}. "
                "Please scan the QR code to make an update if this changes."
            )
            logging.info(f"Parsed start_date: {start_date_fmt}, buffer: {start_buffer}, start_date_str: {start_date_str}")

        left_content = Table(
            [
                [Paragraph(sanitized_address, address_style)],
                [Spacer(1, 0.04 * inch)],
                [Paragraph(f"<b>{start_date_str}</b>", self.styles.subtitle)],
            ],
            colWidths=[self.layout.HEADER_PROPERTY_WIDTH * inch]
        )
        left_content.setStyle(TableStyle([
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
            ('VALIGN',        (0, 0), (-1, -1), 'TOP'),
        ]))

        header_data = [[left_content, qr_code]]
        header_table = Table(
            header_data,
            colWidths=[self.layout.HEADER_PROPERTY_WIDTH * inch,
                    self.layout.HEADER_QR_WIDTH * inch]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN',  (1, 0), (1, 0),   'RIGHT'),
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 0.05 * inch))
        return elements
    
    def build_qr_instructions(self, completion_url):
        """Build QR code scanning instructions"""
        elements = []
        elements.append(Paragraph("<b>Scan QR code to mark complete</b>", 
                                 self.styles.centered))
        elements.append(Paragraph(
            f'<u><a href="{completion_url}" color="blue">Or click here</a></u>',
            self.styles.link
        ))
        return elements
    
    def build_section_divider(self):
        """Build a section divider"""
        elements = []
        elements.append(Spacer(1, 0.08*inch))
        elements.append(HRFlowable(width="100%", thickness=1, color='#CCCCCC'))
        elements.append(Spacer(1, 0.1*inch))
        return elements
    
    def build_action_item_elements(self, value_richtext, translate_fn=None):
        segments = parse_quill_delta(value_richtext)
        elements = []
        
        t = translate_fn if translate_fn else (lambda x: x)
        
        for i, seg in enumerate(segments):
            text = t(seg["text"])
            
            if seg["type"] == "bullet":
                elements.append(Paragraph(f"• {text}", self.styles.body))
            elif seg["type"] == "ordered":
                elements.append(Paragraph(f"{i + 1}. {text}", self.styles.body))
            else:
                elements.append(Paragraph(text, self.styles.body))
        
        return elements
    
    def build_issue_section(self, issue_description, action_items, translate_fn=None):
        """Build the issue description section"""
        elements = []
        
        t = translate_fn if translate_fn else (lambda x: x)
        
        elements.append(Paragraph("Issue Description", self.styles.section_header))
        elements.append(Paragraph(t(issue_description), self.styles.body))
        if action_items:
            elements.append(Spacer(1, 0.1 * inch))
            elements.append(Paragraph("Action Items", self.styles.section_header))
            elements.extend(action_items)  # already Paragraphs
            logging.info(f"Added action items to PDF: {action_items}")
        return elements
    
    def build_image_grid(self, attachment_images, usable):
        """Build image attachment grid"""
        
        grid = ScaledImageGrid(self.styles, self.layout, available_height_in=usable)
        return grid.build(attachment_images)
        # if not attachment_images or len(attachment_images) == 0:
        #     return []
        
        # elements = []
        # elements.append(Spacer(1, 0.1*inch))
        # elements.append(HRFlowable(width="100%", thickness=1, color='#CCCCCC'))
        # elements.append(Spacer(1, 0.1*inch))
        # elements.append(Paragraph("Attached Images", self.styles.section_header))
        # elements.append(Spacer(1, 0.08*inch))
        
        # # Build image grid
        # from PIL import Image as PILImage
        # from reportlab.platypus import Image as ReportLabImage
        
        # image_data = []
        # current_row = []
        
        # for idx, image_bytes in enumerate(attachment_images, 1):
        #     try:
        #         img_element = self._create_image_element(image_bytes, idx)
        #         current_row.append(img_element)
                
        #         # If row is full or last image, add to image_data
        #         if len(current_row) == self.layout.IMAGE_GRID_COLS or idx == len(attachment_images):
        #             while len(current_row) < self.layout.IMAGE_GRID_COLS:
        #                 current_row.append('')
        #             image_data.append(current_row)
        #             current_row = []
                    
        #     except Exception as e:
        #         logging.error(f"Error loading image {idx}: {str(e)}")
        #         error_element = self._create_error_element(idx)
        #         current_row.append(error_element)
                
        #         if len(current_row) == self.layout.IMAGE_GRID_COLS or idx == len(attachment_images):
        #             while len(current_row) < self.layout.IMAGE_GRID_COLS:
        #                 current_row.append('')
        #             image_data.append(current_row)
        #             current_row = []
        
        # # Create table for image grid
        # if image_data:
        #     img_table = Table(
        #         image_data, 
        #         colWidths=[self.layout.IMAGE_COL_WIDTH*inch] * self.layout.IMAGE_GRID_COLS
        #     )
        #     img_table.setStyle(TableStyle([
        #         ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        #         ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        #         ('TOPPADDING', (0, 0), (-1, -1), 6),
        #         ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        #     ]))
        #     elements.append(img_table)
        
        # return elements
    
    def _create_image_element(self, image_bytes, idx):
        """Create a single image element with caption"""
        from PIL import Image as PILImage
        from reportlab.platypus import Image as ReportLabImage
        
        # Get dimensions
        pil_img = PILImage.open(io.BytesIO(image_bytes))
        img_width, img_height = pil_img.size
        aspect_ratio = img_height / img_width
        
        # Calculate display dimensions
        max_width = self.layout.IMAGE_MAX_WIDTH * inch
        max_height = self.layout.IMAGE_MAX_HEIGHT * inch
        
        display_width = max_width
        display_height = display_width * aspect_ratio
        
        if display_height > max_height:
            display_height = max_height
            display_width = display_height / aspect_ratio
        
        # Create image
        img_buffer = io.BytesIO(image_bytes)
        img = ReportLabImage(img_buffer, width=display_width, height=display_height)
        
        # Create container with caption
        return [img, Paragraph(f"Image {idx}", self.styles.caption)]
    
    def _create_error_element(self, idx):
        """Create an error message element"""
        return Paragraph(f"Error loading image {idx}", self.styles.error)