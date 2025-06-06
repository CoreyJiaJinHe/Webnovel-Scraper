import bs4
import re
import os, errno
import datetime
from novel_template import NovelTemplate
import logging
import asyncio
import io
from ebooklib import epub 
from PIL import Image
import aiohttp

logLocation=os.getenv("logs")

def write_to_logs(log):
    todayDate=datetime.datetime.today().strftime('%Y-%m-%d')
    log = datetime.datetime.now().strftime('%c') +" "+log+"\n"
    fileLocation=f"{logLocation}/{todayDate}"
    if (check_directory_exists(fileLocation)):
        f=open(fileLocation,"a")
        f.write(log)
    else:
        f=open(fileLocation,'w')
        f.write(log)



from mongodb import (
    check_existing_book,
    check_existing_book_Title,
    check_latest_chapter,
    get_Entry_Via_ID,
    get_Entry_Via_Title,
    getLatest,
    get_Total_Books,
    get_all_books,
    create_Entry,
    create_latest
)

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from seleniumwire import webdriver

from scrape import test_save_chapter_content

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

options={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Cookie": foxaholic_cookie
    }

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
            errorText=f"Failed to make directory. Function make_directory. Error: {e}"
            write_to_logs(errorText)
            return



def remove_non_english_characters(text):
    invalid_chars='【】'
    for char in invalid_chars:
        text=text.replace(char,'')
    text = re.sub(r'\s+', ' ', text)
    result = re.search(r'([A-Za-z0-9,!\'\-]+( [A-Za-z0-9,!\'\-]+)+)', text)
    #logging.warning(result)
    if not result:
        return text
    return result.group() 

def remove_invalid_characters(inputString):
    invalid_chars = '.-<>:;"/\\|?*()'
    for char in invalid_chars:
        inputString=inputString.replace(char,' ')
#    inputString=re.sub(r"[\(\[].*?[\)\]]", "", inputString)
    inputString=remove_non_english_characters(inputString)
    return inputString.strip()

def remove_tags_from_title(inputString):
    invalid_chars = '.-<>:;"/\\|?*'
    for char in invalid_chars:
        inputString=inputString.replace(char,' ')
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
    try:
        if os.path.exists(imageDir):
            return Image.open(imageDir)
        else:
            #logging.warning(f"Image file not found: {imageDir}")
            errorText=f"Image file not found: {imageDir}"
            write_to_logs(errorText)
    except Exception as e:
        errorText=f"Failed to retrieve image. Function retrieve_stored_image. Error: {e}"
        write_to_logs(errorText)
    return None


def retrieve_cover_from_storage(bookTitle):
    dirLocation=f"./books/raw/{bookTitle}/cover_image.png"
    if os.path.exists(dirLocation):
        try:
            return Image.open(dirLocation)
        except Exception as e:
            errorText=f"Failed to retrieve cover image. Function retrieve_cover_from_storage. Error: {e}"
            write_to_logs(errorText)
            return None
    errorText=f"Cover image does not exist. Function retrieve_cover_from_storage."
    write_to_logs(errorText)
    return None

def storeEpub(bookTitle,new_epub):
    try:
        dirLocation="./books/epubs/"+bookTitle
        if not check_directory_exists(dirLocation):
            make_directory(dirLocation)
        
        dirLocation="./books/epubs/"+bookTitle+"/"+bookTitle+".epub"
        if (check_directory_exists(dirLocation)):
            os.remove(dirLocation)
        epub.write_epub(dirLocation,new_epub)
    except Exception as e:
        errorText=f"Error with storing epub. Function store_epub. Error: {e}"
        write_to_logs(errorText)
    

def store_chapter(content, bookTitle, chapterTitle, chapterID):
    try:
        # Remove invalid characters from file name
        bookTitle = remove_invalid_characters(bookTitle)
        chapterTitle = remove_invalid_characters(chapterTitle)
        #logging.warning(content)
        # Check if the folder for the book exists
        bookDirLocation = "./books/raw/" + bookTitle
        if not check_directory_exists(bookDirLocation):
            make_directory(bookDirLocation)

        # Check if the chapter already exists
        title = f"{bookTitle} - {chapterID} - {chapterTitle}"
        dirLocation = f"./books/raw/{bookTitle}/{title}.html"
        #logging.warning(dirLocation)

        if check_directory_exists(dirLocation):
            return

        # Write the chapter content to the file with UTF-8 encoding
        chapterDirLocation = "./books/raw/" + bookTitle + "/"
        completeName = os.path.join(chapterDirLocation, f"{title}.html")
        with open(completeName, "w", encoding="utf-8") as f:
            if not isinstance(content, str):
                content = content.decode("utf-8")  # Decode bytes to string if necessary
            f.write(content)
    except Exception as e:
        errorText=f"Storing chapter failed. Function store_chapter Error: {e}"
        write_to_logs(errorText)



def update_existing_order_of_contents(bookTitle,chapterList):
    try:
        bookDirLocation=f"./books/raw/{bookTitle}"
        if not (check_directory_exists(bookDirLocation)):
            make_directory(bookDirLocation)
        fileLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
        if (os.path.exists(fileLocation)):
            f=open(fileLocation,"w")
        else:
            f=open(fileLocation,"x")
            
        try:
            for line in chapterList:
                f.write(str(line)) #FORMATTING IS FUCKED
        except Exception as e:
            errorText=f"Updating order of contents failed. Function update_existing_order_of_contents Error: {e}"
            write_to_logs(errorText)
        finally:
            f.close()
    except Exception as e:
        errorText=f"Updating order of contents failed. Function update_existing_order_of_contents Error: {e}"
        write_to_logs(errorText)
        
    
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
    


