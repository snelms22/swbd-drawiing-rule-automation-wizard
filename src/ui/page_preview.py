"""Draws the pages from a LayoutResult as simple rectangles.

This widget only DRAWS what the layout engine decided. It makes no layout decisions of
its own, so if the preview looks wrong the bug is in src/layout/ (or config/), not here.

The pixel sizes below are screen-only spacing for the preview, not drawing layout
numbers, so they live here rather than in config/.
"""
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from src.layout.page_fitter import LayoutResult, Page
from src.layout.settings import LayoutSettings

PADDING_PX = 20          # space around the pages
PAGE_LABEL_PX = 22       # room above each page for "Page 1 ..."
GAP_BETWEEN_PAGES_PX = 24

PAGE_FILL = QColor("white")
PAGE_BORDER = QColor("#333333")
MARGIN_LINE = QColor("#9aa5b1")
KEEPOUT_FILL = QColor("#e4e7eb")
KEEPOUT_BORDER = QColor("#7b8794")
DIVIDER_COLOR = QColor("#d64545")   # DEVIDER layer is red in AutoCAD
GROUND_COLOR = QColor("#2f9e44")    # GROUND layer is green in AutoCAD
BUS_COLOR = QColor("#b8860b")       # BUS layer is yellow in AutoCAD (darkened to show on white)
TEXT_COLOR = QColor("#1f2933")
MIN_TEXT_PX = 9                     # smallest readable font size on screen
NOTE_LINE_SPACING = 1.67            # MText line spacing, in text heights (AutoCAD default)
SECTION_FILL = QColor("#cfe3fa")
SECTION_BORDER = QColor("#2f6db5")
OVERFLOW_FILL = QColor("#f8d0cc")   # a section sticking out past the page edge
OVERFLOW_BORDER = QColor("#c0392b")
BACKGROUND = QColor("#f5f7fa")


