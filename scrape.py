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
import io
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
#print(rooturl)



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


def fetchNovelData(novelURL):
    soup = bs4.BeautifulSoup(requests.get(novelURL).text, 'html.parser')
    x=re.search("/[0-9]+/",novelURL)
    bookID=x.group()
    
    novelData=soup.find("div",{"class":"fic-title"})
    novelData=novelData.get_text().strip().split("\n")
    bookTitle=novelData[0]
    bookAuthor=novelData[len(novelData)-1]
    #logging.warning(novelData)
    
    bookTitle=remove_invalid_characters(bookTitle)
            
    description=soup.find("div",{"class":"description"}).get_text()
    lastScraped=datetime.datetime.now()
    
    chapterTable=soup.find("table",{"id":"chapters"})
    rows=chapterTable.find_all("tr")
    
    latestChapter=rows[len(rows)-1]
    latestChapter=latestChapter.find("a")["href"].split("/")
    latestChapterID=latestChapter[5]
    
    #print(description)
    return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID

#logging.warning(fetchNovelData(url))

def fetchChapterList(novelURL):
    soup = bs4.BeautifulSoup(requests.get(novelURL).text, 'html.parser')
    chapterTable=soup.find("table",{"id":"chapters"})
    rows=chapterTable.find_all("tr")
    
    rooturl=re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/",novelURL)
    rooturl=rooturl.group()
    
    chapterListURL=list()
    f=open("chapters.txt","w")
    for row in rows[1:len(rows)-1]:
        chapterData={}
        chapterData["name"]=row.find("a").contents[0].strip()
        processChapterURL=row.find("a")["href"].split("/")
        #Process into shortened link
        chapterURL=f"{rooturl}{processChapterURL[2]}/{processChapterURL[4]}/{processChapterURL[5]}/"
        chapterListURL.append(chapterURL)
        chapterData["url"]=chapterURL
        f.write(str(chapterData)+"\n")
    f.close()
    return chapterListURL

#logging.warning(fetchChapterList(url))




""" 

#There needs to be a file to keep track of the order of the chapters within the books/raw/bookTitle folder.
#This is because authors tend to go between Ch then Vol Ch, and then back to Ch

def check_order_of_contents(bookTitle,novelURL):
    dirLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
    if (check_directory_exists(dirLocation)):
        f= open(dirLocation,"r")
        f.read()
    else:
        f=[]
    
    chapterList=extract_chapter_ID(fetchChapterList(novelURL))
    newChapterList=update_order_of_contents(chapterList,f)
    
    write_order_of_contents(newChapterList,bookTitle)
    
    if (isinstance(f,io.IOBase)):
        f.close()

    
def update_order_of_contents(chapterList, existingChapterList):
    seen = set()
    combined_list = []

    for chapter in existingChapterList:
        if chapter not in seen:
            seen.add(chapter)
            combined_list.append(chapter)

    for chapter in chapterList:
        if chapter not in seen:
            seen.add(chapter)
            combined_list.append(chapter)

    return combined_list



 """




def fetchChapter(chapterURL):
    soup = bs4.BeautifulSoup(requests.get(chapterURL).text, 'html.parser')
    chapterContent=soup.find("div",{"class":"chapter-inner chapter-content"}).encode('ascii')
    return chapterContent
    


#Get the chapter ID and title.
def extract_chapter_ID(chapterURL):
    chapter=chapterURL.split("/")
    return chapter[len(chapter)-2]

def extract_chapter_title(string):
    extractedTitle=string.split("/")
    return extractedTitle[len(extractedTitle)-1]
    
    
def get_existing_order_of_contents(bookTitle):
    dirLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
    if (check_directory_exists(dirLocation)):
        f= open(dirLocation,"r")
        return f.readlines()
    else:
        return False
        
        

