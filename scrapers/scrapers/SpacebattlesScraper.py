import bs4
import re
import os, errno
import datetime
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
from common import (
    remove_tags_from_title,
    check_directory_exists,
    write_to_logs,
    make_directory,
)




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
    
    
    

    