def generate_new_ID(bookTitle):
    try:
        if (check_existing_book_Title(bookTitle)):
            bookData=get_Entry_Via_Title(bookTitle)
            if bookData:
                return bookData["bookID"]
        return get_Total_Books()+1
    except Exception as e:
        errorText=f"Generate new id failed. Function generate_new_ID Error: {e}"
        write_to_logs(errorText)







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











class ScraperFactory:
    @staticmethod
    def get_scraper(url):
        if "royalroad.com" in url:
            return RoyalRoadScraper()
        elif "foxaholic.com" in url:
            return FoxaholicScraper()
        elif "novelbin.me" in url or "novelbin.com" in url:
            return NovelBinScraper()
        elif "spacebattles.com" in url:
            return SpaceBattlesScraper()
        else:
            errorText="Failed to get scraper. Function get_scraper Error: Unsupported website"
            write_to_logs(errorText)
            raise ValueError("Unsupported website")
        

class Scraper:
    async def fetch_novel_data(self,url):
        raise NotImplementedError
    async def fetch_chapter_list(self,url):
        raise NotImplementedError
    async def fetch_chapter_content(self,soup):
        raise NotImplementedError
    async def fetch_chapter_title(self,soup):
        raise NotImplementedError
    async def get_soup(self,url):
        global gHeaders
        
        try:
            async with aiohttp.ClientSession(headers = gHeaders) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = bs4.BeautifulSoup(html, 'html.parser')
                        return soup
                    else:
                        errorText=f"Failed to get soup. Function get_soup Error: {response.status}"
                        write_to_logs(errorText)
        except Exception as e:
            errorText=f"Failed to get soup. Function get_soup Error: {e}, {url}"
            write_to_logs(errorText)

class SpaceBattlesScraper(Scraper):
    async def fetch_novel_data(self,url):
        logging.warning(url)
        soup=await self.get_soup(url)
        if soup:
            try:
                x=re.findall(r'(\d+)',url)
                bookID=x[len(x)-1]
                
                bookTitle=soup.find("div",{"class":"p-title"}).get_text()
                bookTitle=remove_tags_from_title(bookTitle)
                
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
                                            f.close()
                except Exception as e:
                    errorText=f"Failed to get cover image. There might be no cover. Or a different error. Function fetch_novel_data Error: {e}"
                    write_to_logs(errorText)
                #logging.warning(bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID)
                return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID
            except Exception as e:
                errorText=f"Failed to get novel data. Function Spacebattles fetch_novel_data Error: {e}"
                write_to_logs(errorText)
    
    async def fetch_chapter_list(self,url):
        #logging.warning('Fetching spacebattles total pages')
        #logging.warning(url)
        soup=await self.get_soup(url)
        last=0
        try:
            pagelist=soup.find("ul",{"class":"pageNav-main"})
            for anchor in pagelist.find_all("a"):
                pagenum=anchor.get_text()
                #logging.warning(pagenum)
                if pagenum.isdigit():
                    last = max(last,int(pagenum))
            logging.warning(f"Last page: {last}")
            return last
        except Exception as e:
            errorText=f"Failed to get total number of pages. Function Spacebattles fetch_chapter_list Error: {e}"
            write_to_logs(errorText)

    async def fetch_chapter_content(self,soup):
        raise NotImplementedError
    
    async def fetch_chapter_title(self,soup):
        try:
            threadmarkTitle=soup.find("span",{"class":"threadmarkLabel"})
            return threadmarkTitle.get_text()
        except Exception as e:
            errorText=f"Failed to get chapter title. Function Spacebattles fetch_chapter_title Error: {e}"
            write_to_logs(errorText)
    
    
    
    
    
class RoyalRoadScraper(Scraper):
    async def fetch_novel_data(self, url):
        # RoyalRoad-specific logic
        return await self.RoyalRoad_Fetch_Novel_Data(url)
    
    async def RoyalRoad_Fetch_Novel_Data(self,novelURL):
        soup=await self.get_soup(novelURL)
        if (soup):
            try:
                x=re.search("/[0-9]+/",novelURL)
                bookID=x.group()
                
                novelData=soup.find("div",{"class":"fic-title"})
                novelData=novelData.get_text().strip().split("\n")
                bookTitle=novelData[0]
                bookAuthor=novelData[len(novelData)-1]
                #logging.warning(novelData)
                
                bookTitle=remove_tags_from_title(bookTitle)
                        
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
                if (img_url):
                    if not (check_directory_exists(f"{saveDirectory}/cover_image.png")):
                        await self.royalroad_save_cover_image(bookTitle,img_url,saveDirectory)
                
                #logging.warning(bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID)
                return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID
            except Exception as e:
                errorText=f"Failed to get novel data. Function royalroad_fetch_novel_data Error: {e}"
                write_to_logs(errorText)
        else:
            errorText=f"Failed to get soup for processing. Function RoyalRoad_Fetch_Novel_Data Error: No soup"
            write_to_logs(errorText)
            return None
        
    async def royalroad_save_cover_image(bookTitle,img_url,saveDirectory):
        try:
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
                        response=await response.content.read()
                        with open (fileNameDir,'wb') as f:
                            f.write(response)
                        f.close()
        except Exception as error:
            errorText=f"Failed to get soup for processing. Function RoyalRoad_save_cover_image Error: {error}"
            write_to_logs(errorText)
        

    async def fetch_chapter_list(self, url):
        # RoyalRoad-specific logic
        return await self.RoyalRoad_Fetch_Chapter_List(url)
    
    
    async def RoyalRoad_Fetch_Chapter_List(self,novelURL):
        soup=await self.get_soup(novelURL)
        try:
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
        except Exception as error:
            errorText=f"Failed to get soup for processing. Function RoyalRoad_Fetch_Chapter_List Error: {error}"
            write_to_logs(errorText)

    
    async def fetch_chapter_content(self, soup):
        # RoyalRoad-specific logic
        #logging.warning(soup)
        return await self.RoyalRoad_Fetch_Chapter(soup)

    async def RoyalRoad_Fetch_Chapter(self,soup):
        chapterContent = soup.find("div", {"class": "chapter-inner chapter-content"})
        
        if soup is None:
            errorText=f"Failed to get soup for processing. Function RoyalRoad_Fetch_Chapter Error: No soup"
            write_to_logs(errorText)
            return None
        elif chapterContent is None:
            errorText=f"Failed to get content. Function RoyalRoad_Fetch_Chapter Error: Soup has no chapter-inner"
            write_to_logs(errorText)
