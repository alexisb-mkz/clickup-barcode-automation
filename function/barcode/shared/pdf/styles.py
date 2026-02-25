import logging
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from shared.pdf.components import CJKFontManager

_cjk = CJKFontManager()
_cjk.register()

class PDFStyles:
    """Centralized PDF styling configuration"""
    
    CJK_FONT = 'WQYZenHei'
    CJK_FONT_PATH = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
    
    def __init__(self):
        
        self.base_styles = getSampleStyleSheet()
        self.fontName = _cjk.font_name  # 'CJKFont'
        
        
    def _register_fonts(self):
        """Register CJK fallback font for Chinese/Japanese/Korean text."""
        try:
            pdfmetrics.registerFont(
                TTFont(self.CJK_FONT, self.CJK_FONT_PATH, subfontIndex=0)
            )
        except Exception as e:
            logging.warning(f'Could not register CJK font: {e}')
        
    @property
    def title(self):
        return ParagraphStyle('CustomTitle',
            fontSize=20,        # was 24
            spaceAfter=4,       # was 6
            textColor='#333333',
            fontName=self.fontName)

    @property
    def subtitle(self):
        return ParagraphStyle('CustomSubtitle', parent=self.base_styles['Heading2'],
            fontSize=14,        # was 16
            spaceAfter=6,       # was 10
            textColor='#666666',
            fontName=self.fontName)

    @property
    def section_header(self):
        return ParagraphStyle('SectionHeader', parent=self.base_styles['Heading2'],
            fontSize=12,        # was 14
            spaceAfter=6,       # was 10
            textColor='#444444',
            fontName=self.fontName)

    @property
    def body(self):
        return ParagraphStyle('CustomBody', parent=self.base_styles['BodyText'],
            fontSize=11,        # was 12
            spaceAfter=10,      # was 20
            leading=14,         # was 16
            fontName=self.fontName)
    
    @property
    def centered(self):
        return ParagraphStyle(
            'Centered',
            parent=self.base_styles['BodyText'],
            fontSize=10,
            alignment=TA_CENTER,
            spaceAfter=8,
            fontName=self.fontName
        )
    
    @property
    def link(self):
        return ParagraphStyle(
            'LinkStyle',
            parent=self.base_styles['BodyText'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor='#0066CC',
            spaceAfter=12,
            fontName=self.fontName
        )
    
    @property
    def date(self):
        return ParagraphStyle(
            'DateStyle',
            parent=self.base_styles['Normal'],
            fontSize=10,
            alignment=2,  # RIGHT
            textColor='#666666',
            spaceAfter=12,
            fontName=self.fontName
        )
    
    @property
    def caption(self):
        return ParagraphStyle(
            'Caption',
            parent=self.base_styles['BodyText'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor='#666666',
            fontName=self.fontName)
    
    @property
    def error(self):
        return ParagraphStyle(
            'Error',
            parent=self.base_styles['BodyText'],
            fontSize=9,
            alignment=TA_CENTER,
            textColor='#CC0000',
            fontName=self.fontName
            
        )

# Layout constants
class PDFLayout:
    """PDF layout configuration"""
    PAGE_TOP_MARGIN = 0.5       
    PAGE_BOTTOM_MARGIN = 0.5   
    PAGE_LEFT_MARGIN = 0.75    
    PAGE_RIGHT_MARGIN = 0.75    
    
    PAGE_WIDTH = 8.5
    PAGE_HEIGHT = 11

    QR_CODE_SIZE = 1.0         
    HEADER_PROPERTY_WIDTH = 5.25  
    HEADER_QR_WIDTH = 1.25     

    IMAGE_MAX_WIDTH = 2.75     
    IMAGE_MAX_HEIGHT = 1.75     
    IMAGE_GRID_COLS = 2
    IMAGE_COL_WIDTH = 3.0     
    
    HEADER_HEIGHT_IN = (
      0.3   # date paragraph
    + 0.3   # address/unit paragraph
    + 0.1   # spacer after header table
    + 0.02  # divider
    + 0.1   # spacer
    + 0.3   # "Issue Description" heading
    + 0.25  # issue text (single line; add more for wrapping)
    + 0.1   # spacer after issue section
  )