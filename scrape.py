import bs4
import requests
import re
from pathlib import Path
from pymongo import MongoClient
import os, errno
import datetime
from novel_template import NovelTemplate
import logging
import time
import asyncio
import io
from ebooklib import epub 
from PIL import Image
import aiohttp


#Figure out how to swap tables text color in epub.

MONGODB_URL=os.getenv('MONGODB_URI')
myclient=MongoClient(MONGODB_URL)
mydb=myclient["Webnovels"]
savedBooks=mydb["Books"]




# url="https://www.royalroad.com/fiction/55927/"
# rooturl=re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/",url)
# rooturl=rooturl.group()



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
def check_existing_book_Title(bookTitle):
    results=savedBooks.find_one({"bookName":bookTitle})
    if (results==None):
        return False
    return True

def RoyalRoad_Fetch_Novel_Data(novelURL):
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
    
    img_url = soup.find("div",{"class":"cover-art-container"}).find("img")
    saveDirectory=f"./books/raw/{bookTitle}/"
    if not (check_directory_exists(f"./books/raw/{bookTitle}/cover_image.png")):
        response =requests.get(img_url["src"],stream=True)
        if not response.ok:
            pass
        else:
            fileNameDir=f"{saveDirectory}cover_image.png"
            if not (check_directory_exists(saveDirectory)):
                make_directory(saveDirectory)
            if not (check_directory_exists(fileNameDir)):
                response=response.content
                with open (fileNameDir,'wb') as f:
                    f.write(response)
                f.close()
    #print(description)
    return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID


def RoyalRoad_Fetch_Chapter_List(novelURL):
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

    
def RoyalRoad_Fetch_Chapter(chapterURL):
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
    logging.warning(dirLocation)
    if (check_directory_exists(dirLocation)):
        f=open(dirLocation,"r")
        chapters=f.readlines()
        #logging.warning(chapters)
        return chapters
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
        #logging.warning(dataLine)
        chapterID=dataLine[0]
        chapterLink=dataLine[1]
        chapterTitle=dataLine[2]
        f.write(chapterID+";"+chapterLink+";"+chapterTitle+"\n")
    f.close()


def fetch_Chapter_Title(soup):
    if not (isinstance(soup, bs4.BeautifulSoup)):
        soup=bs4.BeautifulSoup(requests.get(soup).text, 'html.parser')
    chapterTitle=soup.find("h1").get_text()
    return chapterTitle

def remove_non_english_characters(text):
    result=re.search(r'([A-Za-z0-9]+( [A-Za-z0-9]+)+)',text)
    if not result:
        return text
    return result.group() 

def remove_invalid_characters(inputString):
    invalid_chars = '<>:;"/\\|?*'
    for char in invalid_chars:
        inputString=inputString.replace(char,'')
    inputString=re.sub(r"[\(\[].*?[\)\]]", "", inputString)
    inputString=inputString.strip()
    inputString=remove_non_english_characters(inputString)
    return inputString


def check_if_chapter_exists(chapterID,savedChapters):
    if (savedChapters is False):
        return False
    for chapter in savedChapters:
        if chapterID in chapter:
            return True
    return False

#Returns ChapterID and chapter file name
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
    for url in RoyalRoad_Fetch_Chapter_List(novelURL):
        chapterID=extract_chapter_ID(url)
        chapterTitle=fetch_Chapter_Title(url)
        fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
        chapterContent=RoyalRoad_Fetch_Chapter(url)
        
        
        chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
        chapter.set_content(chapterContent)
        
        tocList.append(chapter)
        
        new_epub.add_item(chapter)
        
        asyncio.sleep(0.5)
    new_epub.toc=tocList
    storeEpub(bookTitle,new_epub)
    

def save_images_in_chapter(img_urls,saveDirectory,imageCount):
    if not (check_directory_exists(saveDirectory)):
        make_directory(saveDirectory)
    for image in img_urls:
        imageDir=f"{saveDirectory}image_{imageCount}.png"
        if not (check_directory_exists(imageDir)):
            response=requests.get(image,stream=True, headers = {'User-agent': 'Image Bot'})
            asyncio.sleep(0.5)
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

