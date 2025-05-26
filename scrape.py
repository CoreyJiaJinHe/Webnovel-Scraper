import bs4
import requests
import re
from pathlib import Path
from pymongo import MongoClient
import os, errno
import datetime
from novel_template import NovelTemplate
import logging
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


logLocation=os.getenv("logs")




# url="https://www.royalroad.com/fiction/55927/"
# rooturl=re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/",url)
# rooturl=rooturl.group()

gHeaders={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
}

foxaholic_link="https://www.foxaholic.com/novel/hikikomori-vtuber-wants-to-tell-you-something/"
foxaholic_cookie="cf_clearance=Yv3eBS15RqF0OJDkWUQMp4VMkavycicNn.BAmjp5k_s-1745433738-1.2.1.1-pPt.mnmv16I9aWAG4B9X7_OwjpcEEt2od52XyaQtQTJDPNW4jMeM06HB5mGDP56rAgEXJ2y67lrfURdoIbuGL.LbmmP2yX.4khv.lo6km20gy0wzkm3cO6Z_wxG1DF3gw299AS0oz5WQh4FDznvEuEKjehJm_USSVFde0lMFmHBUcRfRwEJ8J0kDw4fiSOMHswTJLiR8wjvuyXrkwwALcwQgUlFNecGMSbBfV3KlP.1MLnlbYcwq9AlD.lQah7IfrmkiqtpmWfG9A.ky.ZCmrjPRFbFClssCF5roPrbJxW43C0.kbPbzY7Q.0pYvTSgyqg3cNUhDIsObjzgNWbZnEs5ECzR_Xh6QtnCpmw0bFZguX.36QcaRApZFw1HruVnx"

novelbin_cookie="cf_clearance=uV5dVAIEDMPgsA4aAHzYOojtcZLaDZud0OXYDA8.p0c-1744912119-1.2.1.1-SXDR6LWOaDbZ1WGCsFWuANVtmkzCCR_nlP6gzDP6Rk5GBavG0gGbzn2rb0LVhDjEP6bp6I2YzEmAKe1B4hPkTFAqvrBZQIkvahjz.vBPbQ9El6K5ItTLIOpodv..q.lXeFlVa4eqRxB_0fwQMW4z1pDOU3rsh6pCH42VmYfuGbYzygiA2Y0KT39254p88Z0XUr8pS8szqlcY2nbRZSuD.kakIq7dmgudb_o9tS1JCdg4Uf3Mnfp70zZDf5VlT8Z7iMeWwuO0aWI05d70kS8SGf6v.jtfBsbcREU74t34FShuZfM8mgym0fXmLTzRORmlA4jr42pdMWPZ4ixIPHzsIh01uaJi0xOJfR.4EFEfu_g"
novelbin_link="https://novelbin.me/novel-book/raising-orphans-not-assassins"

def write_to_logs(log):
    todayDate=datetime.datetime.today().strftime('%Y-%m-%d')
    log = datetime.datetime.now().strftime('%c') +" "+log+"\n"
    fileLocation=f"{logLocation}/{todayDate}.txt"
    if (check_directory_exists(fileLocation)):
        f=open(fileLocation,"a")
        f.write(log)
    else:
        f=open(fileLocation,'w')
        f.write(log)


global options
options={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Cookie": foxaholic_cookie
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

async def RoyalRoad_Fetch_Novel_Data(novelURL):
    global gHeaders
    try:
        async with aiohttp.ClientSession(headers = gHeaders) as session:
            async with session.get(novelURL) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = bs4.BeautifulSoup(html, 'html.parser')
                    x=re.search("/[0-9]+/",novelURL)
                    bookID=f"rr{x.group()}"
                    
                    novelData=soup.find("div",{"class":"fic-title"})
                    novelData=novelData.get_text().strip().split("\n")
                    bookTitle=novelData[0]
                    bookAuthor=novelData[len(novelData)-1]
                    #logging.warning(novelData)
                    
                    bookTitle=remove_invalid_characters(bookTitle)
                            
                    description=soup.find("div",{"class":"description"}).get_text()
                    if ("\n" in description):
                        description=description.replace("\n","")
                    if ("  " in description):
                        description=description.replace("  "," ")
                    lastScraped=datetime.datetime.now()
                    
                    chapterTable=soup.find("table",{"id":"chapters"})
                    rows=chapterTable.find_all("tr")
                    
                    latestChapter=rows[len(rows)-1]
                    latestChapter=latestChapter.find("a")["href"].split("/")
                    latestChapterID=latestChapter[5]
                    
                    img_url = soup.find("div",{"class":"cover-art-container"}).find("img")
                    saveDirectory=f"./books/raw/{bookTitle}/"
                    if not (check_directory_exists(f"./books/raw/{bookTitle}/cover_image.png")):
                        async with aiohttp.ClientSession(headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
                        }) as session:
                            if not isinstance(img_url,str):
                                img_url=img_url["src"]
                            async with session.get(img_url) as response:
                                if response.status == 200:
                                    fileNameDir=f"{saveDirectory}cover_image.png"
                                    if not (check_directory_exists(saveDirectory)):
                                        make_directory(saveDirectory)
                                    if not (check_directory_exists(fileNameDir)):
                                        response=await response.content.read()
                                        with open (fileNameDir,'wb') as f:
                                            f.write(response)
                                        f.close()
                                else:
                                    errorText=f"Failed to retrieve cover image from royalroad. Response status: {response.status}"
                                    write_to_logs(errorText)
                    #logging.warning(bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID)
                    return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID
                else:
                    errorText=f"Failed to retrieve novel data from royalroad. Response status: {response.status}"
                    write_to_logs(errorText)
    except Exception as e:
        errorText=f"Failed to fetch novel data from royalroad using a suitable link.+\n{e}"
        write_to_logs(errorText)
    #print(description)


async def RoyalRoad_Fetch_Chapter_List(novelURL):
    soup=await getSoup(novelURL)
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

    
async def RoyalRoad_Fetch_Chapter(soup):
    chapterContent = soup.find("div", {"class": "chapter-inner chapter-content"})
    if soup is None:
        logging.warning(f"Did not receive soup")
    elif chapterContent is None:
        logging.warning(f"Failed to extract content from soup")
        return None
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
        chapterID=str(dataLine[0])
        chapterLink=dataLine[1]
        chapterTitle=dataLine[2]
        f.write(chapterID+";"+chapterLink+";"+chapterTitle+"\n")
    f.close()