class PagePreview(QWidget):
    def __init__(self, settings: LayoutSettings, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._result: LayoutResult | None = None

    def show_layout(self, result: LayoutResult):
        self._result = result
        self._update_height()
        self.update()  # ask Qt to repaint

    def resizeEvent(self, event):
        # Page drawings scale with the widget's width, so the needed height changes too.
        super().resizeEvent(event)
        self._update_height()

    # --- Sizing -----------------------------------------------------------------------

    def _drawing_width_units(self) -> float:
        """Width to fit on screen: the page, or more if a section overflows past it."""
        widest = self._settings.drawable_width
        if self._result:
            for page in self._result.pages:
                if page.placed_sections:
                    widest = max(widest, page.placed_sections[-1].right_divider_x)
        return widest

    def _pixels_per_unit(self) -> float:
        usable_px = max(self.width() - 2 * PADDING_PX, 100)
        return usable_px / self._drawing_width_units()

    def _page_height_px(self) -> float:
        return self._settings.drawable_height * self._pixels_per_unit()

    def _page_top_px(self, page_index: int) -> float:
        step = PAGE_LABEL_PX + self._page_height_px() + GAP_BETWEEN_PAGES_PX
        return PADDING_PX + page_index * step + PAGE_LABEL_PX

    def _update_height(self):
        page_count = len(self._result.pages) if self._result else 0
        if page_count == 0:
            self.setMinimumHeight(0)
            return
        bottom = self._page_top_px(page_count - 1) + self._page_height_px() + PADDING_PX
        self.setMinimumHeight(int(bottom))

    def _to_screen(self, x: float, y: float, page_top_px: float) -> QPointF:
        """Drawing units (y up, like AutoCAD) to screen pixels (y down, like Qt)."""
        scale = self._pixels_per_unit()
        return QPointF(
            PADDING_PX + x * scale,
            page_top_px + (self._settings.drawable_height - y) * scale,
        )

    def _rect(self, left, bottom, right, top, page_top_px) -> QRectF:
        return QRectF(
            self._to_screen(left, top, page_top_px), self._to_screen(right, bottom, page_top_px)
        )

    # --- Painting ---------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.fillRect(self.rect(), BACKGROUND)

        if not self._result or not self._result.pages:
            painter.drawText(self.rect(), Qt.AlignCenter, "No sections yet. Click \"Add section\".")
            return

        for index, page in enumerate(self._result.pages):
            self._draw_page(painter, page, self._page_top_px(index))

    def _draw_page(self, painter: QPainter, page: Page, page_top_px: float):
        s = self._settings
        W, H = s.drawable_width, s.drawable_height

        # Label
        margin_note = "relaxed margin" if page.side_margin == s.margin_relaxed else "standard margin"
        painter.setPen(QColor("#1f2933"))
        what = (f"{len(page.placed_sections)} sections, {margin_note} {page.side_margin:g}"
                if page.placed_sections else "devices")
        painter.drawText(QPointF(PADDING_PX, page_top_px - 6), f"Page {page.number}  ({what})")

        # Page outline (the drawable area)
        page_rect = self._rect(0, 0, W, H, page_top_px)
        painter.setPen(QPen(PAGE_BORDER, 1.5))
        painter.setBrush(PAGE_FILL)
        painter.drawRect(page_rect)

        # Margins (dashed)
        top_y = H - s.margin_standard
        bottom_y = s.margin_standard
        painter.setPen(QPen(MARGIN_LINE, 1, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(self._rect(page.side_margin, bottom_y, W - page.side_margin, top_y, page_top_px))

        # Title block keep-out
        keepout_left = W - s.keepout_width
        keepout_rect = self._rect(keepout_left, 0, W, s.keepout_height, page_top_px)
        painter.setPen(QPen(KEEPOUT_BORDER, 1))
        painter.setBrush(KEEPOUT_FILL)
        painter.drawRect(keepout_rect)
        painter.setPen(KEEPOUT_BORDER)
        painter.drawText(keepout_rect, Qt.AlignCenter, "Title block")

        # Section contents: the layout gives one box above the main bus and one below.
        if page.parts is not None:
            edge_of_page = W - page.side_margin
            for content in page.parts.content_boxes:
                overflowing = content.right_x > edge_of_page
                painter.setPen(QPen(OVERFLOW_BORDER if overflowing else SECTION_BORDER, 1.2))
                painter.setBrush(OVERFLOW_FILL if overflowing else SECTION_FILL)
                rect = self._rect(content.left_x, content.bottom_y, content.right_x, content.top_y,
                                  page_top_px)
                painter.drawRect(rect)
                painter.setPen(QColor("#1f2933"))
                painter.drawText(rect.adjusted(2, 2, -2, -2),
                                 Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                                 f"Section {content.section_number}")

        if page.parts is not None:
            self._draw_page_parts(painter, page, page_top_px)

    def _draw_bus(self, painter: QPainter, path, page_top_px: float):
        """Three phases along the bus centre line: A above / left, B on it, C below / right.
        Corners are not joined neatly; this is only a preview."""
        half = self._settings.main_bus.phase_spacing
        painter.setPen(QPen(BUS_COLOR, 1.2))
        for (x1, y1), (x2, y2) in zip(path, path[1:]):
            vertical = abs(x1 - x2) < 1e-9
            for offset in (-half, 0.0, half):
                if vertical:
                    a, b = (x1 + offset, y1), (x2 + offset, y2)
                else:
                    a, b = (x1, y1 - offset), (x2, y2 - offset)
                painter.drawLine(self._to_screen(*a, page_top_px), self._to_screen(*b, page_top_px))

    def _draw_main_breaker_parts(self, painter: QPainter, parts, page_top_px: float):
        """Extra bus runs, library blocks (as their outline box), and waiting-block boxes."""
        painter.setPen(QPen(BUS_COLOR, 0.8))
        for wire in parts.wires:             # device page wires: thinner than bus
            painter.drawLine(self._to_screen(*wire.start, page_top_px),
                             self._to_screen(*wire.end, page_top_px))
        painter.setPen(QPen(BUS_COLOR, 1.2))
        for line in parts.bus_lines:
            painter.drawLine(self._to_screen(*line.start, page_top_px),
                             self._to_screen(*line.end, page_top_px))
        for block in parts.blocks:
            left, bottom, right, top = block.extents
            x, y = block.position
            rect = self._rect(x + left, y + bottom, x + right, y + top, page_top_px)
            if block.block == self._settings.main_bus.junction_dot_block:
                painter.setPen(Qt.NoPen)
                painter.setBrush(BUS_COLOR)
                painter.drawEllipse(rect.adjusted(-1, -1, 1, 1))
            else:   # any other block: its outline, named by its label or state
                painter.setPen(QPen(SECTION_BORDER, 1.0))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(rect)
                self._draw_drawing_text(painter, block.label or block.visibility or block.block,
                                        x + (left + right) / 2, y + top + 0.5,
                                        page_top_px, centred=True)
        for note in parts.notes:
            self._draw_note(painter, note, page_top_px)
        for box in parts.placeholders:
            painter.setPen(QPen(MARGIN_LINE, 1, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            rect = self._rect(box.left_x, box.bottom_y, box.right_x, box.top_y, page_top_px)
            painter.drawRect(rect)
            self._draw_drawing_text(painter, box.text, (box.left_x + box.right_x) / 2,
                                    box.bottom_y + 1, page_top_px, centred=True)

    def _draw_page_parts(self, painter: QPainter, page: Page, page_top_px: float):
        """Main bus, dividers, ground bus (with its symbol and label) and section labels."""
        s = self._settings
        parts = page.parts
        for path in parts.bus_paths:
            self._draw_bus(painter, path, page_top_px)
        self._draw_main_breaker_parts(painter, parts, page_top_px)

        # Dividers: dashed, in the DEVIDER layer's colour (red).
        painter.setPen(QPen(DIVIDER_COLOR, 1.2, Qt.DashLine))
        for line in parts.dividers:
            painter.drawLine(
                self._to_screen(line.x, line.top_y, page_top_px),
                self._to_screen(line.x, line.bottom_y, page_top_px),
            )

        # Ground bus, in the GROUND layer's colour (green).
        ground = parts.ground_bus
        if ground is not None:
            g = s.ground_bus
            painter.setPen(QPen(GROUND_COLOR, 1.5))
            painter.drawLine(
                self._to_screen(ground.start_x, ground.y, page_top_px),
                self._to_screen(ground.end_x, ground.y, page_top_px),
            )
            # Ground symbol: a short stem down from the bus, then bars getting narrower.
            stem_x = ground.start_x + g.symbol_offset_x
            stem_bottom_y = ground.y - g.symbol_stem_length
            painter.drawLine(
                self._to_screen(stem_x, ground.y, page_top_px),
                self._to_screen(stem_x, stem_bottom_y, page_top_px),
            )
            for bar_index, bar_width in enumerate(g.symbol_bar_widths):
                bar_y = stem_bottom_y - bar_index * g.symbol_bar_spacing
                painter.drawLine(
                    self._to_screen(stem_x - bar_width / 2, bar_y, page_top_px),
                    self._to_screen(stem_x + bar_width / 2, bar_y, page_top_px),
                )
            self._draw_drawing_text(
                painter, g.label_text, ground.start_x + g.label_offset_x,
                ground.y + g.label_gap_above_bus, page_top_px, centred=False,
            )

        for label in parts.section_labels:
            self._draw_drawing_text(
                painter, label.text, label.center_x, label.bottom_y, page_top_px, centred=True
            )

    def _draw_note(self, painter, note, page_top_px):
        """A note's lines, stacked around its middle, running away from its x."""
        line_spacing = self._settings.text.height * NOTE_LINE_SPACING
        top_bottom_y = note.middle_y + (len(note.lines) - 2) * line_spacing / 2
        for index, line in enumerate(note.lines):
            bottom_y = top_bottom_y - index * line_spacing
            if note.align == "middle_right":
                self._draw_drawing_text(painter, line, note.x, bottom_y, page_top_px,
                                        centred=False, right_aligned=True)
            else:
                self._draw_drawing_text(painter, line, note.x, bottom_y, page_top_px, centred=False)

    def _draw_drawing_text(self, painter, text, x, bottom_y, page_top_px, centred,
                           right_aligned=False):
        """Draw text at its drawing position. At preview scale the real text height would
        be unreadably small, so the preview uses a minimum font size."""
        painter.save()   # so the font change below doesn't leak into later drawing
        font = painter.font()
        font.setPixelSize(max(int(self._settings.text.height * self._pixels_per_unit()), MIN_TEXT_PX))
        painter.setFont(font)
        painter.setPen(TEXT_COLOR)
        anchor = self._to_screen(x, bottom_y, page_top_px)
        width = painter.fontMetrics().horizontalAdvance(text)
        if centred:
            anchor = QPointF(anchor.x() - width / 2, anchor.y())
        elif right_aligned:
            anchor = QPointF(anchor.x() - width, anchor.y())
        painter.drawText(anchor, text)
        painter.restore()
