import bs4
import requests
import re
from pathlib import Path
from pymongo import MongoClient
import os, errno
import pypub
import datetime
from novel_template import NovelTemplate
import logging
import time

import jsonschema

MONGODB_URL=os.getenv('MONGODB_URI')
myclient=MongoClient(MONGODB_URL)
mydb=myclient["Webnovels"]
savedBooks=mydb["Books"]


from typing import Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app=FastAPI()
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
url="https://www.royalroad.com/fiction/55927/"
rooturl=re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/",url)
rooturl=rooturl.group()
print(rooturl)


#https://([A-Za-z]+(\.[A-Za-z]+)+)/fiction/55927/

def fetchNovelData(novelURL):
    soup = bs4.BeautifulSoup(requests.get(novelURL).text, 'html.parser')
    x=re.search("/[0-9]+/",novelURL)
    bookID=x.group()
    
    novelData=soup.find("div",{"class":"fic-title"})
    novelData=novelData.get_text().strip().split("\n")
    bookTitle=novelData[0]
    bookAuthor=novelData[len(novelData)-1]
    
    description=soup.find("div",{"class":"description"}).get_text()
    lastScraped=datetime.datetime.now()
    #print(description)
    return (bookID,bookTitle,bookAuthor,description,lastScraped)

fetchNovelData(url)


def fetchChapterList(novelURL):
    soup = bs4.BeautifulSoup(requests.get(novelURL).text, 'html.parser')
    chapterTable=soup.find("table",{"id":"chapters"})
    rows=chapterTable.find_all("tr")
    bookData=list()
    chapterListURL=list()
    f=open("chapters.txt","w")
    for row in rows[1:len(rows)-1]:
        chapterData={}
        chapterData["name"]=row.find("a").contents[0].strip()
        
        processChapterURL=row.find("a")["href"].split("/")
        chapterURL=rooturl+""+processChapterURL[1]+"/"+processChapterURL[2]+"/"+processChapterURL[4]+"/"+processChapterURL[5]+"/"
        #print(processChapterURL)
        chapterListURL.append(chapterURL)
        chapterData["url"]=processChapterURL
        bookData.append(chapterData)
        f.write(str(chapterData)+"\n")        
    f.close()
    return chapterListURL

#fetchChapterList(url)

#cors issues.

#@app.get("/chapters")



def fetchChapter(chapterURL):
    soup = bs4.BeautifulSoup(requests.get(chapterURL).text, 'html.parser')
    chapterContent=soup.find("div",{"class":"chapter-inner chapter-content"}).encode('ascii')
    logging.warning(chapterContent)
    return chapterContent
    
    '''
    
    #rows=chapterContent.find_all("p")
    chapterText=list()
    for row in rows[1:len(rows)-1]:
        chapterLine={}
        chapterLine=row.get_text()
        chapterText.append(chapterLine)
    print (chapterText)
    #return (chapterText)'''

def produceEpub(novelURL,bookTitle,Author):
    new_epub=pypub.Epub(bookTitle, creator=Author)
    
    #Get Title, Format Pages
    
    for url in fetchChapterList(novelURL):
        #url="https://www.royalroad.com/fiction/55927/the-newt-and-demon-book-1-2-on-amazon-cozy-alchemy/chapter/937104/chapter-1-the-end-of-the-world"
        #logging.warning(url)
        time.sleep(0.5)
        new_chapter=pypub.create_chapter_from_html(fetchChapter(url))
        new_epub.add_chapter(new_chapter)
    
    if not os.path.exists("./epubs/"+bookTitle):
        try:
            os.makedirs("./epubs/"+bookTitle)
        except OSError as e:
            if e.errno!=errno.EEXIST:
                raise
    new_epub.create('./epubs/{bookTitle}/'+bookTitle)
    
    #pass

produceEpub("https://www.royalroad.com/fiction/55927/","Newt")

#fetchChapter("https://www.royalroad.com/fiction/55927/chapter/937273/")



def mainInterface(chapterURL):
    bookurl=re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/[0-9]+/",chapterURL)
    bookurl=bookurl.group()
    fetchNovelData(bookurl)
    
    soup = bs4.BeautifulSoup(requests.get(chapterURL).text, 'html.parser')
    pass
    #check to see if epub already exists
    #check if new chapter was published for given book
    
    #if yes, update epub.
    #if no, return current epub.


def getEpub(novelURL):
    pass



def check_existing_book(bookID):
    results=savedBooks.find_one({"bookID":bookID})
    if (results==None):
        return False
    else:
        return True



#Requires 6 inputs. BookID, bookName, bookDescription, WebsiteHost, firstChapter#, lastChapter#
def create_Entry(**kwargs):
    logging.warning(kwargs)
    default_values = {
        "bookID": 0,
        "bookName": "Template",
        "bookDescription": "Template",
        "websiteHost": "Template",
        "firstChapter": -1,
        "lastChapter": -1
    }
    #If missing keyword arguments, fill with template values.
    book_data = {**default_values, **kwargs}
    
    logging.warning(book_data)
    book = {
        "bookID": book_data["bookID"],
        "bookName": book_data["bookName"],
        "bookDescription": book_data["bookDescription"],
        "websiteHost": book_data["websiteHost"],
        "firstChapter": book_data["firstChapter"],
        "lastChapter": book_data["lastChapter"],
        "lastScraped": datetime.datetime.now()
    }
        
    #book_json_schema=novelSchema
    
    if (check_existing_book(book_data["bookID"])):
        savedBooks.replace_one({"bookID": book_data["bookID"]}, book)
    else:
        savedBooks.insert_one(book)
        
#create_Entry(bookID=0, bookName="Template", bookDescription="Template")




@app.get("/")
def read_root():
    return {"Hello": "World"}