def append_order_of_contents(bookTitle,chapterData):
    logging.warning(chapterData)
    fileLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
    if (os.path.exists(fileLocation)):
        f=open(fileLocation,"a")
        f.write('\n')
        for dataLine in chapterData:
            chapterID=dataLine[0]
            chapterLink=dataLine[1]
            chapterTitle=dataLine[2]
            f.write(chapterID+";"+chapterLink+";"+chapterTitle+"\n")
    f.close()

async def fetch_Chapter_Title(soup):
    chapterTitle=soup.find("h1").get_text()
    return chapterTitle

def remove_non_english_characters(text):
    invalid_chars='【】'
    for char in invalid_chars:
        text=text.replace(char,'')
    result = re.sub(r'[^A-Za-z0-9,!\'\-\s]', '', text) #removes all non-english characters.
    #logging.warning(result)
    if not result:
        return text
    return result

import unicodedata

def strip_accents(s):
    return ''.join(c for c in unicodedata.normalize('NFD',s) if unicodedata.category(c) !='Mn')

def remove_invalid_characters(inputString):
    invalid_chars = '<>:;"/\\|?*'
    for char in invalid_chars:
        inputString=inputString.replace(char,'')
    inputString=re.sub(r"[\(\[].*?[\)\]]", "", inputString)
    inputString=strip_accents(inputString)
    inputString=remove_non_english_characters(inputString)
    return inputString.strip()

#logging.warning(remove_invalid_characters("https://novelbin.me/novel-book/raising-orphans-not-assassins/vol-1-ch-4-daily-settlement-a-natural-born-powerhouse"))

# logging.warning(remove_invalid_characters("引きこもりVTuberは伝えたい"))
# logging.warning(remove_invalid_characters("The New Normal - A Pokémon Elite 4 SI"))

def check_if_chapter_exists(chapterID,savedChapters):
    if (savedChapters is False):
        return False
    for chapter in savedChapters:
        if chapterID in chapter:
            return True
    return False

#Returns ChapterID and chapter file name
def get_chapter_from_saved(chapterID,savedChapters):
    logging.warning(chapterID)
    #logging.warning(savedChapters)
    for chapter in savedChapters:
        chapter=chapter.split(";")
        if chapterID == chapter[0]:
            return chapter[0],chapter[2].replace("\n","")
        
    return -1,-1
    
def get_chapter_contents_from_saved(dirLocation):
    f=open(dirLocation,"r")
    
    return f.read()

    