#            logging.warning(errorText)
            return None
        return chapterContent#.encode('ascii')
        
    async def query_royalroad(self,title, option):
        if (title.isspace() or title==""):
            errorText=f"Failed to search title. Function query_royalroad Error: No title inputted"
            write_to_logs(errorText)
            return "Invalid Title"
            
        if (option ==0):
            querylink = f"https://www.royalroad.com/fictions/search?globalFilters=false&title={title}"
        elif (option==1):
            querylink = f"https://www.royalroad.com/fictions/search?globalFilters=false&title={title}&orderBy=popularity"
        else:
            errorText=f"Improper query attempt. Function query_royalroad Error: Invalid query option. How did you even do this?"
            write_to_logs(errorText)
            return ("Invalid Option")

        soup=await self.get_soup(querylink)
        try:
            resultTable=soup.find("div",{"class":"fiction-list"})
            bookTable=resultTable.find("h2",{"class":"fiction-title"})
            bookRows=bookTable.find_all("a")
            firstResult=bookRows[0]['href']
            #formatting
            resultLink=f"https://www.royalroad.com{firstResult}"
            return resultLink
        except Exception as error:
            errorText=f"Search failed. Most likely reason: There wasn't any search results. Function query_royalroad Error: {error}"
            write_to_logs(errorText)
            
    async def fetch_chapter_title(self,soup):
        try:
            chapterTitle=soup.find("h1").get_text()
            return chapterTitle
        except Exception as error:
            errorText=f"Failed to get title from soup. Function fetch_chapter_title Error: {error}"
            write_to_logs(errorText)


    
class FoxaholicScraper(Scraper):
    async def get_soup(self,url):
        try:
            driver = webdriver.Firefox()
            driver.request_interceptor=interception
            driver.get(url)
            soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
            driver.close()
            return soup
        except Exception as error:
            errorText=f"Failed to get soup Function foxaholic_get_soup Error: {error}"
            write_to_logs(errorText)
        return None
    
    async def fetch_novel_data(self, url):
        # Foxaholic-specific logic
        return await self.foxaholic_Fetch_Novel_Data(url)

    
    async def foxaholic_Fetch_Novel_Data(self,novelURL):
        try:
            soup=await self.get_soup(novelURL)
            
            bookData=soup.find("div",{"class":"post-content"})
            novelData=bookData.find_all("div",{"class":"summary-content"}) or bookData.find_all("div",{"class":"summary_content"})

            bookTitle=soup.find("div",{"class":"post-title"}).get_text() or soup.find("div",{"class":"post_title"}).get_text()
            bookAuthor=novelData[2].get_text()
            #logging.warning(bookTitle)
            bookTitle=remove_tags_from_title(bookTitle)
            
            bookID=str(generate_new_ID(bookTitle))
            #logging.warning(bookID)
                    
            descriptionBox=soup.find("div",{"class":"description-summary"})
            description=descriptionBox.find("div",{"class":"summary__content"}).get_text()
            
            if (description.startswith("Description: ")):
                description=description[13:]
            if ("\n" in description):
                description=description.replace("\n","")
            if ("  " in description):
                description=description.replace("  "," ")
                
                
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
                await self.foxaholic_save_cover_image("cover_image",img_url,f"./books/raw/{bookTitle}")
            
            return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID
        except Exception as error:
            errorText=f"Failed to extract noveldata from soup. Function foxaholic_fetch_novel_data Error: {error}"
            write_to_logs(errorText)
        return None
    async def foxaholic_save_cover_image(title,img_url,saveDirectory):
        try:
            driver = webdriver.Firefox()
            driver.request_interceptor=interception
            driver.get(img_url["src"])
            image=driver.find_element(By.CSS_SELECTOR, 'img')
            driver.close()
        except Exception as error:
            errorText=f"Failed to retrieve image from url. Function foxaholic_save_cover_image Error: {error}"
            write_to_logs(errorText)
        
        try:
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
        except Exception as error:
            errorText=f"Failed to save image. Function foxaholic_save_cover_image Error: {error}"
            write_to_logs(errorText)



    async def fetch_chapter_list(self, url):
        # Foxaholic-specific logic
        return await self.foxaholic_get_chapter_list(url)


    async def foxaholic_get_chapter_list(self,url):
        #https://www.codecademy.com/article/web-scrape-with-selenium-and-beautiful-soup
        soup = await self.get_soup(url)
        
        try:
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
        except Exception as error:
            errorText=f"Failed to get chapter urls from chapter list of page. Function foxaholic_get_chapter_list Error: {error}"
            write_to_logs(errorText)
    
    async def fetch_chapter_content(self, soup):
        # Foxaholic-specific logic
        return self.foxaholic_scrape_chapter_page(soup)
    
    def foxaholic_scrape_chapter_page(self,soup):
        try:
            pageContent=soup.find_all("div",{"class":"reading-content"})[0]
            chapterContent=pageContent.find_all("p")
            
            chapterContent=re.sub('<p>\\s+</p>,','',str(chapterContent))
            chapterContent=re.sub('</p>,','</p>',str(chapterContent))
            
            if (chapterContent.startswith('[')):
                chapterContent=chapterContent[1:]
            if (chapterContent.endswith(']')):
                chapterContent=chapterContent[:-1]
            
            return bs4.BeautifulSoup(chapterContent,'html.parser')
        except Exception as error:
                errorText=f"Failed to grab content from soup. Function foxaholic_scrape_chapter_page Error: {error}"
                write_to_logs(errorText)
    async def fetch_chapter_title(self,soup):
        
        try:
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
        except Exception as error:
            errorText=f"Failed to get chapter title. Function foxaholic_fetch-chapter_title Error: {error}"
            write_to_logs(errorText)

    
