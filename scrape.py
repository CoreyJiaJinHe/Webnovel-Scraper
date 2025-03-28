import bs4
import requests
import re
from pathlib import Path
from pymongo import MongoClient
import os, errno
#import pypub
import datetime
from novel_template import NovelTemplate
import logging
import time
import io
import jsonschema
from ebooklib import epub 
from PIL import Image



#Figure out how to swap tables text color in epub.

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


def save_cover_image(title,novelURL,saveDirectory):
    soup = bs4.BeautifulSoup(requests.get(novelURL).text, 'html.parser')
    img_url = soup.find("div",{"class":"cover-art-container"}).find("img")
    response =requests.get(img_url["src"],stream=True)
    
    if (saveDirectory.endswith("/")):
        fileNameDir=f"{saveDirectory}{title}.jpg"
    else:
        fileNameDir=f"{saveDirectory}/{title}.jpg"
    
    if not response.ok:
        pass
    else:
        if not (check_directory_exists(saveDirectory)):
            make_directory(saveDirectory)
        if not (check_directory_exists(fileNameDir)):
            response=response.content
            with open (fileNameDir,'wb') as f:
                f.write(response)
            f.close()


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
    for row in rows[1:len(rows)]:
        chapterData={}
        chapterData["name"]=row.find("a").contents[0].strip()
        processChapterURL=row.find("a")["href"].split("/")
        #Process into shortened link
        chapterURL=f"{rooturl}{processChapterURL[2]}/{processChapterURL[4]}/{processChapterURL[5]}/"
        chapterListURL.append(chapterURL)
        chapterData["url"]=chapterURL
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

#Cut out and insert function
def insert_into_Chapter_List(cutOutRange,insertRange,chapterList,existingChapterList):
    cutOutChapters=chapterList[cutOutRange[0]:cutOutRange[1]]
    
    firstHalfChapters=existingChapterList[0:insertRange[0]]
    secondHalfChapters=existingChapterList[insertRange[1]:len(existingChapterList)]
    
    newChapterList=firstHalfChapters+cutOutChapters+secondHalfChapters
    
    pass

def delete_from_Chapter_List(deleteRange,existingChapterList):
    cutOutChapters=existingChapterList[deleteRange[0]:deleteRange[1]]
    
    newChapters=existingChapterList.remove(cutOutChapters)
    
    pass
    
    
    
def fetchChapter(chapterURL):
    response = requests.get(chapterURL)
    if response.status_code != 200:
        logging.warning(f"Failed to fetch chapter URL: {chapterURL}, Status Code: {response.status_code}")
        return None
    soup = bs4.BeautifulSoup(response.text, 'html.parser')
    chapterContent = soup.find("div", {"class": "chapter-inner chapter-content"})
    if chapterContent is None:
        logging.warning(f"Could not find chapter content for URL: {chapterURL}")
    return chapterContent#.encode('ascii')
    
    
    
#Get the chapter ID and title.
def extract_chapter_ID(chapterURL):
    chapter=chapterURL.split("/")
    return chapter[len(chapter)-2]

def extract_chapter_title(string):
    extractedTitle=re.sub('.html','',string)
    extractedTitle=extractedTitle.split("/")
    return extractedTitle[len(extractedTitle)-1]
    
    
def get_existing_order_of_contents(bookTitle):
    dirLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
    if (check_directory_exists(dirLocation)):
        f= open(dirLocation,"r")
        return f.readlines()
    else:
        return False
        
        

def write_order_of_contents(bookTitle, chapterData):
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
        if chapterID == chapter[0]:
            return chapter[0],chapter[2].replace("\n","")
        
    return -1,-1
    
def get_chapter_contents_from_saved(dirLocation):
    f=open(dirLocation,"r")
    
    return f.read()