async def save_images_in_chapter(img_urls,saveDirectory,imageCount):
    if not (check_directory_exists(saveDirectory)):
        make_directory(saveDirectory)
    for image_url in img_urls:
        if ("emoji" in image_url):
            continue
        logging.warning(image_url)
        imageDir=f"{saveDirectory}image_{imageCount}.png"
        if not (check_directory_exists(imageDir)):
            async with aiohttp.ClientSession(headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",}) as session:
                if not isinstance(image_url,str):
                    image_url=image_url["src"]
                async with session.get(image_url) as response:
                    if response.status == 200:
                        response=await response.content.read()
                        with open (imageDir,'wb') as f:
                            f.write(response)
                            imageCount+=1
        await asyncio.sleep(0.5)
    return imageCount

def retrieve_stored_image(imageDir):
    if os.path.exists(imageDir):
        try:
            return Image.open(imageDir)
        except Exception as e:
            write_to_logs(f"Function: retrieve_stored_image. Failed to open image: {e} File Name: {imageDir}")
            return None
    else:
        logging.warning(f"Image file not found: {imageDir}")
    return None

async def getSoup(url):
    async with aiohttp.ClientSession(headers = gHeaders) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = bs4.BeautifulSoup(html, 'html.parser')
                    return soup


async def royalroad_produceEpub(new_epub,novelURL,bookTitle,css):
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    chapterMetaData=list()
    
    tocList=list()
    
    imageCount=0
    #logging.warning(RoyalRoad_Fetch_Chapter_List(novelURL))
    for url in await RoyalRoad_Fetch_Chapter_List(novelURL):
        chapterID=extract_chapter_ID(url)
        logging.warning(url)
        if (check_if_chapter_exists(chapterID,already_saved_chapters)):
            #logging(check_if_chapter_exists(chapterID,already_saved_chapters))
            chapterID,dirLocation=get_chapter_from_saved(chapterID,already_saved_chapters)
            logging.warning(dirLocation)
            chapterContent=get_chapter_contents_from_saved(dirLocation)
            fileChapterTitle=extract_chapter_title(dirLocation)
            chapterTitle=fileChapterTitle.split('-')
            chapterTitle=chapterTitle[len(chapterTitle)-1]
            images=re.findall(r'<img\s+[^>]*src="([^"]+)"[^>]*>',chapterContent)
            currentImageCount=imageCount
            for image in images:
                imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
                epubImage=retrieve_stored_image(imageDir)
                if (epubImage):
                    b=io.BytesIO()
                    epubImage.save(b,'png')
                    b_image1=b.getvalue()
                    
                    image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
                    new_epub.add_item(image_item)
                currentImageCount+=1
            chapterContent=chapterContent.encode("utf-8")
        else:
            await asyncio.sleep(0.5)
            soup=await getSoup(url)
            chapterTitle=await fetch_Chapter_Title(soup)
            fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
            #logging.warning(fileChapterTitle)
            chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{fileChapterTitle}.html"])
            chapterContent=await RoyalRoad_Fetch_Chapter(soup)
            
            hyperlinks=chapterContent.find_all('a',{'class':'link'})
            for link in hyperlinks:
                if 'imgur' in link['href']:
                    p_text=link.get_text()
                    imgur_url=link['href']
                    if not imgur_url.startswith('https://i.imgur.com/'):
                        match = re.search(r'(https?://)?(www\.)?imgur\.com/([a-zA-Z0-9]+)', imgur_url)
                        if match:
                            imgur_id = match.group(3)  # Extract the unique Imgur ID
                            imgur_url = f"https://i.imgur.com/{imgur_id}.png"  # Convert to i.imgur.com format
                    p_tag=bs4.BeautifulSoup(f"<p>{p_text}</p><div><img class=\"image\" src={imgur_url}></div>", 'html.parser')
                    link.replace_with(p_tag)
                    chapterContent=bs4.BeautifulSoup(str(chapterContent),'html.parser')
            
            
            if chapterContent:
                images=chapterContent.find_all('img')
                try:
                    images=[image['src'] for image in images]
                except Exception as e:
                    logging.warning(f"Failed to extract image src: {e}")
                    images=None
                imageDir=f"./books/raw/{bookTitle}/images/"
                currentImageCount=imageCount
                #logging.warning(images)
                if (images):
                    logging.warning("There are images in this chapter")
                    imageCount=await save_images_in_chapter(images,imageDir,imageCount)
                    if (imageCount!=currentImageCount): #This means we succeeded in saving the image.
                        for img,image in zip(chapterContent.find_all('img'),images):
                            img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")
                            
                            imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
                            epubImage=retrieve_stored_image(imageDir)
                            if (epubImage):
                                b=io.BytesIO()
                                epubImage.save(b,'png')
                                b_image1=b.getvalue()
                                
                                image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
                                new_epub.add_item(image_item)
                            currentImageCount+=1
                    else:
                        logging.warning("We failed to save the images in this chapter.")
                else:
                    logging.warning("There are no images in this chapter")
            else:
                logging.warning("chapterContent is None")
            
            chapterContent=chapterContent.encode('ascii')
            store_chapter(chapterContent,bookTitle,chapterTitle,chapterID)

        chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
        chapter.set_content(chapterContent)
        chapter.add_item(css)
        tocList.append(chapter)
        new_epub.add_item(chapter)
    
    logging.warning("We reached retrieve_cover_from_storage")
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
    
    write_order_of_contents(bookTitle, chapterMetaData)
    
    logging.warning("Attempting to store epub")
    storeEpub(bookTitle, new_epub)

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
    dirLocation="./books/epubs/"+bookTitle
    if not check_directory_exists(dirLocation):
        make_directory(dirLocation)
    
    dirLocation="./books/epubs/"+bookTitle+"/"+bookTitle+".epub"
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
    dirLocation="./books/epubs/"+bookTitle+"/"+bookTitle+".epub"
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

def check_latest_chapter(bookID,bookTitle,latestChapter:int):
    bookData=get_Entry_Via_ID(bookID)
    if (bookData is None):
        bookData=get_Entry_Via_Title(bookTitle)
        if (bookData is None):
            return False
    logging.warning(bookData["lastChapter"])
    logging.warning(latestChapter)
    latestChapter=int(latestChapter)
    savedLastChapter=int(bookData["lastChapter"])
    if (savedLastChapter==latestChapter):
        return True
    elif (savedLastChapter<=latestChapter):
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
    result = savedBooks.find({"bookID": {"$nin": [-1, 0]}}).to_list(length=None)
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
async def query_royalroad(title, option):
    if (title.isspace() or title==""):
        return "Invalid Title"
        
    if (option ==0):
        querylink = f"https://www.royalroad.com/fictions/search?globalFilters=false&title={title}"
    elif (option==1):
        querylink = f"https://www.royalroad.com/fictions/search?globalFilters=false&title={title}&orderBy=popularity"
    else:
        return ("Invalid Option")

    soup=await getSoup(querylink)
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
cookie=""

async def instantiate_new_epub(bookID,bookTitle,bookAuthor,default_css):
    try:
        new_epub=epub.EpubBook()
        new_epub.set_identifier(bookID)
        new_epub.set_title(bookTitle)
        new_epub.set_language('en')
        new_epub.add_author(bookAuthor)
        new_epub.add_item(default_css)
        return new_epub
    except Exception as e:
        errorText=f"Failed to create new_epub object. Error: {e}"
        write_to_logs(errorText)
        return
#Main call interface.
async def mainInterface(novelURL, cookie):
    #Check if valid url first.
    isUrl=is_valid_url(novelURL)
    if (cookie):
        setCookie(cookie)
    
    if (isUrl is False):
        searchTerm=novelURL
        try:
            novelURL=query_royalroad(searchTerm,0)
            #shorten url
            novelURL=re.search("https://www.royalroad.com/fiction/[0-9]+/",novelURL)
            novelURL=novelURL.group()
        except Exception as e:
            errorText=f"Failed to search royalroad for a suitable link.+\n{e}"
            write_to_logs(errorText)
            return
    else:
        style=open("style.css","r").read()
        default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)
        try:
            #Then check if it is something I can scrape. 
            #If it is not a royalroad URL, then return false and stop.
            if ("royalroad.com" in novelURL):
                bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter=await RoyalRoad_Fetch_Novel_Data(novelURL)
                
                new_epub=instantiate_new_epub(bookID,bookTitle,bookAuthor)
                await royalroad_produceEpub(new_epub,novelURL,bookTitle,default_css)
                #return asyncio.gather(royalroad_main_interface(novelURL))
            elif ("foxaholic.com" in novelURL):
                bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter=await foxaholic_Fetch_Novel_Data(novelURL)
                
                new_epub=instantiate_new_epub(bookID,bookTitle,bookAuthor)
                await foxaholic_produce_Epub(new_epub,novelURL,bookTitle,default_css)
                #return asyncio.gather(foxaholic_main_interface(novelURL))
            elif("novelbin.me" in novelURL or "novelbin.com" in novelURL):
                bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter=await novelbin_fetch_novel_data(novelURL)

                new_epub=instantiate_new_epub(bookID,bookTitle,bookAuthor)
                await novelbin_produce_epub(new_epub,novelURL,bookTitle,default_css)
                #return asyncio.gather(novelbin_main_interface(novelURL))
            elif("spacebattles.com"in novelURL):
                if re.search(r'/reader/page-\d+/$',novelURL):
                    novelURL=re.sub(r'/reader/page-\d+/$','/reader/',novelURL)
                elif not (novelURL.endswith('/reader/')):
                    if (novelURL.endswith('/')):
                        novelURL+='reader/'
                    else:
                        novelURL+='/reader/'
                bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter=await spacebattles_retrieve_novel_data(novelURL)
        
                new_epub=instantiate_new_epub(bookID,bookTitle,bookAuthor)
                await spacebattles_produce_epub(new_epub,novelURL,bookTitle,default_css)
            else:
                errorText=f"Invalid URL. It does not match Royalroad, Foxaholic, Novelbin, Spacebattles.+\n{e}"
                write_to_logs(errorText)
                return False
        except Exception as e:
            errorText=f"Error has occurred in the production.+\n{e}"
            write_to_logs(errorText)
            return

    rooturl=""
    match = re.search(r"https://(?:www\.)?([A-Za-z0-9.-]+)", novelURL)
    if match:
        rooturl=match.group(1)
    first,last,total=get_first_last_chapter(bookTitle)
    
    bookID=remove_invalid_characters(bookID)
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


