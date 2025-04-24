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

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from seleniumwire import webdriver

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

global options
options={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Cookie": foxaholic_cookie
    }

global cookie
cookie=""
def setCookie(newCookie):
    global cookie
    cookie=newCookie
    

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


def remove_non_english_characters(text):
    invalid_chars='【】'
    for char in invalid_chars:
        text=text.replace(char,'')
    result = re.search(r'([A-Za-z0-9,!\'\-]+( [A-Za-z0-9,!\'\-]+)+)', text)
    #logging.warning(result)
    if not result:
        return text
    return result.group() 

def remove_invalid_characters(inputString):
    invalid_chars = '<>:;"/\\|?*'
    for char in invalid_chars:
        inputString=inputString.replace(char,'')
    inputString=re.sub(r"[\(\[].*?[\)\]]", "", inputString)
    inputString=remove_non_english_characters(inputString)
    return inputString.strip()

def check_if_chapter_exists(chapterID,savedChapters):
    if (savedChapters is False):
        return False
    for chapter in savedChapters:
        if chapterID in chapter:
            return True
    return False


def retrieve_stored_image(imageDir):
    if os.path.exists(imageDir):
        return Image.open(imageDir)
    else:
        logging.warning(f"Image file not found: {imageDir}")
    return None


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
            f.close()
    driver.close()






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



























class ScraperFactory:
    @staticmethod
    def get_scraper(url):
        if "royalroad.com" in url:
            return RoyalRoadScraper()
        elif "foxaholic.com" in url:
            return FoxaholicScraper()
        elif "novelbin.me" in url or "novelbin.com" in url:
            return NovelBinScraper()
        else:
            raise ValueError("Unsupported website")
        

class Scraper:
    def fetch_novel_data(self,url):
        raise NotImplementedError
    def fetch_chapter_list(self,url):
        raise NotImplementedError
    def fetch_chapter_content(self,url):
        raise NotImplementedError
    def fetch_chapter_title(self,soup):
        raise NotImplementedError
    def get_soup(self,url):
        raise NotImplementedError

class RoyalRoadScraper(Scraper):
    async def get_soup(self,url):
        async with aiohttp.ClientSession(headers = gHeaders) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = bs4.BeautifulSoup(html, 'html.parser')
                        return soup
    async def fetch_novel_data(self, url):
        # RoyalRoad-specific logic
        return await self.RoyalRoad_Fetch_Novel_Data(url)
    
    async def RoyalRoad_Fetch_Novel_Data(self,novelURL):
        soup=await self.get_soup(novelURL)
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
        #logging.warning(bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID)
        return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID
        #print(description)

    async def fetch_chapter_list(self, url):
        # RoyalRoad-specific logic
        return await self.RoyalRoad_Fetch_Chapter_List(url)
    
    
    async def RoyalRoad_Fetch_Chapter_List(self,novelURL):
        soup=await self.get_soup(novelURL)
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

    
    async def fetch_chapter_content(self, url):
        # RoyalRoad-specific logic
        soup = await self.get_soup(url)
        return await self.RoyalRoad_Fetch_Chapter(soup)

    async def RoyalRoad_Fetch_Chapter(soup):
        chapterContent = soup.find("div", {"class": "chapter-inner chapter-content"})
        if soup is None:
            logging.warning(f"Did not receive soup")
        elif chapterContent is None:
            logging.warning(f"Failed to extract content from soup")
            return None
        return chapterContent#.encode('ascii')
        
    async def query_royalroad(self,title, option):
        if (title.isspace() or title==""):
            return "Invalid Title"
            
        if (option ==0):
            querylink = f"https://www.royalroad.com/fictions/search?globalFilters=false&title={title}"
        elif (option==1):
            querylink = f"https://www.royalroad.com/fictions/search?globalFilters=false&title={title}&orderBy=popularity"
        else:
            return ("Invalid Option")

        soup=await self.get_soup(querylink)
        resultTable=soup.find("div",{"class":"fiction-list"})
        bookTable=resultTable.find("h2",{"class":"fiction-title"})
        bookRows=bookTable.find_all("a")
        firstResult=bookRows[0]['href']
        #formatting
        resultLink=f"https://www.royalroad.com{firstResult}"
        return resultLink
    
    async def fetch_chapter_title(self,soup):
        chapterTitle=soup.find("h1").get_text()
        return chapterTitle


    
