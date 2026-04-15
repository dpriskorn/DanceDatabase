import logging
import re
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


class PriceMismatchError(Exception):
    """Raised when prices from sidebar and main text don't match."""

    pass


class PriceExtractor:
    def __init__(self, html: str):
        self.original_html = html
        self.sidebar_text = self._extract_sidebar(html)
        self.main_text = self._extract_main_text(html)
        self.price_normal: Optional[int] = None
        self.price_reduced: Optional[int] = None

    def _extract_sidebar(self, html: str) -> str:
        """Extract the sidebar data area from HTML if present."""
        if "<" not in html:
            return ""

        soup = BeautifulSoup(html, "lxml")

        sidebar = soup.select_one(".cwColumnNarrow.cwDataArea")
        if sidebar:
            logger.debug("Extracted sidebar area for price extraction")
            return sidebar.get_text(separator=" ", strip=True)

        data_area = soup.select_one(".cwDataArea")
        if data_area:
            logger.debug("Extracted data area for price extraction")
            return data_area.get_text(separator=" ", strip=True)

        return ""

    def _extract_main_text(self, html: str) -> str:
        """Extract text from main form content (.cwFormCenter) or body."""
        if "<" not in html:
            return html

        soup = BeautifulSoup(html, "lxml")

        form_center = soup.select_one(".cwFormCenter")
        if form_center:
            logger.debug("Extracted main form center for price extraction")
            return form_center.get_text(separator=" ", strip=True)

        form_center = soup.select_one(".cwColumnWide")
        if form_center:
            logger.debug("Extracted main column wide for price extraction")
            return form_center.get_text(separator=" ", strip=True)

        body = soup.select_one("body")
        if body:
            return body.get_text(separator=" ", strip=True)

        return ""

    def extract(self) -> tuple[Optional[int], Optional[int]]:
        """Try all patterns in order of preference. Returns (normal, reduced)."""
        sidebar_normal, sidebar_reduced = self._extract_price_from_text(self.sidebar_text)
        main_normal, main_reduced = self._extract_price_from_text(self.main_text)

        if sidebar_normal is not None and main_normal is not None:
            if sidebar_normal != main_normal:
                raise PriceMismatchError(f"Price mismatch: sidebar={sidebar_normal}, main={main_normal}")

        if sidebar_normal is not None or main_normal is not None:
            self.price_normal = sidebar_normal or main_normal
        else:
            raise PriceMismatchError(f"No price found in text: {self.original_html[:100]}...")

        if sidebar_reduced is not None and main_reduced is not None:
            if sidebar_reduced != main_reduced:
                raise PriceMismatchError(f"Reduced price mismatch: sidebar={sidebar_reduced}, main={main_reduced}")

        self.price_reduced = sidebar_reduced or main_reduced

        return (self.price_normal, self.price_reduced)

    def _extract_price_from_text(self, text: str) -> tuple[Optional[int], Optional[int]]:
        """Extract (normal_price, reduced_price) from given text."""
        if not text:
            return (None, None)

        normal = None
        reduced = None

        normal, reduced = self._try_gratis(text)
        if normal is not None:
            return (normal, reduced)

        normal, reduced = self._try_kostar_with_reduced(text)
        if normal is not None:
            return (normal, reduced)

        normal, reduced = self._try_ovriga_format(text)
        if normal is not None:
            return (normal, reduced)

        normal, reduced = self._try_avgift_format(text)
        if normal is not None:
            return (normal, reduced)

        normal, reduced = self._try_english_price(text)
        return (normal, reduced)

    def _try_gratis(self, text: str) -> tuple[Optional[int], Optional[int]]:
        """Match 'gratis' (free event)."""
        if re.search(r"gratis", text, re.IGNORECASE):
            logger.debug("Price from gratis: 0")
            return (0, None)
        return (None, None)

    def _try_kostar_with_reduced(self, text: str) -> tuple[Optional[int], Optional[int]]:
        """Match 'kostar 400 kr för X tillfällen (studerande eller pensionär 250 kr)'"""
        match = re.search(r"kostar\D*(\d+)\D*kr", text, re.IGNORECASE)
        if match:
            normal = int(match.group(1))
            logger.debug(f"Price from kostar: {normal}")

            reduced_match = re.search(r"pensionär\D*(\d+)\D*kr", text, re.IGNORECASE)
            reduced = int(reduced_match.group(1)) if reduced_match else None
            if reduced:
                logger.debug(f"Reduced price from pensionär: {reduced}")
            return (normal, reduced)
        return (None, None)

    def _try_ovriga_format(self, text: str) -> tuple[Optional[int], Optional[int]]:
        """Match 'Avgift: Studerande, pensionär 300.-, övriga 500.-'"""
        normal_match = re.search(r"övriga\D*(\d+)", text, re.IGNORECASE)
        if normal_match:
            normal = int(normal_match.group(1))
            logger.debug(f"Price from övriga: {normal}")

            reduced_match = re.search(r"pensionär\D*(\d+)", text, re.IGNORECASE)
            reduced = int(reduced_match.group(1)) if reduced_match else None
            if reduced:
                logger.debug(f"Reduced price from pensionär: {reduced}")
            return (normal, reduced)

        reduced_match = re.search(r"studerande[^\d]*(\d+)", text, re.IGNORECASE)
        if reduced_match:
            reduced = int(reduced_match.group(1))
            logger.debug(f"Reduced price from studerande: {reduced}")
            return (None, reduced)

        return (None, None)

    def _try_english_price(self, text: str) -> tuple[Optional[int], Optional[int]]:
        """Match 'Price: 500'"""
        match = re.search(r"Price\s*:\s*(\d+)", text, re.IGNORECASE)
        if match:
            normal = int(match.group(1))
            logger.debug(f"Price from English format: {normal}")
            return (normal, None)
        return (None, None)

    def _try_avgift_format(self, text: str) -> tuple[Optional[int], Optional[int]]:
        """Match 'Avgift: 550 kr' or similar specific Avgift patterns."""
        html_patterns = [
            r"<b>\s*Avgift\s*</b>\s*:\s*(\d+)\s*kr",
            r"<b>\s*Avgift\s*</b>\s*(\d+)\s*kr",
        ]
        plain_patterns = [
            r"[Aa]vgift\s*:\s*(\d+)\s*kr",
            r"[Aa]vgift\s+(\d+)(?:\s|$)",
        ]
        for pattern in html_patterns + plain_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                normal = int(match.group(1))
                logger.debug(f"Price from Avgift format: {normal}")
                return (normal, None)
        return (None, None)