def setCookie(newCookie):
    global cookie
    cookie=newCookie
    


async def updateEpub(novelURL,bookTitle):
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    chapterMetaData=list()
    imageCount=0
    logging.warning("Finding chapters not stored")
    logging.warning(await RoyalRoad_Fetch_Chapter_List(novelURL))
    for url in await RoyalRoad_Fetch_Chapter_List(novelURL):
        chapterID=extract_chapter_ID(url)
        if not (check_if_chapter_exists(chapterID,already_saved_chapters)):
            soup=await getSoup(url)
            chapterTitle=await fetch_Chapter_Title(soup)
            logging.warning(url)
            fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
            chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{fileChapterTitle}.html"])
            chapterContent=await RoyalRoad_Fetch_Chapter(soup)
            if chapterContent:
                images=chapterContent.find_all('img')
                images=[image['src'] for image in images]
                imageDir=f"./books/raw/{bookTitle}/images/"
                currentImageCount=imageCount
                #logging.warning(images)
                if (images):
                    imageCount=await save_images_in_chapter(images,imageDir,imageCount)
                    for img,image in zip(chapterContent.find_all('img'),images):
                        img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")
                else:
                    logging.warning("Chapter has no images")
            else:
                logging.warning("chapterContent is None")
            
            

            chapterContent=chapterContent.encode('ascii')
            store_chapter(chapterContent,bookTitle,chapterTitle,chapterID)
            await asyncio.sleep(0.5)
    append_order_of_contents(bookTitle, chapterMetaData)

async def royalroad_main_interface(bookurl):
    logging.warning(bookurl)
    bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter=await RoyalRoad_Fetch_Novel_Data(bookurl)
    
    #Instantiate new epub object
    new_epub=epub.EpubBook()
    new_epub.set_identifier(bookID)
    new_epub.set_title(bookTitle)
    new_epub.set_language('en')
    new_epub.add_author(bookAuthor)
    style=open("style.css","r").read()
    default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)
    new_epub.add_item(default_css)
    
    
    if (check_existing_book(bookID) or check_existing_book_Title(bookTitle)):
        if not (check_latest_chapter(bookID,bookTitle,latestChapter)):
            await updateEpub(bookurl,bookTitle)

    logging.warning("Generating new epub")
    await royalroad_produceEpub(new_epub,bookurl,bookTitle,default_css)
    rooturl=""
    match = re.search(r"https://(?:www\.)?([A-Za-z0-9.-]+)", bookurl)
    if match:
        rooturl=match.group(1)
    first,last,total=get_first_last_chapter(bookTitle)
    
    bookID=remove_invalid_characters(bookID)
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
        
    return directory
    
    #pass
    #check to see if epub already exists
    #check if new chapter was published for given book
    
    #if yes, update epub.
    #if no, return current epub.

    #implement store order of chapters



#royalroad cookie: .AspNetCore.Identity.Application

specialHeaders={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "cookie":rrcookie
}

async def specialSoup(url, specialHeaders):
    async with aiohttp.ClientSession(headers = specialHeaders) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = bs4.BeautifulSoup(html, 'html.parser')
                    return soup
                
async def retrieve_from_royalroad_follow_list():
    soup=await specialSoup("https://www.royalroad.com/my/follows", specialHeaders)
    bookTitles=soup.find_all("h2",{"class":"fiction-title"})
    bookLinks=[]
    for title in bookTitles:
        a_tag = title.find("a")
        if a_tag and "href" in a_tag.attrs:
            bookLinks.append(f"https://www.royalroad.com{a_tag["href"]}")
    logging.warning(bookLinks)
    for link in bookLinks:
        logging.warning(await royalroad_main_interface(link))
    
#asyncio.run(retrieve_from_royalroad_follow_list())
    
    


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


async def foxaholic_driver_selenium(url):
    driver = webdriver.Firefox()
    driver.request_interceptor=interception
    driver.get(url)
    soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
    driver.close()
    return soup


async def foxaholic_get_chapter_list(url):
    #https://www.codecademy.com/article/web-scrape-with-selenium-and-beautiful-soup
    soup = await foxaholic_driver_selenium(url)
    
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

def find_total_from_source(websiteHost):
    count=savedBooks.find({"bookID": {"$ne": -1},"websiteHost":websiteHost}).count_documents({})
    if (websiteHost=="foxaholic"):
        newID=f"fox{count+1}"
    elif (websiteHost=="novelbin"):   
        newID=f"nb{count+1}"

    

def generate_new_book_ID(bookTitle,websiteHost):
    logging.warning(check_existing_book_Title(bookTitle))
    if (check_existing_book_Title(bookTitle)):
        bookData=get_Entry_Via_Title(bookTitle)
        if bookData:
            return bookData["bookID"]
    else:
        if (websiteHost=="foxaholic" or "novelbin"):
            newID=find_total_from_source(websiteHost)
        





    return get_Total_Books()+1

async def foxaholic_Fetch_Novel_Data(novelURL):
    soup=await foxaholic_driver_selenium(novelURL)
    
    bookData=soup.find("div",{"class":"post-content"})
    novelData=bookData.find_all("div",{"class":"summary-content"}) or bookData.find_all("div",{"class":"summary_content"})

    bookTitle=soup.find("div",{"class":"post-title"}).get_text() or soup.find("div",{"class":"post_title"}).get_text()
    bookAuthor=novelData[2].get_text()
    logging.warning(bookTitle)
    bookTitle=remove_invalid_characters(bookTitle)
    
    bookID=str(generate_new_book_ID(bookTitle,"foxaholic"))
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
        await foxaholic_save_cover_image("cover_image",img_url,f"./books/raw/{bookTitle}")
    
    return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID



#logging.warning(asyncio.run(foxaholic_Fetch_Novel_Data(link)))


#logging.warning(get_first_last_chapter("Hikikomori VTuber Wants to Tell You Something"))


