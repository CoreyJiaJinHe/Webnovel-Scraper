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

#fetchNovelData(url)


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
        chapterURL=f"{rooturl}{processChapterURL[2]}/{processChapterURL[4]}/{processChapterURL[5]}/"
        #print(processChapterURL)
        chapterListURL.append(chapterURL)
        chapterData["url"]=processChapterURL
        bookData.append(chapterData)
        f.write(str(chapterData)+"\n")        
    f.close()
    return chapterListURL

#logging.warning(fetchChapterList("https://www.royalroad.com/fiction/55927/"))




def fetchChapter(chapterURL):
    soup = bs4.BeautifulSoup(requests.get(chapterURL).text, 'html.parser')
    chapterContent=soup.find("div",{"class":"chapter-inner chapter-content"}).encode('ascii')
    return chapterContent
    

def check_directory_exists(path):
    if os.path.exists(path):
        return True
    return False
        
def make_directory(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno!=errno.EEXIST:
            raise

def check_existing_book(bookID):
    results=savedBooks.find_one({"bookID":bookID})
    if (results==None):
        return False
    else:
        return True


def fetchChapterTitle(soup):
    logging.warning(soup)
    if not (isinstance(soup, bs4.BeautifulSoup)):
        soup=bs4.BeautifulSoup(requests.get(soup).text, 'html.parser')
    chapterTitle=soup.find("h1").get_text()
    return chapterTitle


#There needs to be a file to keep track of the order of the chapters within the books/raw/bookTitle folder.
#This is because authors tend to go between Ch then Vol Ch, and then back to Ch

def order_of_contents():
    pass

def produceEpub(novelURL,bookTitle,Author):
    new_epub=pypub.Epub(bookTitle, creator=Author)
    
    for url in fetchChapterList(novelURL):
        chapterTitle = fetchChapterTitle(url)
        chapterContent=fetchChapter(url)
        
        store_chapter(chapterContent,bookTitle,chapterTitle)
    
        new_chapter=pypub.create_chapter_from_html(chapterContent, chapterTitle)
        new_epub.add_chapter(new_chapter)
        time.sleep(0.5)
    dirLocation="./epubs/"+bookTitle
    if not check_directory_exists(dirLocation):
        make_directory(dirLocation)
    
    dirLocation="./epubs/"+bookTitle+"/"+bookTitle+".epub"
    if (check_directory_exists(dirLocation)):
        os.remove(dirLocation)
    new_epub.create(dirLocation)
    
    #pass

def store_chapter(content,bookTitle, chapterTitle):
    #remove invalid characters from file name
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        bookTitle = bookTitle.replace(char, '')
        chapterTitle = chapterTitle.replace(char, '')
        
    #Check if the folder for the book exists
    bookDirLocation="./books/raw/"+bookTitle
    if not (check_directory_exists(bookDirLocation)):
        make_directory(bookDirLocation)

    #check if the chapter already exists
    
    title = f"{bookTitle} - {chapterTitle}"
    dirLocation=f"./books/raw/{bookTitle}/{title}.html"
    #if it is, don't store
    if check_directory_exists(dirLocation):
        logging.warning("Chapter already stored")
        return
    #otherwise, do store the chapter.
    chapterDirLocation = "./books/raw/"+bookTitle+"/"
    completeName = os.path.join(chapterDirLocation, f"{title}.html")
    with open(completeName, "x") as f:
        f.write(content.decode('utf8'))
    f.close()
    



produceEpub("https://www.royalroad.com/fiction/55927/","Newt", "Emgriffiths")

#fetchChapter("https://www.royalroad.com/fiction/55927/chapter/937273/")

#Main call interface.
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

#Return existing epub if the latest chapter is already stored.
def getEpub(novelURL):
    pass


def check_latest_chapter(bookID):
    pass


#Requires 6 inputs. BookID, bookName, bookDescription, WebsiteHost, firstChapter#, lastChapter#
def create_Entry(**kwargs):
    logging.warning(kwargs)
    default_values = {
        "bookID": 0,
        "bookName": "Template",
        "bookDescription": "Template",
        "websiteHost": "Template",
        "firstChapter": -1,
        "lastChapter": -1,
        "totalChapters":-1
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
        "lastScraped": datetime.datetime.now(),
        "totalChapters": book_data["totalChapters"]
    }
    
    if (check_existing_book(book_data["bookID"])):
        savedBooks.replace_one({"bookID": book_data["bookID"]}, book)
    else:
        savedBooks.insert_one(book)
        
#create_Entry(bookID=0, bookName="Template", bookDescription="Template")




@app.get("/")
def read_root():
    return {"Hello": "World"}
