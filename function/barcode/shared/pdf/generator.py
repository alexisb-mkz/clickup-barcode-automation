import io
from pydoc import doc
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate

from shared.utils.helpers import translate_text
from .styles import PDFStyles, PDFLayout
from .templates import MaintenanceRequestTemplate
from .components import ClickableQRCode

def measure_elements_height(elements, available_width_pts, available_height_pts=10_000):
    """
    Return the total rendered height (pts) of a list of ReportLab flowables
    without building a full PDF document.

    Note: some flowables cache internal state after wrap(). If you see layout
    oddities, build separate element lists for the measurement pass and the
    real build pass.
    """
    total = 0.0
    for el in elements:
        try:
            _, h = el.wrap(available_width_pts, available_height_pts - total)
            total += h
        except Exception:
            pass
    return total



class MaintenancePDFGenerator:
    """Main PDF generator for maintenance requests"""
    
    def __init__(self, translate=False):
        self.styles = PDFStyles()
        self.layout = PDFLayout()
        self.template = MaintenanceRequestTemplate(self.styles, self.layout)
        self.translate = translate
    
    def generate(self, property_address, unit_name, start_date, start_buffer, issue_description, action_items,
                 completion_url, attachment_images=None):
        """
        Generate a PDF with formatted maintenance request information
        
        Args:
            property_address: str - The property address
            unit_name: str - Unit number or name
            issue_description: str - Description of the problem
            completion_url: str - URL for the clickable QR code
            attachment_images: list of bytes - Optional list of image bytes
        
        Returns:
            bytes - PDF file content as bytes
        """
        buffer = io.BytesIO()
        
        doc = SimpleDocTemplate(
            buffer, 
            pagesize=letter,
            topMargin=self.layout.PAGE_TOP_MARGIN*inch,
            bottomMargin=self.layout.PAGE_BOTTOM_MARGIN*inch,
            leftMargin=self.layout.PAGE_LEFT_MARGIN*inch,
            rightMargin=self.layout.PAGE_RIGHT_MARGIN*inch
        )
        
        content_w_pts = (
            self.layout.PAGE_WIDTH
            - self.layout.PAGE_LEFT_MARGIN
            - self.layout.PAGE_RIGHT_MARGIN
        ) * inch
        
        elements = []
        
        
        # Create QR code
        qr_code = ClickableQRCode(
            completion_url,
            width=self.layout.QR_CODE_SIZE*inch,
            height=self.layout.QR_CODE_SIZE*inch
        )
        
        translate_fn = translate_text if self.translate else None
        
        header_els = self.template.build_header(
            property_address, unit_name, start_date, start_buffer, qr_code,
            translate_fn=translate_fn
        )
        
        divider_els = self.template.build_section_divider()
        
        action_item_elements = self.template.build_action_item_elements(
            action_items,
            translate_fn=translate_fn
        )
        issue_els = self.template.build_issue_section(
            issue_description, 
            action_item_elements, 
            translate_fn=translate_fn
        )
        
        
        header_height_pts = measure_elements_height(
            header_els + divider_els + issue_els,
            content_w_pts,
        )
        
        page_h_pts = letter[1]
        usable_pts = (
            page_h_pts
            - self.layout.PAGE_TOP_MARGIN  * inch
            - self.layout.PAGE_BOTTOM_MARGIN * inch
            - header_height_pts
        )
        
        grid_el = self.template.build_image_grid(attachment_images, usable_pts / inch)
        
        elements = header_els + divider_els + issue_els + grid_el
        doc.build(elements)
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes