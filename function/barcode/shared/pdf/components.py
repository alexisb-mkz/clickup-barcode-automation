from reportlab.platypus import (
    HRFlowable,
    Flowable,
    Image as ReportLabImage,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    KeepTogether
)
from reportlab.lib.units import inch
import io
import qrcode
from PIL import Image as PILImage

import logging
import os
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.pdfmetrics import registerFontFamily
from reportlab.lib.fonts import _ps2tt_map, _tt2ps_map



class ClickableQRCode(Flowable):
    """
    A clickable QR code that can be embedded in PDFs
    """
    def __init__(self, url, width=1.5*inch, height=1.5*inch):
        Flowable.__init__(self)
        self.qr_image_bytes = None
        self.url = url
        self.width = width
        self.height = height
    
    @staticmethod
    def generate_barcode_bytes(url):
        """Generates a QR code for a URL and returns it as PNG bytes."""
        # Create QR code object 
        qr = qrcode.QRCode(
            version=1, # Controls size (1 is smallest)
            error_correction=qrcode.constants.ERROR_CORRECT_L, # Error correction level
            box_size=10, # Size of each box (pixel)
            border=4, # Thickness of the border
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Create an image from the QR Code instance
        img = qr.make_image(fill_color="black", back_color="white")

        # Use BytesIO to capture image data in memory
        byte_stream = io.BytesIO()
        img.save(byte_stream, format='PNG') # Save as PNG (or 'JPEG', 'SVG', etc.)

        # Get the bytes from the stream
        barcode_bytes = byte_stream.getvalue()

        return barcode_bytes
        
    def draw(self):
        """Draw the QR code with clickable link"""
        from reportlab.lib.utils import ImageReader
        
        qr_image_bytes = self.generate_barcode_bytes(self.url)
        
        # Draw the QR code image
        img_reader = ImageReader(io.BytesIO(qr_image_bytes))
        self.canv.drawImage(
            img_reader,
            0, 0,
            width=self.width,
            height=self.height,
            preserveAspectRatio=True
        )
        
        # Add clickable link overlay
        self.canv.linkURL(
            self.url,
            (0, 0, self.width, self.height),
            relative=1
        )
        
        


class ScaledImageGrid:
    """
    Builds a PDF image section that fits within a known vertical budget.

    - Screenshots (UI / chat) -> full-width, legible.
    - Photos -> 2-column grid, aspect-correct.
    - A single uniform scale factor is applied so the total height never
      exceeds `available_height_in`.
    """

    # Ideal height for a full-width screenshot when space is unlimited.
    SCREENSHOT_IDEAL_HEIGHT_IN = 4.0

    # Minimum screenshot height (below this, text becomes unreadable).
    SCREENSHOT_MIN_HEIGHT_IN = 1.5

    # Ideal row height for photos in the 2-column grid.
    PHOTO_IDEAL_ROW_HEIGHT_IN = 2.5

    # Minimum photo row height.
    PHOTO_MIN_ROW_HEIGHT_IN = 0.8

    # Overhead of the "Attached Images" sub-header rendered in build()
    # (spacer + rule + spacer + heading + spacer ~ 0.5").
    SECTION_HEADER_OVERHEAD_IN = 0.5

    # Per-image vertical padding from table cells (top + bottom).
    CELL_PADDING_IN = 12 / 72  # 12 pts ~ 0.167"

    _SCREEN_DIMS = {
        375, 390, 393, 414, 428, 430,
        750, 828, 858, 886, 1080, 1125, 1170, 1179, 1242, 1284, 1290, 1320,
        768, 810, 820, 834, 1024, 1112, 1133, 1194, 1366, 1640, 1668,
        2048, 2224, 2388, 2732,
        1280, 1366, 1440, 1536, 1600, 1680, 1920, 2048, 2560, 2880, 3456,
        360, 412, 720, 1080, 1440, 1600, 2160,
    }

    # Portrait-only screen ratios (short/long, always < 1).
    # Deliberately excludes 3/4 and 2/3 — those are indistinguishable from
    # common camera aspect ratios (4:3 and 3:2) and cause false positives.
    # Landscape images are rejected before this list is consulted.
    _SCREEN_RATIOS = [
        9 / 16,      # 0.5625 — classic smartphone / 16:9 desktop
        9 / 19.5,    # 0.4615 — iPhone X / 11 / 12 / 13 / 14 / 15
        9 / 20,      # 0.4500 — tall Android
        9 / 21,      # 0.4286 — very tall Android
        10 / 16,     # 0.6250 — some Android / 16:10 tablet
    ]

    def __init__(self, styles, layout, available_height_in=None):
        self.styles = styles
        self.layout = layout

        if available_height_in is None:
            available_height_in = (
                getattr(layout, "PAGE_HEIGHT", 11.0)
                - getattr(layout, "PAGE_TOP_MARGIN", 0.75)
                - getattr(layout, "PAGE_BOTTOM_MARGIN", 0.75)
                - 2.0
            )
        self._available_height_in = max(float(available_height_in), 1.0)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def build(self, attachment_images):
        if not attachment_images:
            return []

        content_w_pts = self._content_width_pts()
        cols          = getattr(self.layout, "IMAGE_GRID_COLS", 2)
        col_w_pts     = content_w_pts / cols - (self.CELL_PADDING_IN * inch)
        budget_in     = max(
            self._available_height_in - self.SECTION_HEADER_OVERHEAD_IN,
            1.0,
        )

        # Phase 1: classify
        items = []
        for idx, image_bytes in enumerate(attachment_images, 1):
            try:
                items.append(self._classify(image_bytes, idx))
            except Exception as e:
                logging.error(f"Error loading image {idx}: {e}")
                items.append(self._error_item(idx))

        # Phase 2: natural heights
        for item in items:
            if not item["is_error"]:
                item["natural_h_in"] = self._natural_height_in(
                    item, content_w_pts, col_w_pts
                )

        # Phase 3: scale factor
        scale = self._compute_scale(items, budget_in, cols)

        # Phase 4: build ReportLab elements
        for item in items:
            if not item["is_error"]:
                self._apply_scale(item, scale, content_w_pts, col_w_pts)

        # Phase 5: assemble flowables
        elements = []
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(HRFlowable(width="100%", thickness=1, color="#CCCCCC"))
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("Attached Images", self.styles.section_header))
        elements.append(Spacer(1, 0.08 * inch))

        elements.extend(self._render_unified_grid(items, cols, content_w_pts))

        return elements

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def _classify(self, image_bytes, idx):
        pil_img       = PILImage.open(io.BytesIO(image_bytes))
        is_screenshot = self._is_screenshot(pil_img)
        img_w, img_h  = pil_img.size
        return {
            "idx":           idx,
            "image_bytes":   image_bytes,
            "pil_img":       pil_img,
            "is_screenshot": is_screenshot,
            "spans_row":     False,  # everything goes in the same grid
            "full_width":    False,
            "is_error":      False,
            "natural_h_in":  0.0,
            "element":       None,
        }

    def _is_screenshot(self, pil_img):
        img_w, img_h = pil_img.size
        pixels = img_w * img_h

        # High-res images are camera photos
        if pixels > 12_000_000:
            return False

        # Camera Exif SubIFD present → camera photo
        try:
            if 0x8769 in pil_img.getexif():
                return False
        except Exception:
            pass

        # Landscape images are almost never screenshots (phones/tablets shoot
        # screenshots in portrait; desktop screenshots are handled by the
        # 16:9 ratio below).  Reject landscape to avoid misclassifying
        # landscape camera photos (4:3, 3:2, 16:9) as screenshots.
        is_landscape = img_w > img_h
        if is_landscape:
            # Only allow landscape if it's a known desktop screenshot size
            # with a strict 16:9 ratio match
            short, long_ = img_h, img_w
            ratio = short / long_ if long_ else 0
            if abs(ratio - 9 / 16) > 0.02:
                return False
            # Fall through for 16:9 landscape desktop screenshots

        short, long_ = min(img_w, img_h), max(img_w, img_h)
        if long_ == 0:
            return False
        ratio = short / long_

        deltas    = [abs(ratio - r) for r in self._SCREEN_RATIOS]
        min_delta = min(deltas)

        if (img_w in self._SCREEN_DIMS or img_h in self._SCREEN_DIMS) and min_delta < 0.08:
            return True
        if min_delta < 0.015:
            return True
        # Heuristic: small portrait image + no Exif + plausible phone ratio
        if not is_landscape and pixels < 4_000_000 and ratio > 0.35 and min_delta < 0.12:
            return True

        return False

    # ------------------------------------------------------------------
    # Natural heights
    # ------------------------------------------------------------------

    def _natural_height_in(self, item, content_w_pts, col_w_pts):
        img_w, img_h = item["pil_img"].size
        aspect = img_h / img_w
        # All images are in column-width cells — screenshots just get a
        # taller ideal height so they render more legibly than photos.
        ideal = (self.SCREENSHOT_IDEAL_HEIGHT_IN if item["is_screenshot"]
                 else self.PHOTO_IDEAL_ROW_HEIGHT_IN)
        return min((col_w_pts / inch) * aspect, ideal)

    # ------------------------------------------------------------------
    # Scale factor
    # ------------------------------------------------------------------

    def _compute_scale(self, items, budget_in, cols):
        """
        Compute a scale in (0, 1] so all images fit within budget_in.

        Models the unified grid layout:
        - Screenshots occupy a full row (their natural_h_in is their height
          at content width, so they count as one row each).
        - Photos are packed cols-per-row; each row height = tallest photo.
        """
        pad = self.CELL_PADDING_IN
        total = 0.0
        photo_buffer = []

        def flush_photos():
            nonlocal total
            if not photo_buffer:
                return
            num_rows = (len(photo_buffer) + cols - 1) // cols
            for r in range(num_rows):
                row = photo_buffer[r * cols : (r + 1) * cols]
                total += max(i["natural_h_in"] for i in row) + pad
            photo_buffer.clear()

        for item in items:
            if item.get("is_error"):
                continue
            if item["spans_row"]:
                flush_photos()
                total += item["natural_h_in"] + pad
            else:
                photo_buffer.append(item)

        flush_photos()

        if total <= 0 or total <= budget_in:
            return 1.0

        return (budget_in * 0.97) / total

    # ------------------------------------------------------------------
    # Apply scale
    # ------------------------------------------------------------------

    def _apply_scale(self, item, scale, content_w_pts, col_w_pts):
        img_w, img_h = item["pil_img"].size
        aspect = img_h / img_w
        min_h = (self.SCREENSHOT_MIN_HEIGHT_IN if item["is_screenshot"]
                else self.PHOTO_MIN_ROW_HEIGHT_IN)

        h_in  = max(item["natural_h_in"] * scale, min_h)
        h_pts = h_in * inch
        w_pts = h_pts / aspect
        if w_pts > col_w_pts:
            w_pts = col_w_pts
            h_pts = w_pts * aspect

        img_el  = ReportLabImage(io.BytesIO(item["image_bytes"]),
                                width=w_pts, height=h_pts)
        caption = Paragraph(f"Image {item['idx']}", self.styles.caption)

        # Nested Table instead of KeepTogether — works correctly inside outer Table cells
        cell_table = Table(
            [[img_el], [caption]],
            colWidths=[col_w_pts]
        )
        cell_table.setStyle(TableStyle([
            ('ALIGN',         (0, 0), (-1, -1), 'CENTER'),
            ('LEFTPADDING',   (0, 0), (-1, -1), 0),
            ('RIGHTPADDING',  (0, 0), (-1, -1), 0),
            ('TOPPADDING',    (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ]))

        item["element"]       = cell_table
        item["display_w_pts"] = w_pts
        item["display_h_pts"] = h_pts

    # ------------------------------------------------------------------
    # Rendering helpers
    # ------------------------------------------------------------------

    def _content_width_pts(self):
        return (
            self.layout.PAGE_WIDTH
            - self.layout.PAGE_LEFT_MARGIN
            - self.layout.PAGE_RIGHT_MARGIN
        ) * inch

    def _render_unified_grid(self, items, cols, content_w_pts):
        """
        Build a single ReportLab Table containing all images.

        Screenshots occupy an entire row (spanning all columns) so they
        render at a readable size. Photos fill individual cells in a
        cols-wide grid. This keeps everything in one table so ReportLab
        can paginate it correctly rather than splitting across separate
        tables.

        Layout algorithm:
        - Walk items in order.
        - If the current item is a screenshot: flush any partial photo row
          with empty padding cells, then emit a full-width row for the
          screenshot.
        - If the current item is a photo: accumulate into the current row;
          emit the row when it's full.
        - At the end, flush any remaining partial photo row.
        """
        if not items:
            return []

        col_w = content_w_pts / cols
        table_rows   = []   # list of row data (each row = list of `cols` cells)
        span_cmds    = []   # SPAN style commands collected as we go
        photo_buffer = []   # accumulate photos until a row is full

        def flush_photo_buffer():
            """Emit the current partial/full photo row, padding if needed."""
            if not photo_buffer:
                return
            row = []
            for item in photo_buffer:
                el = item.get("element")
                if el is None:
                    el = [Paragraph(f"Error rendering image {item['idx']}", self.styles.error)]
                row.append(el)
            while len(row) < cols:
                row.append("")
            table_rows.append(row)
            photo_buffer.clear()

        for item in items:
            if item["spans_row"]:
                # Flush any buffered photos first
                flush_photo_buffer()

                # Screenshot row: first cell holds the image, rest are empty
                # and will be merged via SPAN
                row_idx = len(table_rows)
                row = [item["element"]] + [""] * (cols - 1)
                table_rows.append(row)

                if cols > 1:
                    # SPAN from (col=0, row=row_idx) to (col=cols-1, row=row_idx)
                    span_cmds.append(("SPAN", (0, row_idx), (cols - 1, row_idx)))
            else:
                photo_buffer.append(item)
                if len(photo_buffer) == cols:
                    flush_photo_buffer()

        flush_photo_buffer()  # trailing partial photo row

        if not table_rows:
            return []

        table = Table(table_rows, colWidths=[col_w] * cols)

        style_cmds = [
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING",   (0, 0), (-1, -1), 3),
            ("RIGHTPADDING",  (0, 0), (-1, -1), 3),
        ] + span_cmds

        table.setStyle(TableStyle(style_cmds))
        return [table]

    # Keep _render_full_width and _render_grid for backward compatibility
    # but they are no longer called by build().
    def _render_full_width(self, item, content_w_pts):
        table = Table([[item["element"]]], colWidths=[content_w_pts])
        table.setStyle(TableStyle([
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [table, Spacer(1, 0.08 * inch)]

    def _render_grid(self, items, cols, content_w_pts):
        if not items:
            return []
        col_w = content_w_pts / cols
        rows, row = [], []
        for item in items:
            row.append(item["element"])
            if len(row) == cols:
                rows.append(row)
                row = []
        if row:
            while len(row) < cols:
                row.append("")
            rows.append(row)
        table = Table(rows, colWidths=[col_w] * cols)
        table.setStyle(TableStyle([
            ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
            ("VALIGN",        (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING",    (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        return [table]

    def _error_item(self, idx):
        return {
            "idx":           idx,
            "is_error":      True,
            "full_width":    False,
            "is_screenshot": False,
            "natural_h_in":  0.3,
            "element":       Paragraph(f"Error loading image {idx}", self.styles.error),
        }




# Candidate fonts tried in priority order.
# CID entries (no path) are built into ReportLab and work everywhere — no
# file installation required. TTF paths are tried as fallbacks for local
# dev environments that have them.
_CANDIDATES = [
    # Built-in ReportLab CID fonts — always available, no files needed
    {"name": "STSong-Light", "type": "cid"},
    {"name": "MSung-Light",  "type": "cid"},
    # TTF fallbacks for local dev
    {"name": "WQYZenHei", "type": "ttf",
     "path": "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "subfont": 0},
    {"name": "IPAGothic", "type": "ttf",
     "path": "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf"},
]

class CJKFontManager:
    """
    Registers a CJK-capable font with ReportLab and exposes it under a
    stable family name so that bold/italic tags and ParagraphStyles work
    without errors on both Azure and local dev environments.

    How to use
    ----------
    Instantiate once at module level and call register() at startup:

        cjk = CJKFontManager()
        cjk.register()

    Then reference cjk.font_name in every ParagraphStyle:

        from reportlab.lib.styles import ParagraphStyle

        title_style = ParagraphStyle(
            'Title',
            fontName=cjk.font_name,   # <-- use this everywhere
            fontSize=24,
            spaceAfter=6,
        )

    The font covers Latin characters (English renders fine) and all common
    CJK unified ideographs. Bold tags (<b>...</b>) and bold ParagraphStyles
    resolve correctly because the family is registered in all of ReportLab's
    internal lookup tables.

    If no CJK font can be found the manager falls back to Helvetica, so the
    PDF still generates — Latin text looks normal and CJK characters show
    as boxes rather than crashing.
    """

    FAMILY_NAME = "CJKFont"

    def __init__(self):
        self._registered = False
        self._resolved_name = None

    @property
    def font_name(self) -> str:
        """Pass this to ParagraphStyle(fontName=...) and nowhere else."""
        if not self._registered:
            raise RuntimeError("Call register() before accessing font_name.")
        return self.FAMILY_NAME

    def register(self) -> bool:
        """
        Try each candidate in order, register the first one that works.
        Returns True if a real CJK font was found, False if falling back
        to Helvetica.
        """
        if self._registered:
            return self._resolved_name != "Helvetica"

        for candidate in _CANDIDATES:
            try:
                if candidate["type"] == "cid":
                    ok = self._register_cid(candidate["name"])
                else:
                    ok = self._register_ttf(
                        candidate["name"],
                        candidate["path"],
                        candidate.get("subfont"),
                    )
                if ok:
                    self._resolved_name = candidate["name"]
                    logging.info(
                        f"CJKFontManager: using '{candidate['name']}' "
                        f"as '{self.FAMILY_NAME}'"
                    )
                    self._registered = True
                    return True
            except Exception as e:
                logging.debug(
                    f"CJKFontManager: skipping {candidate['name']}: {e}"
                )

        logging.warning(
            "CJKFontManager: no CJK font available, falling back to Helvetica. "
            "Chinese/Japanese/Korean text will not render correctly."
        )
        self._register_fallback()
        self._resolved_name = "Helvetica"
        self._registered = True
        return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _wire_family(self, normal: str, bold: str):
        """
        Register the font family under FAMILY_NAME in all three of
        ReportLab's internal lookup structures:

          - pdfmetrics font family  (registerFontFamily)
          - _tt2ps_map              (family+bold+italic -> psname)
          - _ps2tt_map              (psname -> family+bold+italic)

        ReportLab's Paragraph parser calls ps2tt(style.fontName) which
        looks up _ps2tt_map. Without injecting the family name there
        directly, any non-Helvetica/Times/Courier fontName raises
        "Can't map determine family/bold/italic".
        """
        family = self.FAMILY_NAME.lower()

        registerFontFamily(
            self.FAMILY_NAME,
            normal=normal,
            bold=bold,
            italic=normal,
            boldItalic=bold,
        )

        # _tt2ps_map: (family, bold_flag, italic_flag) -> psname
        _tt2ps_map[(family, 0, 0)] = normal
        _tt2ps_map[(family, 1, 0)] = bold
        _tt2ps_map[(family, 0, 1)] = normal
        _tt2ps_map[(family, 1, 1)] = bold

        # _ps2tt_map: psname -> (family, bold_flag, italic_flag)
        # This is what ps2tt() actually queries.
        _ps2tt_map[family] = (family, 0, 0)

    def _register_cid(self, font_name: str) -> bool:
        from reportlab.pdfbase.cidfonts import UnicodeCIDFont
        pdfmetrics.registerFont(UnicodeCIDFont(font_name))
        # CID fonts have no separate bold file — map bold to same font
        self._wire_family(normal=font_name, bold=font_name)
        return True

    def _register_ttf(self, alias: str, path: str, subfont_index=None) -> bool:
        from reportlab.pdfbase.ttfonts import TTFont
        if not os.path.exists(path):
            return False
        kwargs = {"subfontIndex": subfont_index} if subfont_index is not None else {}
        pdfmetrics.registerFont(TTFont(alias, path, **kwargs))
        bold_alias = f"{alias}-Bold"
        pdfmetrics.registerFont(TTFont(bold_alias, path, **kwargs))
        self._wire_family(normal=alias, bold=bold_alias)
        return True

    def _register_fallback(self):
        family = self.FAMILY_NAME.lower()
        registerFontFamily(
            self.FAMILY_NAME,
            normal="Helvetica",
            bold="Helvetica-Bold",
            italic="Helvetica-Oblique",
            boldItalic="Helvetica-BoldOblique",
        )
        _tt2ps_map[(family, 0, 0)] = "Helvetica"
        _tt2ps_map[(family, 1, 0)] = "Helvetica-Bold"
        _tt2ps_map[(family, 0, 1)] = "Helvetica-Oblique"
        _tt2ps_map[(family, 1, 1)] = "Helvetica-BoldOblique"
        _ps2tt_map[family] = (family, 0, 0)




