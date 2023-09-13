import scrapy
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule

class MainSpider(CrawlSpider):
    name            = 'main'
    allowed_domains = ['tap.az']
    start_urls      = ['https://tap.az/elanlar']

    rules = (
               Rule(LinkExtractor( allow    =  ('/elanlar/')),
                                   callback =  'parse_item',
                                   follow   =  True
                   ),
            )

    def parse_item(self, response):
        self.logger.info('Parsing page: %s', response.url)
        yield {
            'id'                   : response.css('div.lot-info p:nth-child(1)::text').get(),
            'view'                 : response.css('div.lot-info p:nth-child(2)::text').get(),
            'updated'              : response.css('div.lot-info p:nth-child(2)::text').get(),
            'title'                : response.css('.js-lot-title::text').get(),
            'name'                 : response.css('div.name::text').get(),
            'phone'                : response.css('div.show-phones span:nth-child(2)::text').get(),
            'url'                  : response.url,
            'price'                : response.css('.price-val::text').get(),
            'currency'             : response.css('.price-cur::text').get(),
            'location'             : response.css('.property-value::text').get(),
            'type'                 : response.css('table.properties td.property-value:nth-child(2)::text').get(),
            'building_type'        : response.css('table.properties td.property-value:nth-child(3)::text').get(),
            'area'                 : response.css('table.properties td.property-value:nth-child(4)::text').get(),
            'room_count'           : response.css('table.properties td.property-value:nth-child(4)::text').get(),
            'loc_details'          : response.css('table.properties td.property-value:nth-child(4)::text').get(),
            'description'          : response.css('div.lot-text p::text').get(),

        }