async def foxaholic_save_cover_image(title,img_url,saveDirectory):
    driver = webdriver.Firefox()
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

async def foxaholic_produce_Epub(new_epub,novelURL,bookTitle,css):
    
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    chapterMetaData=list()
    
    tocList=list()
    
    imageCount=0
    
    logging.warning(novelURL)
    for url in await foxaholic_get_chapter_list(novelURL):
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
            await asyncio.sleep(0.5)
            soup = await foxaholic_driver_selenium(url)
            chapterTitle=foxaholic_fetch_Chapter_Title(soup)
            fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
            #logging.warning(fileChapterTitle)
            chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{fileChapterTitle}.html"])
            chapterContent=await foxaholic_scrape_chapter_page(soup)
            
            if chapterContent:
                images=chapterContent.find_all('img')
                images=[image['src'] for image in images]
                imageDir=f"./books/raw/{bookTitle}/images/"
                currentImageCount=imageCount
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
                else:
                    logging.warning("There are no images in this chapter")
            else:
                logging.warning("chapterContent is None")

            #logging.warning(images)
            
            chapterContent=chapterContent.encode('ascii')
            store_chapter(chapterContent,bookTitle,chapterTitle,chapterID)
        
        logging.warning(fileChapterTitle)
        chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
        chapter.set_content(chapterContent)
        chapter.add_item(css)
        tocList.append(chapter)
        new_epub.add_item(chapter)
    
    logging.warning("We reached retrieve_cover_from_storage")
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
    
    write_order_of_contents(bookTitle, chapterMetaData)
    
    logging.warning("Attempting to store epub")
    storeEpub(bookTitle,new_epub)#TypeError: Argument must be bytes or unicode, got 'int'
    

async def foxaholic_main_interface(bookurl):
    logging.warning(bookurl)
    bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter=await foxaholic_Fetch_Novel_Data(bookurl)
    #logging.warning(bookID, bookTitle, latestChapter)
    
    #Instantiate new epub object
    new_epub=epub.EpubBook()
    new_epub.set_identifier(bookID)
    new_epub.set_title(bookTitle)
    new_epub.set_language('en')
    new_epub.add_author(bookAuthor)
    style=open("style.css","r").read()
    default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)
    new_epub.add_item(default_css)
    
    
    if (check_existing_book(bookID) or check_existing_book_Title(bookTitle)):
        if not (check_latest_chapter(bookID,bookTitle,latestChapter)):
            pass
            #await updateEpub(bookurl,bookTitle)
    
    logging.warning("Generating new epub")
        
    await foxaholic_produce_Epub(new_epub,bookurl,bookTitle,default_css)
        
        
    rooturl=""
    match = re.search(r"https://(?:www\.)?([A-Za-z0-9.-]+)", bookurl)
    if match:
        rooturl=match.group(1)
    first,last,total=get_first_last_chapter(bookTitle)
    
    logging.warning(bookID)
    bookID=remove_invalid_characters(bookID)
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
    
    return directory
foxaholic_cookie="cf_clearance=TT0k9I_s8Y9S7vtQJTXVWrRhtGI9ZVsO0fiVqJpiSVA-1744916250-1.2.1.1-d94mrymRnq1272Fwhh6WTI_FeF5bcWCAUMOLDpZURuGIYpMES4yiDiE2NEbHedX7duniT_y7olXfzBlvGx_gR2pHKbbHSU8MTSOvVxiXo9.XFapFFUCdfl.70qKyJLvbjaoGvsH8bRKY4CuNO5iHSRbMXF0ysEGbW8vmZxEdyznD6_GnJ3OsPgRPIdM5mbQ7Mt.NqO1qqZhwYgOQDMz0fH9BgxhxC8HRNoGslrkktHIW6Rzc0KHlXXwSCbhYdKNyVeSCqWZ68YbPoKx0TdG0E78Bt3GkrmmD7yPLrkhYLHq10aTJPIXymWy216B1BKK2f3FoDa8Ss4AEaStqeRMQVHkn68arhc_PC6G4nu5Oajf94Vv5ILz5VqF2GK_.5ZDI"
#logging.warning(foxaholic_main_interface(link,cookie))





















async def novelcool_get_chapter_list(novelURL):
    async with aiohttp.ClientSession(headers = gHeaders
    ) as session:
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

#stuff=asyncio.run(novelcool_get_chapter_list(link))
# with open ('test.txt', 'w') as f:
#     for line in stuff:
#         f.write(f"{line}\n")
# f.close()































async def novelbin_driver_selenium(url):
    driver = webdriver.Firefox()
    driver.request_interceptor=interception
    driver.get(url)
    await asyncio.sleep(2) #Sleep is necessary because of the javascript loading elements on page
    soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
    driver.close()
    return soup


async def novelbin_get_chapter_list(url):
    #https://www.codecademy.com/article/web-scrape-with-selenium-and-beautiful-soup
    soup = await novelbin_driver_selenium(f"{url}#tab-chapters-title")
    
    #logging.warning(soup)
    chapterTable = soup.find("div", {"id": "list-chapter"})
    #logging.warning(chapterTable)
    rows= chapterTable.find_all("li")
    
    chapterListURL=list()
    for row in rows[:len(rows)]:
        processChapterURL=row.find("a")["href"]
        chapterURL=processChapterURL
        chapterListURL.append(chapterURL)
    #logging.warning(chapterListURL)
    return chapterListURL

async def novelbin_fetch_novel_data(novelURL):
    soup=await novelbin_driver_selenium(novelURL)
    
    #There is a problem with the title, it is getting cut off by commas
    
    bookTitle=soup.find("h3",{"class":"title"}).get_text()
    bookTitle=remove_invalid_characters(bookTitle)
    logging.warning(bookTitle)
    
    bookID=str(generate_new_book_ID(bookTitle,"novelbin"))
    logging.warning(bookID)
    
    firstHalfBookData=soup.find("ul",{"class":"info info-meta"})
    novelData=firstHalfBookData.find_all("li")
    bookAuthor=novelData[0].get_text()
    
    descriptionBox=soup.find("div",{"id":"tab-description"})
    description=descriptionBox.find("div",{"class":"desc-text"}).get_text()

    if (description.startswith("Description: ")):
        description=description[13:]
    logging.warning(description)
    
    lastScraped=datetime.datetime.now()
    
    chapterTable = soup.find("div", {"id": "list-chapter"})
    rows= chapterTable.find_all("li")
    
    latestChapter=rows[len(rows)-1]
    latestChapterID=latestChapter.find("a")["href"].split("/")
    latestChapterID=latestChapterID[len(latestChapterID)-1]
    latestChapterID=re.search(r'[0-9]+',latestChapterID).group()
    
    img_url = soup.find("img",{"class":"lazy"})
    
    if not (check_directory_exists(f"./books/raw/{bookTitle}/cover_image.png")):
        await novelbin_save_cover_image("cover_image",img_url,f"./books/raw/{bookTitle}")
    
    return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID


