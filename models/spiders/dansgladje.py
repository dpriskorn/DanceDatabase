import scrapy


class Dansgladje(scrapy.Spider):
    name = "dansgladje_spider"
    start_urls = ["https://dans.se/tools/calendar/?org=dansgladje&restrict=dansgladje"]

    def parse(self, response):
        # Extract all event URLs from the calendar table
        event_links = response.css('table.calendar td.date a::attr(href)').getall()
        event_links += response.css('table.calendar td.headline a::attr(href)').getall()

        # Remove duplicates
        event_links = list(set(event_links))

        for url in event_links:
            yield scrapy.Request(url=url, callback=self.parse_event)

    def parse_event(self, response):
        # Example: extract event details, adapt selectors as needed
        yield {
            "url": response.url,
            "title": response.css("h1::text").get(),
            "date": response.css(".event-date::text").get(),
            "location": response.css(".event-location::text").get(),
            "description": response.css(".event-description::text").get(),
        }