class FoxaholicScraper(Scraper):
    async def get_soup(self,url):
        driver = webdriver.Firefox()
        driver.request_interceptor=interception
        driver.get(url)
        soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
        driver.close()
        return soup
    
    async def fetch_novel_data(self, url):
        # Foxaholic-specific logic
        return await self.foxaholic_Fetch_Novel_Data(url)

    
    async def foxaholic_Fetch_Novel_Data(self,novelURL):
        soup=await self.get_soup(novelURL)
        
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
            await foxaholic_save_cover_image("cover_image",img_url,f"./books/raw/{bookTitle}")
        
        return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID

    async def fetch_chapter_list(self, url):
        # Foxaholic-specific logic
        return await self.foxaholic_get_chapter_list(url)


    async def foxaholic_get_chapter_list(self,url):
        #https://www.codecademy.com/article/web-scrape-with-selenium-and-beautiful-soup
        soup = await self.get_soup(url)
        
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
    
    async def fetch_chapter_content(self, url):
        # Foxaholic-specific logic
        soup = await self.get_soup(url)
        return self.foxaholic_scrape_chapter_page(soup)
    
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
    
    async def fetch_chapter_title(self,soup):
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

    
    
class NovelBinScraper(Scraper):
    async def get_soup(self,url):
        driver = webdriver.Firefox()
        driver.request_interceptor=interception
        driver.get(url)
        await asyncio.sleep(2) #Sleep is necessary because of the javascript loading elements on page
        soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
        driver.close()
        return soup
    
    async def fetch_novel_data(self, url):
        # Novelbin-specific logic
        return await self.novelbin_fetch_novel_data(url)


    async def novelbin_fetch_novel_data(self,novelURL):
        soup=await self.get_soup(novelURL)
        
        #There is a problem with the title, it is getting cut off by commas
        
        bookTitle=soup.find("h3",{"class":"title"}).get_text()
        bookTitle=remove_invalid_characters(bookTitle)
        logging.warning(bookTitle)
        
        bookID=str(generate_new_ID(bookTitle))
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
            await self.novelbin_save_cover_image("cover_image",img_url,f"./books/raw/{bookTitle}")
        
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
                            f.close()
                            
    def fetch_chapter_title(soup):
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

    async def fetch_chapter_list(self, url):
        # Foxaholic-specific logic
        return await self.novelbin_get_chapter_list(url)

    async def novelbin_get_chapter_list(self,url):
        #https://www.codecademy.com/article/web-scrape-with-selenium-and-beautiful-soup
        soup = await self.get_soup(f"{url}#tab-chapters-title")
        
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
    
    async def fetch_chapter_content(self, url):
        # Foxaholic-specific logic
        soup = await self.get_soup(url)
        return self.novelbin_scrape_chapter_page(soup)
    
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
    


class EpubProducer:
    
    
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
    
    async def save_images_in_chapter(img_urls,saveDirectory,imageCount):
        if not (check_directory_exists(saveDirectory)):
            make_directory(saveDirectory)
        for image_url in img_urls:
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
                            f.close()
            await asyncio.sleep(0.5)
                
            imageCount+=1
        return imageCount

    async def produce_epub(self, url, book_title, css, new_epub):
        already_saved_chapters=self.get_existing_order_of_contents(book_title)
        chapterMetaData=list()
        
        tocList=list()
        
        imageCount=0
        chapter_list = await self.fetch_chapter_list(url)
        for chapter_url in chapter_list:
            
            if (check_if_chapter_exists(chapterID,already_saved_chapters)):
                #logging(check_if_chapter_exists(chapterID,already_saved_chapters))
                chapterID,dirLocation=self.get_chapter_from_saved(chapterID,already_saved_chapters)
                chapterContent=self.get_chapter_contents_from_saved(dirLocation)
                fileChapterTitle=self.extract_chapter_title(dirLocation)
                
                chapterTitle=fileChapterTitle.split('-')
                chapterTitle=chapterTitle[len(chapterTitle)-1]
                
                images=re.findall(r'<img\s+[^>]*src="([^"]+)"[^>]*>',chapterContent)
                currentImageCount=imageCount
                for image in images:
                    imageDir=f"./books/raw/{book_title}/images/image_{currentImageCount}.png"
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
                soup=await self.fetch_chapter_content(url)
                chapterTitle=await self.fetch_Chapter_Title(soup)
                fileChapterTitle = f"{book_title} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
                #logging.warning(fileChapterTitle)
                chapterMetaData.append([chapterID,url,f"./books/raw/{book_title}/{fileChapterTitle}.html"])
                chapterContent=await self.fetch_chapter_content(chapter_url)
                
                if chapterContent:
                    images=chapterContent.find_all('img')
                    images=[image['src'] for image in images]
                    imageDir=f"./books/raw/{book_title}/images/"
                    currentImageCount=imageCount
                    #logging.warning(images)
                    if (images):
                        imageCount=await self.save_images_in_chapter(images,imageDir,imageCount)
                        for img,image in zip(chapterContent.find_all('img'),images):
                            img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")
                            
                            imageDir=f"./books/raw/{book_title}/images/image_{currentImageCount}.png"
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

                chapterContent=chapterContent.encode('ascii')
                store_chapter(chapterContent,book_title,chapterTitle,chapterID)

            chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
            chapter.set_content(chapterContent)
            chapter.add_item(css)
            tocList.append(chapter)
            new_epub.add_item(chapter)
        
        logging.warning("We reached retrieve_cover_from_storage")
        img1=retrieve_cover_from_storage(book_title)
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
        
        self.write_order_of_contents(book_title, chapterMetaData)
        
        logging.warning("Attempting to store epub")
        storeEpub(book_title, new_epub)
            
            
            # Process and store chapter content
        # Finalize and store EPUB
    async def updateEpub(self,novelURL,bookTitle):
        already_saved_chapters=self.get_existing_order_of_contents(bookTitle)
        chapterMetaData=list()
        imageCount=0
        for url in await self.fetch_chapter_list(novelURL):
            chapterID=self.extract_chapter_ID(url)
            if not (check_if_chapter_exists(chapterID,already_saved_chapters)):
                soup=await self.get_soup(url)
                chapterTitle=await self.fetch_Chapter_Title(soup)
                logging.warning(url)
                fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
                chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{fileChapterTitle}.html"])
                chapterContent=await self.fetch_chapter_content(url)
                if chapterContent:
                    images=chapterContent.find_all('img')
                    images=[image['src'] for image in images]
                    imageDir=f"./books/raw/{bookTitle}/images/"
                    currentImageCount=imageCount
                    #logging.warning(images)
                    if (images):
                        imageCount=await self.save_images_in_chapter(images,imageDir,imageCount)
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
        