async def novelbin_save_cover_image(title,img_url,saveDirectory):
    async with aiohttp.ClientSession(headers = gHeaders
    ) as session:
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
def novelbin_Fetch_Chapter_Title(soup):
    chapterTitle=soup.find('span',{"class":"chr-text"})

    if chapterTitle:
        chapterTitle=chapterTitle.get_text()
        if (chapterTitle.count("-")>=3):
            chapterTitle=re.sub(r'\bVol\.\s*\d+\s*-\s*Ch\.\s*\d+\s*-\s*', '', chapterTitle)
        else:
            chapterTitle=chapterTitle.split("-")
            chapterTitle=chapterTitle[len(chapterTitle)-1]
        
        if ":" in chapterTitle:
            chapterTitle=chapterTitle.split(": ")
            chapterTitle=chapterTitle[len(chapterTitle)-1]
        else:
            chapterTitle=re.sub(r'\bChapter\s+\d+\b', '', chapterTitle)
        
        chapterTitle=remove_invalid_characters(chapterTitle)
        return chapterTitle
    else:
        return None

def novelbin_scrape_chapter_page(soup):
    pageContent=soup.find_all("div",{"id":"chr-content"})[0]
    chapterContent=pageContent.find_all("p")
    
    chapterContent=re.sub('<p>\\s+</p>,','',str(chapterContent))
    chapterContent=re.sub('</p>,','</p>',str(chapterContent))
    
    if (chapterContent.startswith('[')):
        chapterContent=chapterContent[1:]
    if (chapterContent.endswith(']')):
        chapterContent=chapterContent[:-1]
    
    return bs4.BeautifulSoup(chapterContent,'html.parser')


async def novelbin_produce_epub(new_epub,novelURL,bookTitle,css):
    
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    chapterMetaData=list()
    
    tocList=list()
    
    imageCount=0
    
    logging.warning(novelURL)
    for url in await novelbin_get_chapter_list(novelURL):
        logging.warning (url)
        chapterID=url.split("/")
        chapterID=chapterID[len(chapterID)-1]
        if "vol-" in chapterID:
            chapterID = re.sub(r'vol-+\d', '', chapterID)
        if "volume-" in chapterID:
            chapterID = re.sub(r'volume-+\d', '', chapterID)
        chapterID=re.search(r'\d+',chapterID).group()
        logging.warning(chapterID)

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
            await asyncio.sleep(0.5)
            soup = await novelbin_driver_selenium(url)
            chapterTitle=novelbin_Fetch_Chapter_Title(soup)
            fileChapterTitle = f"{bookTitle} - {chapterID} - {chapterTitle}"
            #logging.warning(fileChapterTitle)
            chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{fileChapterTitle}.html"])
            chapterContent=novelbin_scrape_chapter_page(soup)
            
            if chapterContent:
                images=chapterContent.find_all('img')
                images=[image['src'] for image in images]
                imageDir=f"./books/raw/{bookTitle}/images/"
                currentImageCount=imageCount
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
                else:
                    logging.warning("There are no images in this chapter")
            else:
                logging.warning("chapterContent is None")

            #logging.warning(images)
            
            chapterContent=chapterContent.encode('ascii')
            store_chapter(chapterContent,bookTitle,chapterTitle,chapterID)
        
        logging.warning(fileChapterTitle)
        chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
        chapter.set_content(chapterContent)
        chapter.add_item(css)
        tocList.append(chapter)
        new_epub.add_item(chapter)
    
    logging.warning("We reached retrieve_cover_from_storage")
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
    
    write_order_of_contents(bookTitle, chapterMetaData)
    
    logging.warning("Attempting to store epub")
    storeEpub(bookTitle,new_epub)#TypeError: Argument must be bytes or unicode, got 'int'
    

async def novelbin_main_interface(bookurl):
    
    #logging.warning(bookurl)
    bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter=await novelbin_fetch_novel_data(bookurl)
    
    new_epub=epub.EpubBook()
    new_epub.set_identifier(bookID)
    new_epub.set_title(bookTitle)
    new_epub.set_language('en')
    new_epub.add_author(bookAuthor)
    style=open("style.css","r").read()
    default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)
    new_epub.add_item(default_css)
    
    
    #logging.warning(bookID, bookTitle, latestChapter)
    if (check_existing_book(bookID) or check_existing_book_Title(bookTitle)):
        if not (check_latest_chapter(bookID,bookTitle,latestChapter)):
            pass
            #await updateEpub(bookurl,bookTitle)

    logging.warning("Getting epub")
    
    await novelbin_produce_epub(new_epub,bookurl,bookTitle,default_css)
    
    
    rooturl=""
    match = re.search(r"https://(?:www\.)?([A-Za-z0-9.-]+)", bookurl)
    if match:
        rooturl=match.group(1)
    
    first,last,total=get_first_last_chapter(bookTitle)
    
    logging.warning(bookID)
    bookID=remove_invalid_characters(bookID)
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
    
    return directory








async def spacebattles_fetch_page_soup(url):
    global gHeaders
    async with aiohttp.ClientSession(headers = gHeaders) as session:
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                soup = bs4.BeautifulSoup(html, 'html.parser')
                return soup