def write_order_of_contents(bookTitle, chapterData):
    logging.warning(bookTitle)
    bookDirLocation=f"./books/raw/{bookTitle}"
    if not (check_directory_exists(bookDirLocation)):
        make_directory(bookDirLocation)
    fileLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
    if (os.path.exists(fileLocation)):
        f=open(fileLocation,"w")
    else:
        f=open(fileLocation,"x")
    
    for dataLine in chapterData:
        chapterID=dataLine[0]
        chapterLink=dataLine[1]
        chapterTitle=dataLine[2]
        f.write(chapterID+";"+chapterLink+";"+chapterTitle+"\n")
    f.close()
        
        

def fetchChapterTitle(soup):
    if not (isinstance(soup, bs4.BeautifulSoup)):
        soup=bs4.BeautifulSoup(requests.get(soup).text, 'html.parser')
    chapterTitle=soup.find("h1").get_text()
    return chapterTitle

def retrieveStoredChapter(bookTitle,chapterID):

    pass

def remove_invalid_characters(inputString):
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        inputString=inputString.replace(char,'')
    inputString=re.sub(r"[\(\[].*?[\)\]]", "", inputString)
    inputString=inputString.strip()
    return inputString

def check_if_chapter_exists(chapterID,savedChapters):
    
    if (savedChapters is False):
        return False
    for chapter in savedChapters:
        if chapterID in chapter:
            return True
    return False

def get_chapter_from_saved(chapterID,savedChapters):
    for chapter in savedChapters:
        chapter=chapter.split(";")
        #logging.warning(chapterID+" "+chapter[0])
        if chapterID == chapter[0]:
            return chapter[0],chapter[2].replace("\n","")
    return -1,-1
    
def get_chapter_contents_from_saved(dirLocation):
    logging.warning(dirLocation)
    f=open(dirLocation,"r")
    
    return f.read()

def produceEpub(novelURL,bookTitle,Author):
    new_epub=pypub.Epub(bookTitle, creator=Author)
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    chapterMetaData=list()
    for url in fetchChapterList(novelURL):
        #logging.warning(url)
        chapterID=extract_chapter_ID(url)
        chapterTitle=fetchChapterTitle(url)
        if (already_saved_chapters is False):
            title = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
            chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{title}.html"])
            chapterContent=fetchChapter(url)
            
            store_chapter(chapterContent,bookTitle,chapterTitle,chapterID)
            
        if (check_if_chapter_exists(chapterID,already_saved_chapters)):
            logging.warning('Chapter exists')
            chapterID,dirLocation=get_chapter_from_saved(chapterID,already_saved_chapters)
            chapterContent=get_chapter_contents_from_saved(dirLocation).encode("utf-8")
            chapterTitle=extract_chapter_title(dirLocation)
            
        
    
        new_chapter=pypub.create_chapter_from_html(chapterContent, chapterTitle)
        new_epub.add_chapter(new_chapter)
        time.sleep(0.5)
        
    if (already_saved_chapters is False):
        write_order_of_contents(bookTitle, chapterMetaData)
    
    
    storeEpub(bookTitle,new_epub)
    
def storeEpub(bookTitle,new_epub):
    dirLocation="./epubs/"+bookTitle
    if not check_directory_exists(dirLocation):
        make_directory(dirLocation)
    
    dirLocation="./epubs/"+bookTitle+"/"+bookTitle+".epub"
    if (check_directory_exists(dirLocation)):
        os.remove(dirLocation)
    new_epub.create(dirLocation)

def store_chapter(content,bookTitle, chapterTitle,chapterID):
    #remove invalid characters from file name
    
    bookTitle=remove_invalid_characters(bookTitle)
    chapterTitle=remove_invalid_characters(chapterTitle)
        
    #Check if the folder for the book exists
    bookDirLocation="./books/raw/"+bookTitle
    if not (check_directory_exists(bookDirLocation)):
        make_directory(bookDirLocation)

    
    logging.warning(chapterID)
    #check if the chapter already exists
    title = f"{bookTitle} - {chapterID} - {chapterTitle}"
    logging.warning(title)
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
    