class NovelBinScraper(Scraper):
    async def get_soup(self,url):
        try:
            driver = webdriver.Firefox()
            driver.request_interceptor=interception
            driver.get(url)
            await asyncio.sleep(2) #Sleep is necessary because of the javascript loading elements on page
            soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
            driver.close()
            return soup
        except Exception as error:
            errorText=f"Failed to get soup from url. Function novelbin_get_soup Error: {error}"
            write_to_logs(errorText)

    async def fetch_novel_data(self, url):
        # Novelbin-specific logic
        return await self.novelbin_fetch_novel_data(url)


    async def novelbin_fetch_novel_data(self,novelURL):
        soup=await self.get_soup(novelURL)
        
        #There is a problem with the title, it is getting cut off by commas
        try:
            bookTitle=soup.find("h3",{"class":"title"}).get_text()
            bookTitle=remove_tags_from_title(bookTitle)
            logging.warning(bookTitle)
            
            bookID=str(generate_new_ID(bookTitle))
            logging.warning(bookID)
            
            firstHalfBookData=soup.find("ul",{"class":"info info-meta"})
            novelData=firstHalfBookData.find_all("li")
            bookAuthor=novelData[0].get_text()
            
            if ("\n" in bookAuthor):
                bookAuthor=bookAuthor.replace("\n","")
            if ("  " in bookAuthor):
                bookAuthor=bookAuthor.replace("  "," ")
                
            if ("Author:" in bookAuthor):
                bookAuthor=bookAuthor.replace("Author:","")
                
            descriptionBox=soup.find("div",{"id":"tab-description"})
            description=descriptionBox.find("div",{"class":"desc-text"}).get_text()

            if (description.startswith("Description: ")):
                description=description[13:]
            description=description.strip()
            if ("\n" in description):
                description=description.replace("\n","")
            if ("  " in description):
                description=description.replace("  "," ")
            
            logging.warning(description)
            
            lastScraped=datetime.datetime.now()
            
            chapterTable = soup.find("div", {"id": "list-chapter"})
            rows= chapterTable.find_all("li")
            
            latestChapter=rows[len(rows)-1]
            latestChapterID=latestChapter.find("a")["href"].split("/")
            latestChapterID=latestChapterID[len(latestChapterID)-1]
            latestChapterID=re.search(r'[0-9]+',latestChapterID).group()
        except Exception as error:
            errorText=f"Failed to get novel data. Function novelbin-fetch_novel_data Error: {error}"
            write_to_logs(errorText)
        
        try:
            img_url = soup.find("img",{"class":"lazy"})
            
            if not (check_directory_exists(f"./books/raw/{bookTitle}/cover_image.png")):
                await self.novelbin_save_cover_image("cover_image",img_url,f"./books/raw/{bookTitle}")
        except Exception as error:
            errorText=f"Failed to find image, or save it. Function novelbin_fetch_novel_data Error: {error}"
            write_to_logs(errorText)
            
        return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID


    async def novelbin_save_cover_image(self,title,img_url,saveDirectory):
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
                    response=await response.content.read()
                    with open (fileNameDir,'wb') as f:
                        f.write(response)
                        f.close()
                            
    async def fetch_chapter_title(self,soup):
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
            errorText=f"Failed to get chapter title. Function novelbin_get_chapter_list Error: No chapterTitle found"
            write_to_logs(errorText)
            return None
            
    async def fetch_chapter_list(self, url):
        # novelbin-specific logic
        return await self.novelbin_get_chapter_list(url)

    async def novelbin_get_chapter_list(self,url):
        #https://www.codecademy.com/article/web-scrape-with-selenium-and-beautiful-soup
        soup = await self.get_soup(f"{url}#tab-chapters-title")
        
        try:
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
        except Exception as error:
            errorText=f"Failed to get chapter urls from chapter list of page. Function novelbin_get_chapter_list Error: {error}"
            write_to_logs(errorText)
            
    async def fetch_chapter_content(self, soup):
        # Foxaholic-specific logic
        return self.novelbin_scrape_chapter_page(soup)
    
    def novelbin_scrape_chapter_page(self,soup):
        try:
            pageContent=soup.find_all("div",{"id":"chr-content"})[0]
            chapterContent=pageContent.find_all("p")
            
            chapterContent=re.sub('<p>\\s+</p>,','',str(chapterContent))
            chapterContent=re.sub('</p>,','</p>',str(chapterContent))
            
            if (chapterContent.startswith('[')):
                chapterContent=chapterContent[1:]
            if (chapterContent.endswith(']')):
                chapterContent=chapterContent[:-1]
            
            return bs4.BeautifulSoup(chapterContent,'html.parser')
        except Exception as error:
            errorText=f"Failed to get chapterContent as soup object. Function novelbin_scrape_chapter_page Error: {error}"
            write_to_logs(errorText)

