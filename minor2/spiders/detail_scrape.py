import crochet
crochet.setup()     # initialize crochet

#All imports used in project
import json
import scrapy
import pickle
from flask import Flask,request
from scrapy.crawler import CrawlerRunner
from flask_cors import CORS
from scrapy.utils.log import configure_logging
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
#Intilazations
app = Flask('Scrape With Flask')
cors = CORS(app)
crawl_runner = CrawlerRunner()      # requires the Twisted reactor to run                  # store quotes
scrape_in_progress = False
scrape_complete = False
urls2=[]
final_data = {}

#Spider
class MySpider2(scrapy.Spider):
    name="course_details"
    def start_requests(self):
        for url in urls2[0]:
            yield scrapy.Request(url=url,callback=self.parse)
            
    def parse(self,response):
        course_details={}
        name= response.css('h1.banner-title::text').get()
        instructor_rating= response.css('span.avg-instructor-rating__total span::text').get()
        skills=response.css('div.Skills span::text').getall()
        rating_div=response.css('div.XDPRating span::text').getall()
        content_rating=rating_div[0]
        no_of_ratings=rating_div[1]
        domains=response.css('a.color-white.font-weight-bold::text').getall()
        domain=domains[1:]
        no_of_reviews=response.xpath('.//div/div/div/span/text()').getall()[0]
        time= response.css('h4._16ni8zai.m-b-0.m-t-1s span::text').get()
        org=response.css('h4.headline-4-text.bold.rc-Partner__title::text').get()
        instructor=response.css('h4.rc-Partner__title::text').get()
        course_details['name']=name
        course_details['instructor_rating']=instructor_rating
        course_details['no_of_reviews']=no_of_reviews.split(" ")[0]
        course_details['skills']=skills
        course_details['content_rating']=content_rating
        course_details['no_of_ratings']=no_of_ratings.split(" ")[0]
        course_details['domain']=domain
        course_details['time']=time.split(" ")[1]
        course_details['org']=org
        final_data[name]=course_details


#url requests
@app.route('/coursedetails',methods=['POST'])
def coursedetails():
    req_data=request.get_json()
    urls2.append(req_data['data_url'])
    configure_logging({'LOG_FORMAT': '%(levelname)s: %(message)s'})
    global scrape_in_progress
    global scrape_complete

    if not scrape_in_progress:
        scrape_in_progress = True
        global quotes_list
        # start the crawler and execute a callback when complete
        scrape_with_crochet()
        return 'SCRAPING'
    elif scrape_complete:
        return 'SCRAPE COMPLETE'
    return 'SCRAPE IN PROGRESS'    

@app.route('/results')
def get_results():
    """
    Get the results only if a spider has results
    """
    global scrape_complete
    if scrape_complete:
        # with open("detail.pkl","wb") as f:
        #     pickle.dump(final_data,f)
        return json.dumps(final_data)
    return 'Scrape Still Progress'

@crochet.run_in_reactor
def scrape_with_crochet():
    eventual=crawl_runner.crawl(MySpider2)
    eventual.addCallback(finished_scrape)

def finished_scrape(null):
    """
    A callback that is fired after the scrape has completed.
    Set a flag to allow display the results from /results
    """
    global scrape_complete
    global scrape_in_progress
    scrape_complete = True

#run app
if __name__=='__main__':
    app.run('0.0.0.0', 9000)