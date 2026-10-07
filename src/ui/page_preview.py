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
DIVIDER_LINE = QColor("#52606d")
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
        painter.drawText(
            QPointF(PADDING_PX, page_top_px - 6),
            f"Page {page.number}  ({len(page.placed_sections)} sections, {margin_note} "
            f"{page.side_margin:g})",
        )

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

        # Sections (component area)
        for placed in page.placed_sections:
            overflowing = placed.right_divider_x > W - page.side_margin
            painter.setPen(QPen(OVERFLOW_BORDER if overflowing else SECTION_BORDER, 1.2))
            painter.setBrush(OVERFLOW_FILL if overflowing else SECTION_FILL)
            box = self._rect(
                placed.component_left_x, placed.component_bottom_y,
                placed.component_right_x, placed.component_top_y, page_top_px,
            )
            painter.drawRect(box)
            painter.setPen(QColor("#1f2933"))
            painter.drawText(box.adjusted(2, 2, -2, -2), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                             placed.section.name)

        # Dividing lines. How tall they really are is still an open item, so the preview
        # draws them between the top and bottom margins, stopping at the title block.
        painter.setPen(QPen(DIVIDER_LINE, 1.5))
        for x in page.divider_xs:
            line_bottom = s.keepout_height if x > keepout_left else bottom_y
            painter.drawLine(
                self._to_screen(x, top_y, page_top_px), self._to_screen(x, line_bottom, page_top_px)
            )
