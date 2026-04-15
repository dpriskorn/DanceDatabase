import pytest

from src.models.cogwork.price import PriceExtractor, PriceMismatchError


class TestPriceExtractor:
    def test_kostar_format_extracts_normal_price(self):
        extractor = PriceExtractor("Kursen kostar 500 kr")
        normal, reduced = extractor.extract()
        assert normal == 500
        assert reduced is None

    def test_kostar_format_extracts_both_prices(self):
        text = "Kursen kostar 400 kr för 6 tillfällen (studerande eller pensionär 250 kr)"
        extractor = PriceExtractor(text)
        normal, reduced = extractor.extract()
        assert normal == 400
        assert reduced == 250

    def test_kostar_no_space(self):
        extractor = PriceExtractor("Kursen kostar 500kr")
        normal, reduced = extractor.extract()
        assert normal == 500

    def test_ovriga_format_extracts_both_prices(self):
        text = "Avgift: Studerande, pensionär 300.-, övriga 500.-"
        extractor = PriceExtractor(text)
        normal, reduced = extractor.extract()
        assert normal == 500
        assert reduced == 300

    def test_english_price_format(self):
        extractor = PriceExtractor("Price: 300")
        normal, reduced = extractor.extract()
        assert normal == 300

    def test_no_price_raises_exception(self):
        extractor = PriceExtractor("Free event")
        with pytest.raises(PriceMismatchError, match="No price found"):
            extractor.extract()

    def test_kostar_case_insensitive(self):
        extractor = PriceExtractor("KOSTAR 750 KR")
        normal, reduced = extractor.extract()
        assert normal == 750

    def test_kostar_with_nbsp(self):
        extractor = PriceExtractor("Kursen kostar 400\xa0kr")
        normal, reduced = extractor.extract()
        assert normal == 400

    def test_gratis_is_zero(self):
        extractor = PriceExtractor("Välkommen den 10/4 kl 10-12. Vi bjuder på fika. Gratis.")
        normal, reduced = extractor.extract()
        assert normal == 0
        assert reduced is None

    def test_avgift_format(self):
        extractor = PriceExtractor("Avgift: 350 kr")
        normal, reduced = extractor.extract()
        assert normal == 350

    def test_avgift_format_no_colon(self):
        extractor = PriceExtractor("Avgift 350 kr")
        normal, reduced = extractor.extract()
        assert normal == 350

    def test_avgift_format_with_newlines(self):
        html = "<!DOCTYPE html>\n<html>\nAvgift: 150 kr\n</html>"
        extractor = PriceExtractor(html)
        normal, reduced = extractor.extract()
        assert normal == 150

    def test_full_html_document(self):
        html = """<!DOCTYPE html>
<html lang="sv">
<head>
    <meta charset="utf-8">
    <meta name="keywords" content="boka, kursavgift">
</head>
<body>
    <div class="cwColumnNarrow cwDataArea">
        <p><b>Ort</b>: Sundsvall</p>
        <p class="cwPlace"><b>Var</b>: Spegelsalen i Stadshuset, Sundsvall</p>
        <p><b>När</b>: Lö 18/4 17:00 - 01.30</p>
        <p><b>Avgift</b>: 550 kr</p>
    </div>
</body>
</html>"""
        extractor = PriceExtractor(html)
        normal, reduced = extractor.extract()
        assert normal == 550

    def test_html_extraction_from_sidebar(self):
        html = """<div class="cwColumnNarrow cwDataArea">
    <p><b>Ort</b>: Sundsvall</p>
    <p><b>Avgift</b>: 350 kr</p>
</div>"""
        extractor = PriceExtractor(html)
        normal, reduced = extractor.extract()
        assert normal == 350

    def test_data_area_fallback(self):
        html = """<div class="cwDataArea">
    <p><b>Avgift</b>: 400 kr</p>
</div>"""
        extractor = PriceExtractor(html)
        normal, reduced = extractor.extract()
        assert normal == 400

    def test_cwcolumnwide_main_content(self):
        html = """<div class="cwColumnWide">
    <p>Kursen kostar 250 kr</p>
</div>"""
        extractor = PriceExtractor(html)
        normal, reduced = extractor.extract()
        assert normal == 250

    def test_plain_text_passes_through(self):
        text = "Avgift: 200 kr"
        extractor = PriceExtractor(text)
        normal, reduced = extractor.extract()
        assert normal == 200

    def test_price_mismatch_raises_exception(self):
        html = """<!DOCTYPE html>
<html>
<body>
    <div class="cwColumnNarrow cwDataArea">
        <p><b>Avgift</b>: 500 kr</p>
    </div>
    <div class="cwFormCenter">
        <p>Kursen kostar 400 kr</p>
    </div>
</body>
</html>"""
        extractor = PriceExtractor(html)
        with pytest.raises(PriceMismatchError, match="Price mismatch"):
            extractor.extract()

    def test_main_text_and_sidebar_both_used(self):
        html = """<!DOCTYPE html>
<html>
<body>
    <div class="cwColumnNarrow cwDataArea">
        <p><b>Avgift</b>: 500 kr</p>
    </div>
    <div class="cwFormCenter">
        <p>Kursen kostar 500 kr</p>
    </div>
</body>
</html>"""
        extractor = PriceExtractor(html)
        normal, reduced = extractor.extract()
        assert normal == 500