def produceEpub(new_epub,novelURL,bookTitle,css):
    
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    chapterMetaData=list()
    
    #logging.warning(already_saved_chapters)
    tocList=list()
    
    imageCount=0
    
    #logging.warning(RoyalRoad_Fetch_Chapter_List(novelURL))
    for url in RoyalRoad_Fetch_Chapter_List(novelURL):
        chapterID=extract_chapter_ID(url)
        chapterTitle=fetch_Chapter_Title(url)
        #logging.warning(url)
        if (check_if_chapter_exists(chapterID,already_saved_chapters)):
            #logging(check_if_chapter_exists(chapterID,already_saved_chapters))
            chapterID,dirLocation=get_chapter_from_saved(chapterID,already_saved_chapters)
            chapterContent=get_chapter_contents_from_saved(dirLocation)
            fileChapterTitle=extract_chapter_title(dirLocation)
            images=re.findall(r'<img\s+[^>]*src="([^"]+)"[^>]*>',chapterContent)
            
            currentImageCount=imageCount
            for image in images:
                imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
                epubImage=retrieve_stored_image(imageDir)
                b=io.BytesIO()
                epubImage.save(b,'png')
                b_image1=b.getvalue()
                
                image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
                new_epub.add_item(image_item)
                currentImageCount+=1
            chapterContent=chapterContent.encode("utf-8")
        else:
            
            asyncio.sleep(0.5)
            fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
            #logging.warning(fileChapterTitle)
            chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{fileChapterTitle}.html"])
            chapterContent=RoyalRoad_Fetch_Chapter(url)
            
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
                img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")
                
                imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
                epubImage=retrieve_stored_image(imageDir)
                b=io.BytesIO()
                epubImage.save(b,'png')
                b_image1=b.getvalue()
                
                image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
                new_epub.add_item(image_item)
                currentImageCount+=1
            chapterContent=chapterContent.encode('ascii')
            store_chapter(chapterContent,bookTitle,chapterTitle,chapterID)
            
        
            
        #logging.warning(fileChapterTitle)
        chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
        chapter.set_content(chapterContent)
        chapter.add_item(css)
        tocList.append(chapter)
        new_epub.add_item(chapter)
    
    logging.warning("We reached produceEpub")
    img1=retrieve_cover_from_storage(bookTitle)
    b=io.BytesIO()
    img1.save(b,'png')
    b_image1=b.getvalue()
    
    image1_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image1)
    new_epub.add_item(image1_item)
    
    new_epub.toc=tocList
    new_epub.spine=tocList
    new_epub.add_item(epub.EpubNcx())
    new_epub.add_item(epub.EpubNav())
    
    if (already_saved_chapters is False or not already_saved_chapters):
        write_order_of_contents(bookTitle, chapterMetaData)
    
    logging.warning("Attempting to store epub")
    storeEpub(bookTitle,new_epub)

def retrieve_cover_from_storage(bookTitle):
    dirLocation=f"./books/raw/{bookTitle}/cover_image.png" #or 
    if os.path.exists(dirLocation):
        try:
            return Image.open(dirLocation)
        except Exception as e:
            logging.warning(f"Failed to open image: {e}")
            return None
    else:
        dirLocation=f"./books/raw/{bookTitle}/cover_image.png"
        try:
            return Image.open(dirLocation)
        except Exception as e:
            logging.warning(f"Failed to open image: {e}")
            return None
    

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
    if is_empty(lines):
        return -1,-1,-1
    firstChapterID=lines[0].split(";")[0]
    lastChapterID=lines[len(lines)-1].split(";")[0]
    
    return firstChapterID,lastChapterID,len(lines)

def is_empty(chapterList):
    if not chapterList:
        return True
    return False

#Return existing epub directory if the latest chapter is already stored.
def getEpub(bookID):
    results=savedBooks.find_one({"bookID":bookID})
    directory=results["directory"]
    return directory

def get_Entry_Via_Title(bookTitle):
    results = savedBooks.find_one({"bookID": {"$ne": -1}, "bookName": bookTitle})
    if not results:
        return None
    return results

def check_latest_chapter(bookID,bookTitle,latestChapter):
    bookData=get_Entry_Via_ID(bookID)
    if (bookData is None):
        return False
    if (bookData["lastChapter"]==latestChapter):
        return True
    elif (bookData["lastChapter"]<=latestChapter):
        #update epub
        return False
    return True



#Requires 10 inputs. BookID, bookName, bookAuthor, bookDescription, WebsiteHost, firstChapter#, lastChapter#, totalChapters, directory
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
    logging.warning(f"book_data['bookID']: {book_data['bookID']}")
    logging.warning(book_data["bookID"])
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
    
    
    logging.warning(book)
    logging.warning(check_existing_book_Title(book_data["bookName"]))
    logging.warning(check_existing_book(book_data["bookID"]))
    if (check_existing_book(book_data["bookID"]) and check_existing_book_Title(book_data["bookName"])):
        result=savedBooks.replace_one({"bookID": book_data["bookID"]}, book)
        logging.warning(f"Replaced book: {result}")
    else:
        result = savedBooks.insert_one(book)
        logging.warning(f"Inserted book: {result}")