def generate_Epub_Based_On_Stored_Order(new_epub, bookTitle):
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    
    tocList=list()
    for url in already_saved_chapters:
        url=url.split(";")
        chapterID=url[0]
        fileChapterTitle=extract_chapter_title(url[len(url)-1])
        dirLocation=url[len(url)-1]
        chapterContent=get_chapter_contents_from_saved(dirLocation).encode("utf-8")
        
        strippedTitle=fileChapterTitle.split('-')
        strippedTitle=strippedTitle[len(strippedTitle)-1].strip()
        
        chapter=epub.EpubHtml(title=strippedTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
        chapter.set_content(chapterContent)
        
        
        tocList.append(chapter)
        
        new_epub.add_item(chapter)
    
    new_epub.toc=tocList
    storeEpub(bookTitle,new_epub)
    
        
def generate_Epub_Based_On_Online_Order(new_epub,novelURL,bookTitle):
    
    
    tocList=list()
    for url in fetchChapterList(novelURL):
        chapterID=extract_chapter_ID(url)
        chapterTitle=fetchChapterTitle(url)
        fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
        chapterContent=fetchChapter(url)
        
        
        chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
        chapter.set_content(chapterContent)
        
        tocList.append(chapter)
        
        new_epub.add_item(chapter)
        
        time.sleep(0.5)
    new_epub.toc=tocList
    storeEpub(bookTitle,new_epub)
    

def save_images_in_chapter(img_urls,saveDirectory,imageCount):
    if not (check_directory_exists(saveDirectory)):
        make_directory(saveDirectory)
    for image in img_urls:
        imageDir=f"{saveDirectory}image_{imageCount}.jpg"
        if not (check_directory_exists(imageDir)):
            response=requests.get(image,stream=True, headers = {'User-agent': 'Image Bot'})
            time.sleep(0.5)
            imageCount+=1
            if response.ok:
                response=response.content
                with open (imageDir,'wb') as f:
                    f.write(response)
                f.close()
    return imageCount

def retrieve_stored_image(imageDir):
    if os.path.exists(imageDir):
        return Image.open(imageDir)
    else:
        logging.warning(f"Image file not found: {imageDir}")
    return None

def produceEpub(new_epub,novelURL,bookTitle):
    
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    chapterMetaData=list()
    
    tocList=list()
    
    imageCount=0
    
    logging.warning(fetchChapterList(novelURL))
    for url in fetchChapterList(novelURL):
        chapterID=extract_chapter_ID(url)
        chapterTitle=fetchChapterTitle(url)
        logging.warning(url)
        if (already_saved_chapters is False):
            fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
            chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{fileChapterTitle}.html"])
            chapterContent=fetchChapter(url)
            
            if chapterContent:
                images=chapterContent.find_all('img')
                images=[image['src'] for image in images]
            else:
                logging.warning("chapterContent is None")

            imageDir=f"./books/raw/{bookTitle}/images/"
            currentImageCount=imageCount
            #logging.warning(images)
            if (images):
                imageCount=save_images_in_chapter(images,imageDir,imageCount)
            for img,image in zip(chapterContent.find_all('img'),images):
                img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.jpg")
                
                imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.jpg"
                epubImage=retrieve_stored_image(imageDir)
                b=io.BytesIO()
                epubImage.save(b,'jpeg')
                b_image1=b.getvalue()
                
                image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.jpg', media_type='image/jpg', content=b_image1)
                new_epub.add_item(image_item)
                currentImageCount+=1
            chapterContent=chapterContent.encode('ascii')
            store_chapter(chapterContent,bookTitle,chapterTitle,chapterID)
            
        elif (check_if_chapter_exists(chapterID,already_saved_chapters)):
            chapterID,dirLocation=get_chapter_from_saved(chapterID,already_saved_chapters)
            chapterContent=get_chapter_contents_from_saved(dirLocation)
            fileChapterTitle=extract_chapter_title(dirLocation)
            images=re.findall(r'<img\s+[^>]*src="([^"]+)"[^>]*>',chapterContent)
            
            currentImageCount=imageCount
            for image in images:
                imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.jpg"
                epubImage=retrieve_stored_image(imageDir)
                b=io.BytesIO()
                epubImage.save(b,'jpeg')
                b_image1=b.getvalue()
                
                image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.jpg', media_type='image/jpg', content=b_image1)
                new_epub.add_item(image_item)
                currentImageCount+=1
            chapterContent=chapterContent.encode("utf-8")
        chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
        chapter.set_content(chapterContent)
            
        tocList.append(chapter)
        new_epub.add_item(chapter)
        time.sleep(0.5)
    
    logging.warning("We reached produceEpub")
    img1=retrieve_cover_from_storage(bookTitle)
    b=io.BytesIO()
    img1.save(b,'jpeg')
    b_image1=b.getvalue()
    
    image1_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.jpeg', media_type='image/jpeg', content=b_image1)
    new_epub.add_item(image1_item)
    
    new_epub.toc=tocList
    new_epub.spine=tocList
    new_epub.add_item(epub.EpubNcx())
    new_epub.add_item(epub.EpubNav())
    #NCX and Navigation Tile is needed.
    #DEFINITELY NEEDS A Spine.
    
    if (already_saved_chapters is False):
        write_order_of_contents(bookTitle, chapterMetaData)
    
    logging.warning("Attempting to store epub")
    storeEpub(bookTitle,new_epub)

def retrieve_cover_from_storage(bookTitle):
    dirLocation=f"./books/raw/{bookTitle}/cover_image.jpg"
    return Image.open(dirLocation)


def storeEpub(bookTitle,new_epub):
    dirLocation="./epubs/"+bookTitle
    if not check_directory_exists(dirLocation):
        make_directory(dirLocation)
    
    dirLocation="./epubs/"+bookTitle+"/"+bookTitle+".epub"
    if (check_directory_exists(dirLocation)):
        os.remove(dirLocation)
    epub.write_epub(dirLocation,new_epub)

def store_chapter(content, bookTitle, chapterTitle, chapterID):
    # Remove invalid characters from file name
    bookTitle = remove_invalid_characters(bookTitle)
    chapterTitle = remove_invalid_characters(chapterTitle)
        
    # Check if the folder for the book exists
    bookDirLocation = "./books/raw/" + bookTitle
    if not check_directory_exists(bookDirLocation):
        make_directory(bookDirLocation)

    # Check if the chapter already exists
    title = f"{bookTitle} - {chapterID} - {chapterTitle}"
    dirLocation = f"./books/raw/{bookTitle}/{title}.html"
    if check_directory_exists(dirLocation):
        return

    # Write the chapter content to the file with UTF-8 encoding
    chapterDirLocation = "./books/raw/" + bookTitle + "/"
    completeName = os.path.join(chapterDirLocation, f"{title}.html")
    with open(completeName, "w", encoding="utf-8") as f:
        if not isinstance(content, str):
            content = content.decode("utf-8")  # Decode bytes to string if necessary
        f.write(content)

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
    lastChapterID=lines[len(lines)-1].split(";")[0]
    
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





#https://github.com/aerkalov/ebooklib/issues/194
#Do this to embed images into the epub.
#Will need to have a counter as the html files are being stored.
#So that image_01 -> image_02 -> image_03
#DONE #Will also need to replace the src="link here" to src="images/image_01.jpg" while chapters are being stored.
#DONE #Will need to store the images into the raw epub folder.
#DONE #Will need to add_item(image_01) into the epub each time.




#Will need to write a css sheet for tables.
#Set base text to black
#Set table text to white




#Aside from Royalroad, write scrape functions for Spacebattles, Fanfiction.net, NovelCool(Aggregators)

#ToDO:Also scrape from raw websites, feed into google translate or AI translate api, then store.




#Main call interface.
def mainInterface(novelURL):
    bookurl=re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/[0-9]+/",novelURL)
    
    if (bookurl is None):
        return False
    
    
    bookurl=bookurl.group()
    bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter=fetchNovelData(bookurl)
    
    if(check_latest_chapter(bookID,bookTitle,latestChapter)):
        directory=getEpub(bookID)
    else:
        save_cover_image("cover_image",novelURL,f"./books/raw/{bookTitle}")
        new_epub=epub.EpubBook()
        new_epub.set_identifier(bookID)
        new_epub.set_title(bookTitle)
        new_epub.set_language('en')
        new_epub.add_author(bookAuthor)
        produceEpub(new_epub,bookurl,bookTitle)

        
        
        rooturl = re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/", novelURL)
        rooturl = rooturl.group()
        first,last,total=get_first_last_chapter(bookTitle)
        
        bookID=remove_invalid_characters(bookID)
        directory = create_epub_directory_url(bookTitle)
        create_Entry(
            bookID=int(bookID),
            bookName=bookTitle,
            bookAuthor=bookAuthor,
            bookDescription=description,
            websiteHost=rooturl,
            firstChapter=first,
            lastChapter=last,
            totalChapters=total,
            directory=directory
        )
    
    return directory
    
    #pass
    #check to see if epub already exists
    #check if new chapter was published for given book
    
    #if yes, update epub.
    #if no, return current epub.

    #implement store order of chapters



#Requires 9 inputs. BookID, bookName, bookAuthor, bookDescription, WebsiteHost, firstChapter#, lastChapter#, totalChapters, directory
def create_Entry(**kwargs):
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
#mainInterface("https://www.royalroad.com/my/follows")
mainInterface("https://www.royalroad.com/fiction/54046/final-core-a-holy-dungeon-core-litrpg")


@app.get("/")
def read_root():
    return {"Hello": "World"}