class Database:
    _instance = None

    @staticmethod
    def get_instance():
        if Database._instance is None:
            MONGODB_URL = os.getenv('MONGODB_URI')
            Database._instance = MongoClient(MONGODB_URL)["Webnovels"]
        return Database._instance

#savedBooks=Database.get_instance()


#Retrieve book data from MongoDB
def get_Entry_Via_ID(bookID):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID":bookID})
    return results
#Retrieve latest book data from MongoDB
def getLatest():
    db=Database.get_instance()
    savedBooks=db["Books"]
    result=savedBooks.find_one({"bookID":-1})
    logging.warning(result)
    return result

def get_Total_Books():
    db=Database.get_instance()
    savedBooks=db["Books"]
    result=savedBooks.count_documents({})
    return result-2

def get_all_books():
    db=Database.get_instance()
    savedBooks=db["Books"]
    result = savedBooks.find({"bookID": {"$nin": [-1, 0]}}).to_list(length=None)
    result=[[result["bookID"],result["bookName"],(result["lastScraped"]).strftime('%m/%d/%Y'),result["lastChapter"]] for result in result]
    return result


def generate_new_ID(bookTitle):
    #logging.warning(check_existing_book_Title(bookTitle))
    if (check_existing_book_Title(bookTitle)):
        bookData=get_Entry_Via_Title(bookTitle)
        if bookData:
            return bookData["bookID"]
    return get_Total_Books()+1


def check_existing_book(bookID):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID":bookID})
    if (results==None):
        return False
    else:
        return True
def check_existing_book_Title(bookTitle):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookName":bookTitle})
    if (results==None):
        return False
    return True


#Return existing epub directory if the latest chapter is already stored.
def getEpub(bookID):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID":bookID})
    directory=results["directory"]
    return directory

def get_Entry_Via_Title(bookTitle):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results = savedBooks.find_one({"bookID": {"$ne": -1}, "bookName": bookTitle})
    if not results:
        return None
    return results

def check_latest_chapter(bookID,bookTitle,latestChapter):
    bookData=get_Entry_Via_ID(bookID)
    if (bookData is None):
        bookData=get_Entry_Via_Title(bookTitle)
        if (bookData is None):
            return False
    logging.warning(bookData["lastChapter"])
    logging.warning(latestChapter)
    if (bookData["lastChapter"]==latestChapter):
        return True
    elif (bookData["lastChapter"]<=latestChapter):
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
    db=Database.get_instance()
    savedBooks=db["Books"]
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
        db=Database.get_instance()
        savedBooks=db["Books"]
        if (check_existing_book(-1)):
            savedBooks.replace_one({"bookID": -1}, book)
        else:
            savedBooks.insert_one(book)