def create_latest(**kwargs):
        default_values = {
            "bookID": -1,
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
            "bookID": -1,
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
        
        if (check_existing_book(-1)):
            savedBooks.replace_one({"bookID": -1}, book)
        else:
            savedBooks.insert_one(book)

#Retrieve book data from MongoDB
def get_Entry_Via_ID(bookID):
    results=savedBooks.find_one({"bookID":bookID})
    return results
#Retrieve latest book data from MongoDB
def getLatest():
    result=savedBooks.find_one({"bookID":-1})
    logging.warning(result)
    return result

def get_Total_Books():
    result=savedBooks.count_documents({})
    return result-2

def getAllBooks():
    result=savedBooks.find({"bookID": {"$ne": -1}}).to_list(length=None)
    now=datetime.datetime.now()
    result=[[result["bookID"],result["bookName"],(result["lastScraped"]).strftime('%m/%d/%Y'),result["lastChapter"]] for result in result]
    return result


def update_existing_order_of_contents(bookTitle,chapterList):
    bookDirLocation=f"./books/raw/{bookTitle}"
    if not (check_directory_exists(bookDirLocation)):
        make_directory(bookDirLocation)
    fileLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
    if (os.path.exists(fileLocation)):
        f=open(fileLocation,"w")
    else:
        f=open(fileLocation,"x")
    for line in chapterList:
        f.write(str(line)) #FORMATTING IS FUCKED
    f.close()
    
    

#Cut out and insert function
#Take [range1:range2] from the chapterList and insert into position [insertRange1] of existingChapterList
def insert_into_Chapter_List(cutOutRange,insertRange,chapterList,existingChapterList):
    
    if (cutOutRange[0]<= cutOutRange[1]):
        logging.warning("Invalid range")
        return False
    if (cutOutRange[0] >=len(existingChapterList or cutOutRange[1]>=len(existingChapterList))):
        logging.warning("Out of bounds error")
        return False
    if (insertRange>=len(existingChapterList) or insertRange<0):
        logging.warning("Insert range out of bounds")
        return False
    if (existingChapterList):
        logging.warning("Existing chapter list is empty")
        return False
    
    #Get the desired chapters to cut out from "chapterList" of the new file to be inserted into the saved existingChapterList.
    cutOutChapters=chapterList[cutOutRange[0]:cutOutRange[1]]
    
    #Split the existing chapterList in half to insert
    firstHalfChapters=existingChapterList[0:insertRange]
    secondHalfChapters=existingChapterList[insertRange:]
    
    #Create new chapterlist, insert the cutout in
    newChapterList=list()
    newChapterList=firstHalfChapters+cutOutChapters+secondHalfChapters
    return newChapterList



        
def delete_from_Chapter_List(deleteRange,existingChapterList):
    if (deleteRange[0]<= deleteRange[1]):
        logging.warning("Invalid range")
        return False
    if (deleteRange[0] >=len(existingChapterList or deleteRange[1]>=len(existingChapterList))):
        logging.warning("Out of bounds error")
        return False
    
    cutOutChapters=existingChapterList[deleteRange[0]:deleteRange[1]]
    for item in cutOutChapters:
        existingChapterList.remove(item)
    newChapterList=existingChapterList
    return newChapterList
    




#TODO: Fuzzy search for if input is not link. If input is Title, send query, get results.

#API:https://www.royalroad.com/fictions/search?globalFilters=false&title=test&orderBy=popularity
#https://www.royalroad.com/fictions/search?globalFilters=false&title=test
#Two versions. Popularity, and Relevance.
#Relevance to get best possible match.
#Popularity for when results have similar names.


#div class="fiction-list"
#div class= "row fiction-list-item"
#h2 class="fiction-title"
#a href format="/fiction/#####/title"


#option takes two values 0 or 1. 0 for relevance. 1 for popularity.
def query_royalroad(title, option):
    if (title.isspace() or title==""):
        return "Invalid Title"
        
    if (option ==0):
        querylink = f"https://www.royalroad.com/fictions/search?globalFilters=false&title={title}"
    elif (option==1):
        querylink = f"https://www.royalroad.com/fictions/search?globalFilters=false&title={title}&orderBy=popularity"
    else:
        return ("Invalid Option")

    
    soup = bs4.BeautifulSoup(requests.get(querylink).text, 'html.parser')
    resultTable=soup.find("div",{"class":"fiction-list"})
    bookTable=resultTable.find("h2",{"class":"fiction-title"})
    bookRows=bookTable.find_all("a")
    firstResult=bookRows[0]['href']

    #formatting
    resultLink=f"https://www.royalroad.com{firstResult}"
    
    return resultLink

#logging.warning(query_royalroad("Pokemon",1))

def is_valid_url(url):
    regex = re.compile(
        r'^(https?:\/\/)?'  # Optional http or https
        r'([a-zA-Z0-9.-]+)'  # Domain name
        r'(\.[a-zA-Z]{2,})'  # Top-level domain
        r'(\/[^\s]*)?$'  # Optional path
    )
    return re.match(regex, url) is not None



#Aside from Royalroad, write scrape functions for Spacebattles, Novelbin, Lightnovelpub, Foxaholic (Not possible), Fanfiction.net, NovelCool(Aggregators)

#ToDO:Also scrape from raw websites, feed into google translate or AI translate api, then store.
#Spacebattles: https://github.com/imgurbot12/pypub/blob/master/examples/spacebattles.py

#  "authority": "www.google.com",
#     "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
#     "accept-language": "en-US,en;q=0.9",
#     "cache-control": "max-age=0",
#     'User-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0'

#Main call interface.
async def mainInterface(novelURL):
    #Check if valid url first.
    isUrl=is_valid_url(novelURL)
    if (isUrl is False):
        searchTerm=novelURL
        novelURL=query_royalroad(searchTerm,0)
        #shorten url
        novelURL=re.search("https://www.royalroad.com/fiction/[0-9]+/",novelURL)
        novelURL=novelURL.group()
    else:
        #Then check if it is something I can scrape. 
        #If it is not a royalroad URL, then return false and stop.
        royalroadUrl=re.search("https://www.royalroad.com/fiction/[0-9]+/",novelURL)
        #logging.warning(royalroadUrl)
        if (royalroadUrl is None):
            return False
        novelURL=royalroadUrl.group()
    
    bookurl=novelURL
    logging.warning(bookurl)
    bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter=RoyalRoad_Fetch_Novel_Data(bookurl)
    #logging.warning(bookID, bookTitle, latestChapter)
    if (check_latest_chapter(bookID,bookTitle,latestChapter)):
        pass
        #directory=getEpub(bookID)
    else:
        logging.warning("Doing else")
        #save_cover_image("cover_image",novelURL,f"./books/raw/{bookTitle}")
        new_epub=epub.EpubBook()
        new_epub.set_identifier(bookID)
        new_epub.set_title(bookTitle)
        new_epub.set_language('en')
        new_epub.add_author(bookAuthor)
        style=open("style.css","r").read()
        default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)

        new_epub.add_item(default_css)
        produceEpub(new_epub,bookurl,bookTitle,default_css)

        
        
        rooturl = re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/", novelURL)
        rooturl = rooturl.group()
        first,last,total=get_first_last_chapter(bookTitle)
        
        bookID=int(remove_invalid_characters(bookID))
        #logging.warning(bookID)
        directory = create_epub_directory_url(bookTitle)
        create_Entry(
            bookID=bookID,
            bookName=bookTitle,
            bookAuthor=bookAuthor,
            bookDescription=description,
            websiteHost=rooturl,
            firstChapter=first,
            lastChapter=last,
            totalChapters=total,
            directory=directory
        )
        
        create_latest(
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

#asyncio.run(mainInterface("https://www.royalroad.com/fiction/54046/final-core-a-holy-dungeon-core-litrpg"))
#asyncio.run(mainInterface("https://Test.com"))
#asyncio.run(mainInterface("Final Core"))


#mainInterface("https://www.royalroad.com/my/follows")
#mainInterface("https://www.royalroad.com/fiction/54046/final-core-a-holy-dungeon-core-litrpg")

#logging.warning(getAllBooks())


#TODO: Create a epub function that generates from links, and existing file retrievals if link isn't available

#https://github.com/aerkalov/ebooklib/issues/194
#Do this to embed images into the epub.
#Will need to have a counter as the html files are being stored.
#So that image_01 -> image_02 -> image_03
#DONE #Will also need to replace the src="link here" to src="images/image_01.png" while chapters are being stored.
#DONE #Will need to store the images into the raw epub folder.
#DONE #Will need to add_item(image_01) into the epub each time.




#DONE Will need to write a css sheet for tables.
#DONE Set base text to black
#DONE Set table text to white



#Impossible due to Cloudflare protection.
#from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from seleniumwire import webdriver

link="https://www.foxaholic.com/novel/koukyuu-no-karasu/"
cookie="cf_clearance=0hmTQCcfRP_WisLpGzckJTs5AAzgFehE1KxgC8D1cRY-1744729214-1.2.1.1-Im4sknw0ZrCvEkM9LdG.VoLyU.pe.MDPSXZpZilkOZNyTTcXRwmQeoDFBHrpUm6832BTS2wsyaV13AWtB4.Z7ERFeJGhZHiqdmBV9oJ0fq57AH3ZrlXm2aSm3Rn.jgX2FaTLpZ5IcbgFiNhK3T3.iX6z673eRkWA1m.nwe4yluh7xCWmYSM2ndgIEiskmHsr4xdhFH9GeD.ZXHPaCYcCVe_fpnDHr3scpMeDqyCNrb3_y2rv1xM1Y5S.VozKduLwLOSMRW4asdhr0DSCWgSR0Cf5ibYMFKjIR90QX_PE3qhoPwE12lHOBCvasKlAt.U7XB_I34Xf1e.zLwAGX.sE4do5L0zePXs7s8bw4RNSjHT0Kz4BKalDN.E_F4VmZ7W4"



def foxaholic_driver_selenium(url,cookie):
    driver = webdriver.Firefox()
    options={
        #"Host": "www.foxaholic.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        #"Referer": "https://www.foxaholic.com/",
        #Foxaholic requires cookie. Will need to get new cookie each time.
        "Cookie": cookie
    }
    def interception (request):
        del request.headers['User-Agent']
        del request.headers['Accept']
        del request.headers['Accept-Language']
        del request.headers['Accept-Encoding']
        #del request.headers['Referer']
        del request.headers['Cookie']
        
        request.headers['User-Agent']=options["User-Agent"]
        request.headers['Accept']=options["Accept"]
        request.headers['Accept-Language']=options["Accept-Language"]
        request.headers['Accept-Encoding']=options["Accept-Encoding"]
        #request.headers['Referer']=options["Referer"]
        request.headers['Cookie']=options["Cookie"]
    driver.request_interceptor=interception
    driver.get(url)
    soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
    driver.close()
    return soup


def foxaholic_get_chapter_list(url,cookie):
    #https://www.codecademy.com/article/web-scrape-with-selenium-and-beautiful-soup
    soup = foxaholic_driver_selenium(url,cookie)
    
    #logging.warning(soup)
    chapterTable = soup.find_all("ul",class_='main version-chap no-volumn')[0]
    #logging.warning(chapterTable)
    rows= chapterTable.find_all("li", {"class":"wp-manga-chapter free-chap"})
    chapterListURL=list()
    for row in rows[1:len(rows)]:
        chapterData={}
        chapterData["name"]=row.find("a").contents[0].strip()
        processChapterURL=row.find("a")["href"]
                    
        chapterURL=processChapterURL
        chapterListURL.append(chapterURL)
    chapterListURL=list(reversed(chapterListURL))
    #logging.warning(chapterListURL)
    return chapterListURL

#asyncio.run(foxaholic_get_chapter_list(link,cookie))



def foxaholic_scrape_chapter_page(soup):
    pageContent=soup.find_all("div",{"class":"reading-content"})[0]
    chapterContent=pageContent.find_all("p")
    
    chapterContent=re.sub('<p>\\s+</p>,','',str(chapterContent))
    chapterContent=re.sub('</p>,','</p>',str(chapterContent))
    
    if (chapterContent.startswith('[')):
        chapterContent=chapterContent[1:]
    if (chapterContent.endswith(']')):
        chapterContent=chapterContent[:-1]
    
    return bs4.BeautifulSoup(chapterContent,'html.parser')



def generate_new_ID(bookTitle):
    logging.warning(check_existing_book_Title(bookTitle))
    if (check_existing_book_Title(bookTitle)):
        bookData=get_Entry_Via_Title(bookTitle)
        if bookData:
            return bookData["bookID"]
    return get_Total_Books()+1

def foxaholic_Fetch_Novel_Data(novelURL,cookie):
    soup=foxaholic_driver_selenium(novelURL,cookie)
    
    bookData=soup.find("div",{"class":"post-content"})
    novelData=bookData.find_all("div",{"class":"summary-content"}) or bookData.find_all("div",{"class":"summary_content"})

    bookTitle=soup.find("div",{"class":"post-title"}).get_text() or soup.find("div",{"class":"post_title"}).get_text()
    bookAuthor=novelData[2].get_text()
    logging.warning(bookTitle)
    bookTitle=remove_invalid_characters(bookTitle)
    
    bookID=str(generate_new_ID(bookTitle))
    logging.warning(bookID)
            
    descriptionBox=soup.find("div",{"class":"description-summary"})
    description=descriptionBox.find("div",{"class":"summary__content"}).get_text()

    if (description.startswith("Description: ")):
        description=description[13:]
    
    location1=re.search("translator",description ,re.IGNORECASE)
    if not location1:
        location1=len(description)
    else:
        location1=location1.start()
    location2=re.search("release schedule",description,re.IGNORECASE)
    if not location2:
        location2=len(description)
    else:
        location2=location2.start()
    location3=re.search('editor',description,re.IGNORECASE)
    if not location3:
        location3=len(description)
    else:
        location3=location3.start()

    location=min(location1,location2,location3)
    description=description[:location].strip()

    logging.warning(description)
    lastScraped=datetime.datetime.now()
    chapterTable = soup.find_all("ul",class_='main version-chap no-volumn')[0]
    rows= chapterTable.find_all("li", {"class":"wp-manga-chapter free-chap"})
    
    latestChapter=rows[0]
    latestChapterID=latestChapter.find("a")["href"].split("/")
    latestChapterID=latestChapterID[len(latestChapterID)-2]
    latestChapterID=re.search(r'[0-9]+',latestChapterID).group()
    
    img_url = soup.find("div",{"class":"summary_image"}).find("img")
    
    if not (check_directory_exists(f"./books/raw/{bookTitle}/cover_image.png")):
        foxaholic_save_cover_image("cover_image",img_url,f"./books/raw/{bookTitle}",cookie)
    
    return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID


#Obsolete. Foxaholic does not have a working search api.
def foxaholic_query(title,cookie):
    if (title.isspace() or title==""):
        return "Invalid Title"
    
    querylink = f"https://www.foxaholic.com/?s={title}"

    soup=foxaholic_driver_selenium(querylink,cookie)
    
    resultTable=soup.find("div",{"class":"tab-content-wrap"})
    bookTable=resultTable.find("h4",{"class":"heading"})
    bookRows=bookTable.find("a")
    firstResult=bookRows['href']

    #formatting
    resultLink=f"https://www.royalroad.com{firstResult}"
    
    return resultLink

def foxaholic_save_cover_image(title,img_url,saveDirectory,cookie):
    driver = webdriver.Firefox()
    options={
        #"Host": "www.foxaholic.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        #"Referer": "https://www.foxaholic.com/",
        #Foxaholic requires cookie. Will need to get new cookie each time.
        "Cookie": cookie
    }
    def interception (request):
        del request.headers['User-Agent']
        del request.headers['Accept']
        del request.headers['Accept-Language']
        del request.headers['Accept-Encoding']
        #del request.headers['Referer']
        del request.headers['Cookie']
        
        request.headers['User-Agent']=options["User-Agent"]
        request.headers['Accept']=options["Accept"]
        request.headers['Accept-Language']=options["Accept-Language"]
        request.headers['Accept-Encoding']=options["Accept-Encoding"]
        #request.headers['Referer']=options["Referer"]
        request.headers['Cookie']=options["Cookie"]
    driver.request_interceptor=interception
    driver.get(img_url["src"])
    image=driver.find_element(By.CSS_SELECTOR, 'img')
    
    if (saveDirectory.endswith("/")):
        fileNameDir=f"{saveDirectory}{title}.png"
    else:
        fileNameDir=f"{saveDirectory}/{title}.png"
    if image:
        if not (check_directory_exists(saveDirectory)):
            make_directory(saveDirectory)
        if not (check_directory_exists(fileNameDir)):
            with open (fileNameDir,'wb') as f:
                f.write(image.screenshot_as_png)
            f.close()
    driver.close()


#foxaholic_save_cover_image("cover_image",link,f"./books/raw/Hikikomori VTuber Wants to Tell You Something",cookie)

def foxaholic_fetch_Chapter_Title(soup):
    chapterTitle=soup.find('div',{"class":"reading-content"})
    chapterTitle=chapterTitle.find("h1")

    if chapterTitle:
        chapterTitle=chapterTitle.get_text()
    else:
        chapterTitle=soup.find('ol',{"class":"breadcrumb"})
        chapterTitle=chapterTitle.find("li",{"class":"active"}).get_text()
        if (" - " in chapterTitle):
            chapterTitle=chapterTitle.split(" - ")[1]
        elif (": " in chapterTitle):
            chapterTitle.split(": ")[1]
    chapterTitle=remove_invalid_characters(chapterTitle)
    return chapterTitle

def foxaholic_produce_Epub(new_epub,novelURL,bookTitle,css,cookie):
    
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    chapterMetaData=list()
    
    tocList=list()
    
    imageCount=0
    
    logging.warning(novelURL)
    for url in foxaholic_get_chapter_list(novelURL,cookie):
        logging.warning (url)
        chapterID=url.split("/")
        chapterID=chapterID[len(chapterID)-2]
        chapterID=re.search(r'\d+',chapterID).group()
        
        if (check_if_chapter_exists(chapterID,already_saved_chapters)):
            chapterID,dirLocation=get_chapter_from_saved(chapterID,already_saved_chapters)
            chapterContent=get_chapter_contents_from_saved(dirLocation)
            fileChapterTitle=extract_chapter_title(dirLocation)
            #logging.warning(fileChapterTitle)
            
            chapterTitle=fileChapterTitle.split('-')
            chapterTitle=chapterTitle[len(chapterTitle)-1]
            
            images=re.findall(r'<img\s+[^>]*src="([^"]+)"[^>]*>',chapterContent)
            currentImageCount=imageCount
            for image in images:
                imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
                epubImage=retrieve_stored_image(imageDir)
                b=io.BytesIO()
                epubImage.save(b,'png')
                b_image1=b.getvalue()
                
                image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
                new_epub.add_item(image_item)
                currentImageCount+=1
            chapterContent=chapterContent.encode("utf-8")
        
        else:
            time.sleep(0.5)
            soup = foxaholic_driver_selenium(url,cookie)
            chapterTitle=foxaholic_fetch_Chapter_Title(soup)
            fileChapterTitle = f"{bookTitle} - {chapterID} - {chapterTitle}"
            #logging.warning(fileChapterTitle)
            chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{fileChapterTitle}.html"])
            chapterContent=foxaholic_scrape_chapter_page(soup)
            
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
                img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")
                
                imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
                epubImage=retrieve_stored_image(imageDir)
                b=io.BytesIO()
                epubImage.save(b,'png')
                b_image1=b.getvalue()
                
                image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
                new_epub.add_item(image_item)
                currentImageCount+=1
            chapterContent=chapterContent.encode('ascii')
            store_chapter(chapterContent,bookTitle,chapterTitle,chapterID)
        
        logging.warning(fileChapterTitle)
        chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
        chapter.set_content(chapterContent)
        chapter.add_item(css)
        tocList.append(chapter)
        new_epub.add_item(chapter)
    
    logging.warning("We reached produceEpub")
    img1=retrieve_cover_from_storage(bookTitle)
    if img1:    
        b=io.BytesIO()
        try:
            img1.save(b,'png')
            b_image1=b.getvalue()
            image1_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image1)
            new_epub.add_item(image1_item)
        except Exception as e:
            logging.warning(f"Failed to save image:{e}")
    
    
    
    new_epub.toc=tocList
    new_epub.spine=tocList
    new_epub.add_item(epub.EpubNcx())
    new_epub.add_item(epub.EpubNav())
    
    if (already_saved_chapters is False or not already_saved_chapters):
        write_order_of_contents(bookTitle, chapterMetaData)
    
    logging.warning("Attempting to store epub")
    storeEpub(bookTitle,new_epub)#TypeError: Argument must be bytes or unicode, got 'int'
    

