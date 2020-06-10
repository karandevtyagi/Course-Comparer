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
import numpy as np
import pandas as pd
import spacy
from spacy_langdetect import LanguageDetector
from spacy.lang.en.stop_words import STOP_WORDS
import pickle
#Intilazations
app = Flask('Scrape With Flask')
cors = CORS(app)
crawl_runner = CrawlerRunner()      # requires the Twisted reactor to run                  # store quotes
scrape_in_progress = False
scrape_complete = False
urls2=[]
response = {}
course_name=""
nlp = spacy.load('en_core_web_sm')
nlp.add_pipe(LanguageDetector(), name='language_detector', last=True)
other_stopwords = {"i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", 
            "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", 
            "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", 
            "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", 
            "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", 
            "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", 
            "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", 
            "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", 
            "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than",
            "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"}
STOP_WORDS = STOP_WORDS | other_stopwords
nlp.max_length = 150000000000000
#process function
def process(name):
    data=pd.read_csv("./course_review1.csv")
    data = data.fillna("")
    ml_data = data[data['CourseId'] == name]
    ml_data=ml_data[ml_data['Label']!='']
    positive = ml_data[ml_data['Label'].astype(int) >= 4]
    neutral = ml_data[ml_data['Label'].astype(int) == 3]
    negative = ml_data[ml_data['Label'].astype(int) <= 2]
    positive_string = ' '.join(list(positive["Review"]))
    neutral_string = ' '.join(list(neutral["Review"]))
    negative_string = ' '.join(list(negative["Review"]))
    doc_positive = nlp(positive_string)
    doc_neutral = nlp(neutral_string)
    doc_negative = nlp(negative_string)
    # Extract all phrases

    positive_phrases = [chunk.text.lower() for chunk in doc_positive.noun_chunks if chunk.text.lower() not in STOP_WORDS]
    #print(positive_phrases)
    positive_phrases = pd.Series(positive_phrases)


    neutral_phrases = [chunk.text.lower() for chunk in doc_neutral.noun_chunks if chunk.text.lower() not in STOP_WORDS]
    #print(neutral_phrases)
    neutral_phrases = pd.Series(neutral_phrases)


    negative_phrases = [chunk.text.lower() for chunk in doc_negative.noun_chunks if chunk.text.lower() not in STOP_WORDS]
    #print(negative_phrases)
    negative_phrases = pd.Series(negative_phrases)
    d={}
    d_p = {}
    rough = positive_phrases.value_counts()[:20] #top 20 only

    for review in positive["Review"]:
        for phrase,count in rough.items():
            if phrase in d_p:
                d_p[phrase].append(review)
            else:
                d_p[phrase] = [review]
    d_n = {}
    rough1 = negative_phrases.value_counts()[:20] #top 20 only

    for review in negative["Review"]:
        for phrase,count in rough1.items():
            if phrase in d_n:
                d_n[phrase].append(review)
            else:
                d_n[phrase] = [review] 
    d_nu = {}
    rough2 = neutral_phrases.value_counts()[:20] #top 20 only

    for review in neutral["Review"]:
        for phrase,count in rough2.items():
            if phrase in d_nu:
                d_nu[phrase].append(review)
            else:
                d_nu[phrase] = [review] 
    d['positive']=d_p
    d['negative']=d_n
    d['neutral']=d_nu              
    return d
#Spider
class MySpider1(scrapy.Spider):
    name="course_reviews"
    global course_name
    course_name=""
    def start_requests(self):
        for url in urls2:
            global course_name
            course_name=url.split('/')[-2]
            yield scrapy.Request(url=url,callback=self.parse)
            
    def parse(self,response):
#         reviews=response.css('div.reviewText p::text').getall()
        reviewBlock=response.css('div.review-text')
        with open('course_review1.csv','a',encoding='utf-8') as f:
            for ix in reviewBlock:
                review=ix.css('div.reviewText p::text').get()
                stars=ix.css('label svg::attr(style)').getall()
                star=len([i for i in stars if i[5]=='#'])
                review=review.replace(","," ")
                to_append=course_name+','+review+','+str(star)+'\n'
                f.write(to_append)
#             stars_list.append(star)
        f.close()
        next_page=response.css('ul.cui-buttonList a::attr(href)').getall()[-1]
        if next_page is not None:
            next_page=response.urljoin(next_page)
            yield scrapy.Request(next_page,callback=self.parse)
        else:
            global scrape_in_progress
            scrape_in_progress=False



#url requests
@app.route('/coursereview',methods=['POST'])
def coursereview():
    with open("response1.pkl","rb") as f:
        response=pickle.load(f)
    req_data=request.get_json()
    names=req_data['data_url']
    data=pd.read_csv("./course_review1.csv")
    data = data.fillna("")
    for name in names:
        n=name.split("/")[-2]
        if len(data[data['CourseId'] == n]) !=0:
            response[n]=process(n)
        else:
            urls2.append(name)
            global scrape_in_progress
            scrape_in_progress=True
            c=0
            while scrape_in_progress:
                if(c==0):
                    scrape_with_crochet()
                    c=c+1
            response[n]=process(n)
    with open("response1.pkl","wb") as f:
        pickle.dump(response,f)
    f.close()
    return json.dumps(response)


@crochet.run_in_reactor
def scrape_with_crochet():
    eventual=crawl_runner.crawl(MySpider1)
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
    app.run('0.0.0.0', 9001)