def create_epub_directory_url(bookTitle):
    dirLocation="./epubs/"+bookTitle+"/"+bookTitle+".epub"
    return dirLocation

def get_first_last_chapter(bookTitle):
    dirLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
    if (check_directory_exists(dirLocation)):
        f= open(dirLocation,"r")
        lines=f.readlines()
        f.close()
    else:
        return -1,-1,-1
    firstChapterID=lines[0].split(";")[0]
    lastChapterID=lines[0].split(";")[len(lines)-1]
    
    
    
    return firstChapterID,lastChapterID,len(lines)




#Return existing epub directory if the latest chapter is already stored.
def getEpub(bookID):
    results=savedBooks.find_one({"bookID":bookID})
    directory=results["directory"]
    return directory

    
    

def check_latest_chapter(bookID,bookTitle,latestChapter):
    bookData=get_Entry(bookID)
    if (bookData is None):
        return False
    if (bookData["lastChapter"]==latestChapter):
        return True
    elif (bookData["lastChapter"]<=latestChapter):
        #update epub
        return False
    return True


#Main call interface.
def mainInterface(novelURL):
    bookurl=re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/[0-9]+/",novelURL)
    bookurl=bookurl.group()
    bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter=fetchNovelData(bookurl)
    
    
    if(check_latest_chapter(bookID,bookTitle,latestChapter)):
        getEpub(bookID)
    else:
        produceEpub(novelURL,bookTitle,bookAuthor)

        
        
        rooturl = re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/", novelURL)
        rooturl = rooturl.group()
        first,last,total=get_first_last_chapter(bookTitle)
        
        bookID=remove_invalid_characters(bookID)

        create_Entry(
            bookID=int(bookID),
            bookName=bookTitle,
            bookAuthor=bookAuthor,
            bookDescription=description,
            websiteHost=rooturl,
            firstChapter=first,
            lastChapter=last,
            totalChapters=total,
            directory=create_epub_directory_url(bookTitle)
        )
    
    
    
    #pass
    #check to see if epub already exists
    #check if new chapter was published for given book
    
    #if yes, update epub.
    #if no, return current epub.

    #implement store order of chapters



#Requires 9 inputs. BookID, bookName, bookAuthor, bookDescription, WebsiteHost, firstChapter#, lastChapter#, totalChapters, directory
def create_Entry(**kwargs):
    logging.warning(kwargs)
    default_values = {
        "bookID": 0,
        "bookName": "Template",
        "bookAuthor": "Template",
        "bookDescription": "Template",
        "websiteHost": "Template",
        "firstChapter": -1,
        "lastChapter": -1,
        "totalChapters":-1,
        "directory": "Template"
    }
    #If missing keyword arguments, fill with template values.
    book_data = {**default_values, **kwargs}
    
    logging.warning(book_data)
    book = {
        "bookID": book_data["bookID"],
        "bookName": book_data["bookName"],
        "bookAuthor":book_data["bookAuthor"],
        "bookDescription": book_data["bookDescription"],
        "websiteHost": book_data["websiteHost"],
        "firstChapter": book_data["firstChapter"],
        "lastChapter": book_data["lastChapter"],
        "lastScraped": datetime.datetime.now(),
        "totalChapters": book_data["totalChapters"],
        "directory": book_data["directory"]
    }
    
    if (check_existing_book(book_data["bookID"])):
        savedBooks.replace_one({"bookID": book_data["bookID"]}, book)
    else:
        savedBooks.insert_one(book)

#Retrieve book data from MongoDB
def get_Entry(bookID):
    results=savedBooks.find_one({"bookID":bookID})
    return results


#logging.warning(read_Entry(54046))

mainInterface("https://www.royalroad.com/fiction/54046/final-core-a-holy-dungeon-core-litrpg")


@app.get("/")
def read_root():
    return {"Hello": "World"}