def foxaholic_main_interface(bookurl,cookie):

    #Check if valid url first.
    isUrl=is_valid_url(bookurl)
    if (isUrl is False):
        return
    #logging.warning(bookurl)
    bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter=foxaholic_Fetch_Novel_Data(bookurl,cookie)
    #logging.warning(bookID, bookTitle, latestChapter)
    if (check_latest_chapter(bookID,bookTitle,latestChapter)):
        pass
        #directory=getEpub(bookID)
    else:
        logging.warning("Getting epub")
        #foxaholic_save_cover_image("cover_image",bookurl,f"./books/raw/{bookTitle}",cookie)
        
        new_epub=epub.EpubBook()
        new_epub.set_identifier(bookID)
        new_epub.set_title(bookTitle)
        new_epub.set_language('en')
        new_epub.add_author(bookAuthor)
        style=open("style.css","r").read()
        
        default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)

        new_epub.add_item(default_css)
        foxaholic_produce_Epub(new_epub,bookurl,bookTitle,default_css,cookie)
        
        
        rooturl = re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/", bookurl)
        rooturl = rooturl.group()
        first,last,total=get_first_last_chapter(bookTitle)
        
        logging.warning(bookID)
        bookID=int(remove_invalid_characters(bookID))
        #logging.warning(bookID)
        directory = create_epub_directory_url(bookTitle)
        create_Entry(
            bookID=bookID,
            bookName=bookTitle,
            bookAuthor=bookAuthor,
            bookDescription=description,
            websiteHost=rooturl,
            firstChapter=first,
            lastChapter=last,
            totalChapters=total,
            directory=directory
        )
        
        create_latest(
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




#logging.warning(foxaholic_main_interface(link,cookie))





















async def novelcool_get_chapter_list(novelURL):
    async with aiohttp.ClientSession(headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br, zstd",
    }) as session:
        async with session.get(novelURL) as response:
            if response.status == 200:
                html = await response.text()
                soup = bs4.BeautifulSoup(html, 'html.parser')
                chapterTable = soup.find("div", {"class": "chapter-item-list"})
                rows= chapterTable.find_all("div", {"class":"chp-item"})
                chapterListURL=list()
                for row in rows[0:len(rows)]:
                    processChapterURL=row.find("a")["href"]
                    chapterURL=processChapterURL
                    chapterListURL.append(chapterURL)
                logging.warning(chapterListURL)      
                return chapterListURL