async def spacebattles_retrieve_novel_data(url):
    soup=await spacebattles_fetch_page_soup(url)
    if soup:
        x=re.findall(r'(\d+)',url)
        bookID=f"sb{x[len(x)-1]}"
        
        bookTitle=soup.find("div",{"class":"p-title"}).get_text()
        bookTitle=remove_invalid_characters(bookTitle)
        
        #the assumption is that there is always a bookTitle
        bookAuthor=soup.find("div",{"class":"p-description"})
        bookAuthor=bookAuthor.find("a").get_text()
        
        description=soup.find("div",{"class":"threadmarkListingHeader-extraInfo"})
        description=description.find("div",{"class":"bbWrapper"}).get_text()
        description=description.encode('utf-8').decode('utf-8')
        description = description.replace('\n', ' ')  # Replaces newline characters with a space
        description = description.replace('  ', ' ')  # Reduces double spacing to a single space
        description = description.strip()  # Removes leading and trailing whitespace
        lastScraped=datetime.datetime.now()
        
        chapterTable=soup.find("div",{"class":"structItemContainer"})
        rows=chapterTable.find_all("li")
        
        latestChapter=rows[len(rows)-1]
        latestChapter=latestChapter.get_text()
        match=re.search(r'\b\d+(?:-\d+)?\b',latestChapter)
        latestChapterID=match.group()
        
        try:
            img_url = soup.find("span",{"class":"avatar avatar--l"})
            img_url=img_url.find("img")
            if (img_url):
                saveDirectory=f"./books/raw/{bookTitle}/"
                if not (check_directory_exists(f"./books/raw/{bookTitle}/cover_image.png")):
                    async with aiohttp.ClientSession(headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
                    }) as session:
                        if not isinstance(img_url,str):
                            img_url=img_url["src"]
                        async with session.get(f"https://forums.spacebattles.com/{img_url}") as response:
                            if response.status == 200:
                                fileNameDir=f"{saveDirectory}cover_image.png"
                                if not (check_directory_exists(saveDirectory)):
                                    make_directory(saveDirectory)
                                if not (check_directory_exists(fileNameDir)):
                                    response=await response.content.read()
                                    with open (fileNameDir,'wb') as f:
                                        f.write(response)
        except Exception as e:
            logging.warning("There is no image")
        #logging.warning(bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID)
        return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID
async def spacebattles_get_pages(url):
    soup=await spacebattles_fetch_page_soup(url)
    last=0
    pagelist=soup.find("ul",{"class":"pageNav-main"})
    for anchor in pagelist.find_all("a"):
        pagenum=anchor.get_text()
        #logging.warning(pagenum)
        if pagenum.isdigit():
            last = max(last,int(pagenum))
    return last
    
#asyncio.run(spacebattles_get_pages("https://forums.spacebattles.com/threads/quahinium-ind5235ustries-shipworks-k525ancolle-si.1103320/reader/"))
    
    
async def spacebattles_remove_garbage_from_chapter(chapterContent):
    if not isinstance(chapterContent, bs4.element.Tag):
        logging.warning("chapterContent is not a BeautifulSoup Tag object.")
        return chapterContent  # Return as-is if it's not a valid object

    tags_to_remove = ["blockquote","button"]
    for tag in tags_to_remove:
        for element in chapterContent.find_all(tag):
            element.extract()
    div_classes_to_remove=["js-selectToQuoteEnd"]
    for div_class in div_classes_to_remove:
        for element in chapterContent.find_all("div",{"class":div_class}):
            element.extract()
    
    img_classes_to_remove=["smilie"]
    for img_class in img_classes_to_remove:
        for element in chapterContent.find_all("img",{"class":img_class}):
            element.extract()
    
    emoji_pattern = re.compile("["
        u"\U0001F600-\U0001F64F"  # emoticons
        u"\U0001F300-\U0001F5FF"  # symbols & pictographs
        u"\U0001F680-\U0001F6FF"  # transport & map symbols
        u"\U0001F1E0-\U0001F1FF"  # flags (iOS)
                           "]+", flags=re.UNICODE)
    
    chapterContent=re.sub(emoji_pattern,'',str(chapterContent))
    chapterContent=bs4.BeautifulSoup(chapterContent,'html.parser')
    
    
            
    return chapterContent

async def spacebattles_save_page_content(chapterContent,bookTitle,fileTitle):
    #bookTitle=fileTitle.split(" - ")[0]
    bookDirLocation = "./books/raw/" + bookTitle+"/"
    if not check_directory_exists(bookDirLocation):
        make_directory(bookDirLocation)

    # Check if the chapter already exists
    dirLocation = f"./books/raw/{bookTitle}/{fileTitle}.html"
    if check_directory_exists(dirLocation):
        return

    # Write the chapter content to the file with UTF-8 encoding
    chapterDirLocation = "./books/raw/" + bookTitle + "/"
    completeName = os.path.join(chapterDirLocation, f"{fileTitle}.html")
    if (isinstance(chapterContent,list)):
        with open (completeName,"w", encoding="utf-8") as f:
            for article in chapterContent:
                article=article.encode('ascii')
                if (not isinstance(article,str)):
                    f.write(article.decode('utf-8'))
    else:
        with open (completeName,"w", encoding="utf-8") as f:
            chapterContent=chapterContent.encode('ascii')
            f.write(chapterContent.decode('utf-8'))

async def test_save_chapter_content(chapterContent):
    if (isinstance(chapterContent,list)):
        with open ('test.html','a', encoding="utf-8") as f:
                for article in chapterContent:
                    article=article.encode('ascii')
                    if (not isinstance(article,str)):
                        f.write(article.decode('utf-8'))
    else:
        with open ('test.html','a', encoding="utf-8") as f:
            chapterContent=chapterContent.encode('ascii')
            f.write(chapterContent.decode('utf-8'))
    
