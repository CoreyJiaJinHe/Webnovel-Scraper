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

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from seleniumwire import webdriver

import Scraper
from common import(
    interception,
    write_to_logs,
    generate_new_ID,
    remove_tags_from_title,
    check_directory_exists,
    make_directory,
    remove_invalid_characters,
    basicHeaders
)






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
        async with aiohttp.ClientSession(headers = basicHeaders
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