link="https://www.novelcool.com/novel/If-You-Could-Hear-My-Heart.html"

# stuff=asyncio.run(novelcool_get_chapter_list(link))
# with open ('test.txt', 'w') as f:
#     for line in stuff:
#         f.write(f"{line}\n")
# f.close()





def novelbin_driver_selenium(url,cookie):
    driver = webdriver.Firefox()
    options={
        #"Host": "www.foxaholic.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        #"Referer": "https://www.foxaholic.com/",
        #Foxaholic requires cookie. Will need to get new cookie each time.
        "Cookie": cookie
    }
    def interception (request):
        del request.headers['User-Agent']
        del request.headers['Accept']
        del request.headers['Accept-Language']
        del request.headers['Accept-Encoding']
        #del request.headers['Referer']
        del request.headers['Cookie']
        
        request.headers['User-Agent']=options["User-Agent"]
        request.headers['Accept']=options["Accept"]
        request.headers['Accept-Language']=options["Accept-Language"]
        request.headers['Accept-Encoding']=options["Accept-Encoding"]
        #request.headers['Referer']=options["Referer"]
        request.headers['Cookie']=options["Cookie"]
    driver.request_interceptor=interception
    driver.get(url)
    time.sleep(2) #Sleep is necessary because of the javascript loading elements on page
    soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
    driver.close()
    return soup