class EpubProducer:
    async def fetch_chapter_list(self, url):
        raise NotImplementedError("Subclasses must implement this method.")

    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count, new_epub):
        raise NotImplementedError("Subclasses must implement this method.")

    async def extract_chapter_ID(self,chapter_url):
        raise NotImplementedError("Subclasses must implement this method.")
    
    async def retrieve_images_in_chapter(self,images_url,image_dir,image_count,new_epub):
        current_image_count=image_count
        try:
            for img_url in images_url:
                image_path=f"{image_dir}/{img_url}"
                epubImage=Image.open(image_path)
                b=io.BytesIO()
                epubImage.save(b,'png')
                image_data=b.getvalue()
                image_item = epub.EpubItem(uid=f"image_{current_image_count}", file_name=img_url, media_type="image/png", content=image_data)
                new_epub.add_item(image_item)
                current_image_count+=1
            return current_image_count
        except Exception as error:
            errorText=f"Failed to retrieve images for chapter to add to epub object. Function retrieve_images_in_chapter Error: {error}"
            write_to_logs(errorText)
    def get_existing_order_of_contents(self, book_title):
        # Default implementation
        dir_location = f"./books/raw/{book_title}/order_of_chapters.txt"
        if os.path.exists(dir_location):
            with open(dir_location, "r") as f:
                return f.readlines()
        return []

    def check_if_chapter_exists(self, chapter_id, saved_chapters):
        for chapter in saved_chapters:
            if str(chapter_id) in chapter:
                return True
        return False

    def get_chapter_from_saved(self, chapter_id, saved_chapters):
        for chapter in saved_chapters:
            chapter = chapter.split(";")
            if str(chapter_id) == str(chapter[0]):
                return chapter[0], chapter[2].strip()
        return None, None

    def get_chapter_contents_from_saved(self, dir_location):
        with open(dir_location, "r") as f:
            return f.read()

    # def extract_chapter_ID(self, chapter_url):
    #     return chapter_url.split("/")[-2]

    def extract_chapter_title(self, dir_location):
        return os.path.basename(dir_location).split(" - ")[-1].replace(".html", "")

    def create_epub_chapter(self, chapter_title,file_chapter_title,chapter_content, css):
        try:
            chapter_content=chapter_content.encode('ascii')
            chapter=epub.EpubHtml(title=chapter_title,file_name=file_chapter_title+'.xhtml',lang='en')
            chapter.set_content(chapter_content)
            chapter.add_item(css)
            return chapter
        except Exception as error:
            errorText=f"Failed to create chapter to add to epub. Function create_epub_chapter Error: {error}"
            write_to_logs(errorText)

    def add_cover_image(self, book_title, new_epub):
        img = retrieve_cover_from_storage(book_title)
        if img:
            b = io.BytesIO()
            img.save(b, "png")
            b_image = b.getvalue()
            cover_item = epub.EpubItem(uid="cover_image", file_name="images/cover_image.png", media_type="image/png", content=b_image)
            new_epub.add_item(cover_item)

    def finalize_epub(self, new_epub, toc_list, book_title, chapter_metadata):
        self.write_order_of_contents(book_title, chapter_metadata)
        #logging.warning(toc_list)
        new_epub.toc = toc_list
        new_epub.spine = toc_list
        new_epub.add_item(epub.EpubNcx())
        new_epub.add_item(epub.EpubNav())
        storeEpub(book_title, new_epub)

    def write_order_of_contents(self, book_title, chapter_metadata):
        file_location = f"./books/raw/{book_title}/order_of_chapters.txt"
        logging.warning(chapter_metadata)
        with open(file_location, "w") as f:
            for data in chapter_metadata:
                logging.warning(data)
                f.write(";".join(str(data))+ "\n")
            
    # async def updateEpub(self,novelURL,bookTitle):
    #     already_saved_chapters=self.get_existing_order_of_contents(bookTitle)
    #     chapterMetaData=list()
    #     imageCount=0
    #     for url in await self.fetch_chapter_list(novelURL):
    #         chapterID=self.extract_chapter_ID(url)
    #         if not (check_if_chapter_exists(chapterID,already_saved_chapters)):
    #             soup=await self.get_soup(url)
    #             chapterTitle=await self.fetch_Chapter_Title(soup)
    #             logging.warning(url)
    #             fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
    #             chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{fileChapterTitle}.html"])
    #             chapterContent=await self.fetch_chapter_content(soup)
    #             if chapterContent:
    #                 images=chapterContent.find_all('img')
    #                 images=[image['src'] for image in images]
    #                 imageDir=f"./books/raw/{bookTitle}/images/"
    #                 currentImageCount=imageCount
    #                 #logging.warning(images)
    #                 if (images):
    #                     imageCount=await self.save_images_in_chapter(images,imageDir,imageCount)
    #                     for img,image in zip(chapterContent.find_all('img'),images):
    #                         img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")
    #                 else:
    #                     logging.warning("Chapter has no images")
    #             else:
    #                 logging.warning("chapterContent is None")
                
                

    #             chapterContent=chapterContent.encode('utf-8')
    #             store_chapter(chapterContent,bookTitle,chapterTitle,chapterID)
    #             await asyncio.sleep(0.5)
    #     append_order_of_contents(bookTitle, chapterMetaData)
    
    async def produce_epub(self, url, book_title, css, new_epub):
        already_saved_chapters = self.get_existing_order_of_contents(book_title)
        chapter_list = await self.fetch_chapter_list(url)
        chapter_metadata = []
        toc_list = []
        image_count = 0
        logging.warning(chapter_list)
        for chapter_url in chapter_list:
            logging.warning(chapter_url)
            chapter_id = await self.extract_chapter_ID(chapter_url)
            if self.check_if_chapter_exists(chapter_id, already_saved_chapters):
                chapter_id, dir_location = self.get_chapter_from_saved(chapter_id, already_saved_chapters)
                chapter_content = self.get_chapter_contents_from_saved(dir_location)
                chapter_title = self.extract_chapter_title(dir_location)
                chapter_content_soup=bs4.BeautifulSoup(chapter_content,'html.parser')
                images=chapter_content_soup.find_all('img')
                images=[image['src'] for image in images]
                image_dir = f"./books/raw/{book_title}/"
                if images:
                    image_count=await self.retrieve_images_in_chapter(images, image_dir,image_count,new_epub)
            else:
                chapter_title, chapter_content, image_count = await self.process_new_chapter(
                    chapter_url, book_title, chapter_id, image_count, new_epub
                )
                
            file_chapter_title = f"{book_title} - {chapter_id} - {remove_invalid_characters(chapter_title)}"
            chapter_metadata.append([chapter_id, chapter_url, f"./books/raw/{book_title}/{file_chapter_title}.html"])
            
            chapter = self.create_epub_chapter(chapter_title, file_chapter_title, chapter_content, css)
            toc_list.append(chapter)
            new_epub.add_item(chapter)

        self.add_cover_image(book_title, new_epub)
        self.finalize_epub(new_epub, toc_list, book_title, chapter_metadata)

    async def save_images_in_chapter(self, img_urls, save_directory, image_count, new_epub):
        global gHeaders
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
        #logging.warning(img_urls)
        try:
            for img_url in img_urls:
                image_path = f"{save_directory}image_{image_count}.png"
                if not os.path.exists(image_path):
                    async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",}) as session:
                        if not isinstance(img_url,str):
                            img_url=img_url["src"]
                        async with session.get(img_url) as response:
                            if response.status == 200:
                                response=await response.content.read()
                                with open(image_path, "wb") as f:
                                    f.write(response)
                                    try:
                                        # Add image to EPUB
                                        epubImage=Image.open(image_path)
                                        b=io.BytesIO()
                                        epubImage.save(b,'png')
                                        image_data=b.getvalue()
                                        image_item = epub.EpubItem(uid=f"image_{image_count}", file_name=f"images/image_{image_count}.png", media_type="image/png", content=image_data)
                                        new_epub.add_item(image_item)
                                    except Exception as e:
                                        errorText=f"Failed to add image to epub. Function save_images_in_chapter Error: {e}"
                                        write_to_logs(errorText)
                                        continue
                                    image_count += 1
                await asyncio.sleep(0.5)
            return image_count
        except Exception as e:
            errorText=f"Failed to get save image. Function save_images_in_chapter Error: {e}"
            write_to_logs(errorText)
            