async def spacebattles_produce_epub(new_epub,novelURL,bookTitle,css):
    already_saved_chapters = get_existing_order_of_contents(bookTitle)
    chapterMetaData=list()
    tocList=list()
    imageCount=0
    logging.warning(await spacebattles_get_pages(novelURL))
    for pageNum in range(1, await spacebattles_get_pages(novelURL)):
        await asyncio.sleep(1)
        page_url = f"{novelURL}page-{pageNum}/"
        if check_if_chapter_exists(page_url, already_saved_chapters):
            #Unfinished. Can't think of how to do this.
            #Order of chapters is saved by pages, there is a limit of 10 threadmarks per page, and threadmarks are saved as individual chapters
            #The idea is to have a for loop that retrieves 10 chapters, and saves it to the new epub.
            #But if there isn't 10 chapters for said page, then it will break.
            #Not only that, but the chapter directory aren't saved either.
            #So existing code will not work. I will either have to create a new process or change the way the chapters are saved.
            
            
            #Idea. Since I'm already saving all the page content as one file.
            #I can theoretically insert a custom tag of my own to use as the split point for chapters.
            #this custom tag iwll need to hold the chapter_title as it isn't saved in my current code.
            
            chapter_id, dir_location = get_chapter_from_saved(pageNum, already_saved_chapters)
            page_content = get_chapter_contents_from_saved(dir_location)
            page_soup=bs4.BeautifulSoup(page_content,'html.parser')
            all_chapters=page_soup.find_all('div',{'id':'chapter-start'})
            for chapter_soup in all_chapters:
                chapter_title=chapter_soup.find('title')
                chapter_title=chapter_title.get_text()
                images=chapter_soup.find_all('img')
                images=[image['src'] for image in images]
                if images:
                    for image in images:
                        imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
                        epubImage=retrieve_stored_image(imageDir)
                        b=io.BytesIO()
                        epubImage.save(b,'png')
                        b_image1=b.getvalue()
                        
                        image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
                        new_epub.add_item(image_item)
                        currentImageCount+=1
                chapter=epub.EpubHtml(title=chapter_title, file_name=f"{bookTitle} - {pageNum} - {chapter_title}.xhtml", lang='en')
                chapter_content=chapter_soup.encode('ascii')
                chapter.set_content(chapter_content)
                chapter.add_item(css)
                tocList.append(chapter)
                new_epub.add_item(chapter)
                logging.warning("Retrieved:"+str(chapter_title))
            fileTitle=bookTitle+" - "+str(pageNum)
            chapterMetaData.append([pageNum,page_url,f"./books/raw/{bookTitle}/{fileTitle}.html"])
        else:
            soup=await spacebattles_fetch_page_soup(page_url)
            articles=soup.find_all("article",{"class":"message"})
            #await test_save_chapter_content(articles)
            #logging.warning(articles)
            pageContent=""
            if (articles):
                for article in articles:
                    #logging.warning(article)
                    threadmarkTitle=article.find("span",{"class":"threadmarkLabel"})
                    title=threadmarkTitle.get_text()
                    
                    chapterContent=article.find("div",{"class":"message-userContent"})
                    #logging.warning(chapterContent)
                    sanitizedChapterContent=await spacebattles_remove_garbage_from_chapter(chapterContent)
                    
                    #logging.warning(title)
                    #logging.warning(sanitizedChapterContent)
                    images=sanitizedChapterContent.find_all('img')
                    images=[image['src'] for image in images]
                    imageDir=f"./books/raw/{bookTitle}/images/"
                    currentImageCount=imageCount
                    #logging.warning(images)
                    if (images):
                        imageCount=await save_images_in_chapter(images,imageDir,imageCount)
                        for img,image in zip(sanitizedChapterContent.find_all('img'),images):
                            img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")
                            
                            imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
                            epubImage=retrieve_stored_image(imageDir)
                            b=io.BytesIO()
                            epubImage.save(b,'png')
                            b_image1=b.getvalue()
                            
                            image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
                            new_epub.add_item(image_item)
                            currentImageCount+=1
                    chapter=epub.EpubHtml(title=title, file_name=f"{bookTitle} - {pageNum} - {title}.xhtml", lang='en')
                    stringSanitizedChapterContent=str(sanitizedChapterContent)
                    pageContent+=f"<div id='chapter-start'><title>{title}</title>{stringSanitizedChapterContent}</div>"
                    
                    
                    
                    sanitizedChapterContent=sanitizedChapterContent.encode('ascii')
                    chapter.set_content(sanitizedChapterContent)
                    chapter.add_item(css)
                    tocList.append(chapter)
                    new_epub.add_item(chapter)
                    logging.warning("Saved"+str(title))
                    
                    
                    
            fileTitle=bookTitle+" - "+str(pageNum)
            #logging.warning(pageContent)
            #await test_save_chapter_content(bs4.BeautifulSoup(pageContent,'html.parser'))
            pageContent=bs4.BeautifulSoup(pageContent,'html.parser')
            await spacebattles_save_page_content(pageContent,bookTitle,fileTitle)
            chapterMetaData.append([pageNum,page_url,f"./books/raw/{bookTitle}/{fileTitle}.html"])
    
    # logging.warning("We reached retrieve_cover_from_storage")
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
    
    write_order_of_contents(bookTitle, chapterMetaData)
    
    # logging.warning("Attempting to store epub")
    storeEpub(bookTitle, new_epub)


async def spacebattles_interface(bookurl):
    if re.search(r'/reader/page-\d+/$',bookurl):
        bookurl=re.sub(r'/reader/page-\d+/$','/reader/',bookurl)
    elif not (bookurl.endswith('/reader/')):
        if (bookurl.endswith('/')):
            bookurl+='reader/'
        else:
            bookurl+='/reader/'
    
    
    bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter=await spacebattles_retrieve_novel_data(bookurl)
    
    #Instantiate new epub object
    new_epub=epub.EpubBook()
    new_epub.set_identifier(bookID)
    new_epub.set_title(bookTitle)
    new_epub.set_language('en')
    new_epub.add_author(bookAuthor)
    style=open("style.css","r").read()
    default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)
    new_epub.add_item(default_css)
    
    logging.warning("Generating new epub")
    await spacebattles_produce_epub(new_epub,bookurl,bookTitle,default_css)


    rooturl=""
    match = re.search(r"https://(?:www\.)?([A-Za-z0-9.-]+)", bookurl)
    if match:
        rooturl=match.group(1)

    first,last,total=get_first_last_chapter(bookTitle)
    
    bookID=remove_invalid_characters(bookID)
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
        
    return directory

url="https://forums.spacebattles.com/threads/quahinium-ind5235ustries-shipworks-k525ancolle-si.1103320/reader/"
link="https://forums.spacebattles.com/threads/the-new-normal-a-pok%C3%A9mon-elite-4-si.1076757/reader/"
#asyncio.run(spacebattles_interface("https://forums.spacebattles.com/threads/the-new-normal-a-pok%C3%A9mon-elite-4-si.1076757/reader/"))
#logging.warning(bookID)
#logging.warning(asyncio.run(spacebattles_retrieve_novel_data(link)))
#logging.warning(get_first_last_chapter("The New Normal - A Pokemon Elite 4 SI"))


#write_to_logs("Test log")
#logging.warning(datetime.datetime.now().strftime('%c'))

    