async def novelbin_get_chapter_list(url,cookie):
    #https://www.codecademy.com/article/web-scrape-with-selenium-and-beautiful-soup
    soup = novelbin_driver_selenium(f"{url}#tab-chapters-title",cookie)
    
    #logging.warning(soup)
    chapterTable = soup.find("div", {"id": "list-chapter"})
    #logging.warning(chapterTable)
    rows= chapterTable.find_all("li")
    
    chapterListURL=list()
    for row in rows[1:len(rows)]:
        processChapterURL=row.find("a")["href"]
        chapterURL=processChapterURL
        chapterListURL.append(chapterURL)
    #logging.warning(chapterListURL)
    return chapterListURL

def novelbin_fetch_novel_data(novelURL,cookie):
    soup=novelbin_driver_selenium(novelURL,cookie)
    
    bookID=str(generate_new_ID(bookTitle))
    logging.warning(bookID)
    
    bookTitle=soup.find("h3",{"class":"title"}).get_text()
    bookTitle=remove_invalid_characters(bookTitle)
    logging.warning(bookTitle)
    
    firstHalfBookData=soup.find("ul",{"class":"info info-meta"})
    novelData=firstHalfBookData.find_all("li")
    bookAuthor=novelData[0].get_text()
    
    descriptionBox=soup.find("div",{"id":"tab-description"})
    description=descriptionBox.find("div",{"class":"desc-text"}).get_text()

    if (description.startswith("Description: ")):
        description=description[13:]
    logging.warning(description)
    
    lastScraped=datetime.datetime.now()
    
    chapterTable = soup.find_all("ul",class_='main version-chap no-volumn')[0]
    rows= chapterTable.find_all("li", {"class":"wp-manga-chapter free-chap"})
    
    latestChapter=rows[0]
    latestChapterID=latestChapter.find("a")["href"].split("/")
    latestChapterID=latestChapterID[len(latestChapterID)-2]
    latestChapterID=re.search(r'[0-9]+',latestChapterID).group()
    
    img_url = soup.find("img",{"class":"lazy"})
    
    if not (check_directory_exists(f"./books/raw/{bookTitle}/cover_image.png")):
        novelbin_save_cover_image("cover_image",img_url,f"./books/raw/{bookTitle}")
    
    return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID


async def novelbin_save_cover_image(title,img_url,saveDirectory):
    async with aiohttp.ClientSession(headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    }) as session:
        if not isinstance(img_url,str):
            img_url=img_url["src"]
        async with session.get(img_url) as response:
            #logging.warning(response)
            if response.status == 200:
                if (saveDirectory.endswith("/")):
                    fileNameDir=f"{saveDirectory}{title}.png"
                else:
                    fileNameDir=f"{saveDirectory}/{title}.png"
                
                if not (check_directory_exists(saveDirectory)):
                    make_directory(saveDirectory)
                if not (check_directory_exists(fileNameDir)):
                    response=await response.content.read()
                    with open (fileNameDir,'wb') as f:
                        f.write(response)
                    f.close()

#link="https://novelbin.me/media/novel/genshin-impact-i-heavenly-principle-will-make-teyvat-supreme.jpg"
#asyncio.run(novelbin_save_cover_image('cover_image',link,f"./books/raw/test"))
cookie="cf_clearance=NlJs0bngkId6uzNmAa_5P7aIl9NLJHbmsYlRQoJ3Y0s-1744745517-1.2.1.1-UzOUPHlUin548pVnivA2Fax1Vl6uZqLTCpCHsvAr1huj3y.FBDW0ONuE65caZwGR9ObtilS415VxAQanWZzgLT60KJ83WO9mNsBUsrR_912KlG1G8i5vBLfykKJMSd452Oh7fkx1_Hq9BSY3_vHB8umQqgRX7VhOozxsti2fAHL.8wDvHHJvGAS3fFtvKbcUAzOZp_IfdHphAsy3Zgz29pEzDH9UKzJgDcazR5G0_wrF98HniUf5paAjAEi0aVc0B2QyOHHuJtxWSIoVWW_r9R.0POerWMqm9uv9blPIdFT0fWfDmf8YTpRYu.DptIYLW8o88NkJgyrq_zapncRFaQHCNOBUme0HVS91MpbwlaY"
link="https://novelbin.me/novel-book/raising-orphans-not-assassins"
logging.warning(asyncio.run(novelbin_get_chapter_list(link,cookie)))