class SpaceBattlesEpubProducer(EpubProducer):
    async def spacebattles_fetch_chapter_list(self,url):
        scraper=SpaceBattlesScraper()
        return await scraper.fetch_chapter_list(url)
    
    async def spacebattles_remove_garbage_from_chapter(self,chapterContent):
        if not isinstance(chapterContent, bs4.element.Tag):
            logging.warning("chapterContent is not a BeautifulSoup Tag object.")
            return chapterContent  # Return as-is if it's not a valid object

        tags_to_remove = ["blockquote","button","noscript"]
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

    async def spacebattles_save_page_content(self,chapterContent,bookTitle,fileTitle):
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
        f.close()

    #Overrides existing produce_epub
    async def produce_epub(self,novelURL,bookTitle,css,new_epub):
        logging.warning('Starting produce_epub in overwritten method')
        already_saved_chapters = self.get_existing_order_of_contents(bookTitle)
        chapterMetaData=list()
        tocList=list()
        imageCount=0
        scraper=SpaceBattlesScraper()
        for pageNum in range(1, await self.spacebattles_fetch_chapter_list(novelURL)+1):
            await asyncio.sleep(1)
            page_url = f"{novelURL}page-{pageNum}/"
            
            logging.warning (page_url)
            #Retrieval does not work at the moment
            if check_if_chapter_exists(page_url, already_saved_chapters):
                chapter_id, dir_location = self.get_chapter_from_saved(pageNum, already_saved_chapters)
                page_content = self.get_chapter_contents_from_saved(dir_location)
                page_soup=bs4.BeautifulSoup(page_content,'html.parser')
                all_chapters=page_soup.find_all('div',{'id':'chapter-start'})
                for chapter_soup in all_chapters:
                    chapter_title=chapter_soup.find('title')
                    chapter_title=chapter_title.get_text()
                    images=chapter_soup.find_all('img')
                    images=[image['src'] for image in images]
                    currentImageCount=imageCount
                    if images:
                        for image in images:
                            try:
                                imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
                                epubImage=retrieve_stored_image(imageDir)
                                b=io.BytesIO()
                                epubImage.save(b,'png')
                                b_image1=b.getvalue()
                                
                                image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
                                new_epub.add_item(image_item)
                                currentImageCount+=1
                            except Exception as e:
                                errorText=f"Failed to add image to epub. Image does not exist, was never saved. Function spacebattles_produce_epub Error: {e}"
                                write_to_logs(errorText)
                                continue
                    imageCount=currentImageCount
                    chapter=epub.EpubHtml(title=chapter_title, file_name=f"{bookTitle} - {pageNum} - {chapter_title}.xhtml", lang='en')
                    chapter_content=chapter_soup.encode('ascii')
                    chapter.set_content(chapter_content)
                    chapter.add_item(css)
                    tocList.append(chapter)
                    new_epub.add_item(chapter)
                
                fileTitle=bookTitle+" - "+str(pageNum)
                chapterMetaData.append([pageNum,page_url,f"./books/raw/{bookTitle}/{fileTitle}.html"])
            else:
                soup=await scraper.get_soup(page_url)
                articles=soup.find_all("article",{"class":"message"})
                pageContent=""
                if (articles):
                    for article in articles:
                        threadmarkTitle=article.find("span",{"class":"threadmarkLabel"})
                        title=threadmarkTitle.get_text()
                        title=remove_tags_from_title(title)
                        logging.warning(title)
                        
                        chapterContent=article.find("div",{"class":"message-userContent"})
                        chapterContent=await self.spacebattles_remove_garbage_from_chapter(chapterContent)
                        
                        
                        hyperlinks=chapterContent.find_all('a',{'class':'link'})
                        
                        #Convert hyperlinked text into normal text with image appended after.
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
                                
                        #images=chapterContent.find_all('img')
                        #logging.warning(images)
                        images=[]
                        seen = set()
                        for image in chapterContent.find_all('img'):
                            # Get the image URL from 'src' or fallback to 'data-src'
                            img_url = image['src'] if re.match(r'^https?://', image.get('src', '')) else image.get('data-src', '')
                            # Add the URL to the list if it's valid and not already seen
                            if img_url and img_url not in seen:
                                images.append(img_url)
                                seen.add(img_url)
                        
                        imageDir=f"./books/raw/{bookTitle}/images/"
                        currentImageCount=imageCount
                        if (images):
                            imageCount=await self.save_images_in_chapter(images,imageDir,imageCount,new_epub)
                            for img,image in zip(chapterContent.find_all('img'),images):
                                # Ensure the 'src' attribute exists before replacing
                                if img.has_attr('src') and image:
                                    # Replace the 'src' attribute with the local path
                                    img['src'] = f"images/image_{currentImageCount}.png"
                                    currentImageCount += 1
                                # img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")       
                                # currentImageCount+=1
                        
                        chapter=epub.EpubHtml(title=title, file_name=f"{bookTitle} - {pageNum} - {title}.xhtml", lang='en')
                        stringChapterContent=str(chapterContent)
                        pageContent+=f"<div id='chapter-start'><title>{title}</title>{stringChapterContent}</div>"
                        
                        chapterContent=chapterContent.encode('ascii')
                        chapter.set_content(chapterContent)
                        chapter.add_item(css)
                        tocList.append(chapter)
                        new_epub.add_item(chapter)
                        
                        
                        
                fileTitle=bookTitle+" - "+str(pageNum)
                pageContent=bs4.BeautifulSoup(pageContent,'html.parser')
                
                await self.spacebattles_save_page_content(pageContent,bookTitle,fileTitle)
                chapterMetaData.append([str(pageNum),page_url,f"./books/raw/{bookTitle}/{fileTitle}.html"])
        
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
                logging.warning(f"There is no cover image:{e}")
        
        new_epub.toc=tocList
        new_epub.spine=tocList
        new_epub.add_item(epub.EpubNcx())
        new_epub.add_item(epub.EpubNav())
        
        self.write_order_of_contents(bookTitle, chapterMetaData)
        
        # logging.warning("Attempting to store epub")
        storeEpub(bookTitle, new_epub)

    