def create_epub_directory_url(bookTitle):
    dirLocation="./epubs/"+bookTitle+"/"+bookTitle+".epub"
    return dirLocation

def is_empty(chapterList):
    if not chapterList:
        return True
    return False

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


async def main_interface(url):
    try:
        scraper=ScraperFactory.get_scraper(url)
        bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter= await scraper.fetch_novel_data(url)
        epub_producer=EpubProducer()
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
        
        await epub_producer.produce_epub(url, bookTitle,default_css,new_epub)
    except ValueError as e:
        logging.error(f"Error: {e}")
    finally:
        rooturl = re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/", url)
        rooturl = rooturl.group()
        first,last,total=get_first_last_chapter(bookTitle)
        
        bookID=int(remove_invalid_characters(bookID))
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

    

        

# async def produceEpub(new_epub,novelURL,bookTitle,css):
#     already_saved_chapters=get_existing_order_of_contents(bookTitle)
#     chapterMetaData=list()
    
#     tocList=list()
    
#     imageCount=0
#     #logging.warning(RoyalRoad_Fetch_Chapter_List(novelURL))
#     for url in await RoyalRoad_Fetch_Chapter_List(novelURL):
#         chapterID=extract_chapter_ID(url)
#         logging.warning(url)
#         if (check_if_chapter_exists(chapterID,already_saved_chapters)):
#             #logging(check_if_chapter_exists(chapterID,already_saved_chapters))
#             chapterID,dirLocation=get_chapter_from_saved(chapterID,already_saved_chapters)
#             chapterContent=get_chapter_contents_from_saved(dirLocation)
#             fileChapterTitle=extract_chapter_title(dirLocation)
#             chapterTitle=fileChapterTitle.split('-')
#             chapterTitle=chapterTitle[len(chapterTitle)-1]
#             images=re.findall(r'<img\s+[^>]*src="([^"]+)"[^>]*>',chapterContent)
#             currentImageCount=imageCount
#             for image in images:
#                 imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
#                 epubImage=retrieve_stored_image(imageDir)
#                 b=io.BytesIO()
#                 epubImage.save(b,'png')
#                 b_image1=b.getvalue()
                
#                 image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
#                 new_epub.add_item(image_item)
#                 currentImageCount+=1
#             chapterContent=chapterContent.encode("utf-8")
#         else:
#             await asyncio.sleep(0.5)
#             soup=await getSoup(url)
#             chapterTitle=await fetch_Chapter_Title(soup)
#             fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
#             #logging.warning(fileChapterTitle)
#             chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{fileChapterTitle}.html"])
#             chapterContent=await RoyalRoad_Fetch_Chapter(soup)
            
#             if chapterContent:
#                 images=chapterContent.find_all('img')
#                 images=[image['src'] for image in images]
#                 imageDir=f"./books/raw/{bookTitle}/images/"
#                 currentImageCount=imageCount
#                 #logging.warning(images)
#                 if (images):
#                     imageCount=await save_images_in_chapter(images,imageDir,imageCount)
#                     for img,image in zip(chapterContent.find_all('img'),images):
#                         img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")
                        
#                         imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
#                         epubImage=retrieve_stored_image(imageDir)
#                         b=io.BytesIO()
#                         epubImage.save(b,'png')
#                         b_image1=b.getvalue()
                        
#                         image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
#                         new_epub.add_item(image_item)
#                         currentImageCount+=1
#                 else:
#                     logging.warning("There are no images in this chapter")
#             else:
#                 logging.warning("chapterContent is None")

#             chapterContent=chapterContent.encode('ascii')
#             store_chapter(chapterContent,bookTitle,chapterTitle,chapterID)

#         chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
#         chapter.set_content(chapterContent)
#         chapter.add_item(css)
#         tocList.append(chapter)
#         new_epub.add_item(chapter)
    
#     logging.warning("We reached retrieve_cover_from_storage")
#     img1=retrieve_cover_from_storage(bookTitle)
#     if img1:    
#         b=io.BytesIO()
#         try:
#             img1.save(b,'png')
#             b_image1=b.getvalue()
#             image1_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image1)
#             new_epub.add_item(image1_item)
#         except Exception as e:
#             logging.warning(f"Failed to save image:{e}")
    
#     new_epub.toc=tocList
#     new_epub.spine=tocList
#     new_epub.add_item(epub.EpubNcx())
#     new_epub.add_item(epub.EpubNav())
    
#     write_order_of_contents(bookTitle, chapterMetaData)
    
#     logging.warning("Attempting to store epub")
#     storeEpub(bookTitle, new_epub)
