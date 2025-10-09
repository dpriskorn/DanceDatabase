# from main import DanceEvent
#
#
# class DanceEventsSpider(scrapy.Spider):
#     """
#     example html
#     <div class="col-md-4 col-lg-4 col-sm-12">
#                 <div class="card custom-card p-2 mt-2 mb-4">
#                   <div class="text-center">
#                     <h2 style="font-family: 'Barlow Condensed', sans-serif; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"><b>WCS Umeå</b></h2>
#                   </div>
#                   <div class="image-container">
#
#                       <img src="/admin/club_images/1.png" alt="Club Image" class="custom-card-img">
#
#                   </div>
#
#                     <div class="card-body">
#                       <h3 class="custom-card-title">Community Swing 2025</h3>
#                       <p class="custom-card-text">
#                       <strong>Where:</strong> Umeå Folkets Hus<br>
#                       <strong>When:</strong> Starts 2025-11-15
#                       </p>
#
#                         <a href="/wcsumea/community-swing-25" class="btn btn-rounded btn-green px-5">Read more and Register</a>
#
#                     </div>
#                 </div>
#             </div>
#     """
#     name = "dance_events"
#     start_urls = ["https://onbeat.dance/explore"]  # Replace with real URL
#
#     def parse(self, response):
#         """Parse list of event cards."""
#         for card in response.css("div.col-md-4.col-lg-4.col-sm-12"):
#             title = card.css("h3.custom-card-title::text").get(default="").strip()
#             organizer = card.css("h2 b::text").get(default="").strip()
#             where = card.css("p strong:contains('Where:')::text").get()
#             when_text = card.css("p::text").re_first(r"Starts\s+([\d-]+)")
#
#             start_time = None
#             if when_text:
#                 try:
#                     start_time = datetime.strptime(when_text, "%Y-%m-%d")
#                 except ValueError:
#                     pass
#
#             link = card.css("a.btn-green::attr(href)").get()
#             image = card.css("img.custom-card-img::attr(src)").get()
#
#             event = DanceEvent(
#                 id=f"{organizer.lower().replace(' ', '-')}-{start_time.date() if start_time else 'unknown'}",
#                 # dance_type_qid="",  # could be mapped later
#                 start_time_utc=start_time,
#                 label={"sv": title, "en": title},
#                 # description="",
#                 # coordinates="",
#                 # organizer_qid="",
#                 fully_booked=False,
#                 website=str(response.urljoin(link)) if link else "",
#                 location=where,
#                 image=image,
#             )
#
#             yield event.model_dump()
#
# # Example Scrapy command to run this:
# # scrapy runspider dance_events_spider.py -O events.json