class FoxaholicEpubProducer(EpubProducer):
    async def fetch_chapter_list(self, url):
        scraper = FoxaholicScraper()
        return await scraper.fetch_chapter_list(url)

    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count, new_epub):
        scraper = FoxaholicScraper()
        soup = await scraper.get_soup(chapter_url)
        chapter_title = await scraper.fetch_chapter_title(soup)
        chapter_content = scraper.foxaholic_scrape_chapter_page(soup)

        # Save chapter content
        currentImageCount=image_count
        # Process images
        images=chapter_content.find_all('img')
        images=[image['src'] for image in images]
        logging.warning(images)
        image_dir = f"./books/raw/{book_title}/images/"
        if images:
            image_count = await self.save_images_in_chapter(images, image_dir, image_count, new_epub)
            for img,image in zip(chapter_content.find_all('img'),images):
                img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")       
                currentImageCount+=1
        
        encoded_chapter_content=chapter_content.encode('ascii')
        
        store_chapter(encoded_chapter_content.decode('utf-8'), book_title, chapter_title, chapter_id)

        return chapter_title, chapter_content, image_count
    
    #This grabs the first digit in the URL to treat as the ChapterID
    async def extract_chapter_ID(self, chapter_url):
        chapterID=chapter_url.split("/")
        chapterID=chapterID[len(chapterID)-2]
        chapterID=re.search(r'\d+',chapterID).group()
        return chapterID
    
class NovelBinEpubProducer(EpubProducer):
    async def fetch_chapter_list(self, url):
        scraper = NovelBinScraper()
        return await scraper.fetch_chapter_list(url)
    
    async def generate_chapter_title(self, chapter_id):
        chapter_id=int(chapter_id)
        
        volume_number=int(chapter_id//10000)
        chapter_number=int(chapter_id%10000)
        
        return f"V{volume_number}Ch{chapter_number}"
        
    
    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count, new_epub):
        scraper = NovelBinScraper()
        soup = await scraper.get_soup(chapter_url)
        chapter_title = await scraper.fetch_chapter_title(soup)
        chapter_title=await self.generate_chapter_title(chapter_id)+" "+chapter_title
        
        chapter_content = scraper.novelbin_scrape_chapter_page(soup)
        chapterInsert=f'<h1>{chapter_title}</h1>'
        chapter_content=chapterInsert+str(chapter_content)
        chapter_content=bs4.BeautifulSoup(chapter_content,'html.parser')
        # Save chapter content
        currentImageCount=image_count
        # Process images
        images=chapter_content.find_all('img')
        images=[image['src'] for image in images]
        logging.warning(images)
        image_dir = f"./books/raw/{book_title}/images/"
        if images:
            image_count = await self.save_images_in_chapter(images, image_dir, image_count, new_epub)
            for img,image in zip(chapter_content.find_all('img'),images):
                img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")       
                currentImageCount+=1
        
        encoded_chapter_content=chapter_content.encode('ascii')
        store_chapter(encoded_chapter_content, book_title, chapter_title, chapter_id)

        return chapter_title, chapter_content, image_count
    
    
    
    #This grabs the numbers in the URL to treat as the ChapterID.
    #And modifies the chapterID to be a unique increasing number
    #The first number represents the volume if it exists, and the subsequent digits represent the order of the chapters
    async def extract_chapter_ID(self, chapter_url):
        chapterID=chapter_url.split("/")
        chapterID=chapterID[len(chapterID)-1]
        first_number=10000
        if "vol-" in chapterID:
            first_number=re.search(r'\d+',chapterID)
            if (first_number):
                first_number=first_number.group()
            chapterID = re.sub(r'vol-+\d', '', chapterID)
        if "volume-" in chapterID:
            first_number=re.search(r'\d+',chapterID)
            if (first_number):
                first_number=first_number.group()
            chapterID = re.sub(r'volume-+\d', '', chapterID)
        chapterID=re.search(r'\d+',chapterID).group()
        chapterID=int(first_number)*10000+int(chapterID)
        return str(chapterID)

class RoyalRoadEpubProducer(EpubProducer):
    async def fetch_chapter_list(self, url):
        scraper = RoyalRoadScraper()
        return await scraper.fetch_chapter_list(url)

    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count, new_epub):
        scraper = RoyalRoadScraper()
        soup = await scraper.get_soup(chapter_url)
        #logging.warning(soup)
        chapter_title = await scraper.fetch_chapter_title(soup)
        #logging.warning(chapter_title)
        chapter_content = await scraper.fetch_chapter_content(soup)
        # Save chapter content
        currentImageCount=image_count
        # Process images
        images=chapter_content.find_all('img')
        images=[image['src'] for image in images]
        logging.warning(images)
        image_dir = f"./books/raw/{book_title}/images/"
        if images:
            image_count = await self.save_images_in_chapter(images, image_dir, image_count, new_epub)
            for img,image in zip(chapter_content.find_all('img'),images):
                img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")       
                currentImageCount+=1
        
        encoded_chapter_content=chapter_content.encode('ascii')
        
        store_chapter(encoded_chapter_content, book_title, chapter_title, chapter_id)

        return chapter_title, chapter_content, image_count

    #Extracts the chapter ID from the URL. Royalroad has unique IDs that increase with each chapter.
    async def extract_chapter_ID(self,chapter_url):
        return chapter_url.split("/")[-2]


def create_epub_directory_url(bookTitle):
    dirLocation="./books/epubs/"+bookTitle+"/"+bookTitle+".epub"
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


async def main_interface(url, cookie):
    try:
        if (cookie):
            setCookie(cookie)
        epub_producer = None
        if "royalroad.com" in url:
            epub_producer = RoyalRoadEpubProducer()
        elif "foxaholic.com" in url:
            epub_producer = FoxaholicEpubProducer()
        elif "novelbin.com" in url or "novelbin.me" in url:
            epub_producer= NovelBinEpubProducer()
        elif "spacebattles.com" in url:
            epub_producer=SpaceBattlesEpubProducer()
            normalized_url = url if url.endswith('/') else url + '/'
            if re.search(r'/reader/page-\d+/$',normalized_url):
             url = re.sub(r'/reader/page-\d+/?$', '/reader/', url)
            elif not url.rstrip('/').endswith('/reader'):
                if url.endswith('/'):
                    url += 'reader/'
                else:
                    url += '/reader/'
        else:
            raise ValueError("Unsupported website")
        logging.warning(url)
        logging.warning('Creating scraper')
        scraper=ScraperFactory.get_scraper(url)
        logging.warning('Fetching novel data')
        bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter= await scraper.fetch_novel_data(url)
        
        
        
        new_epub=epub.EpubBook()
        new_epub.set_identifier(bookID)
        new_epub.set_title(bookTitle)
        new_epub.set_language('en')
        new_epub.add_author(bookAuthor)
        style=open("style.css","r").read()
        default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)
        new_epub.add_item(default_css)
        #if (check_existing_book(bookID) or check_existing_book_Title(bookTitle)):
            #if not (check_latest_chapter(bookID,bookTitle,latestChapter)):
                #pass
        logging.warning('Producing epub')
        logging.warning(url)
        await epub_producer.produce_epub(url, bookTitle,default_css,new_epub)
        rooturl=""
        match = re.search(r"https://(?:www\.)?([A-Za-z0-9.-]+)", url)
        if match:
            rooturl=match.group(1)
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
    
    
    except ValueError as e:
        logging.error(f"Error: {e}")
        
#link="https://novelbin.com/b/raising-orphans-not-assassins"
#link="https://www.royalroad.com/fiction/54046/final-core-a-holy-dungeon-core-litrpg"
#link="https://forums.spacebattles.com/threads/the-factory-must-wo-wo-class-abyssal-si.1221239/"
link="https://forums.spacebattles.com/threads/salvage-sarcasm-and-submarines-a-kancolle-fic.836982/reader/page-18"
asyncio.run(main_interface(link, None))
