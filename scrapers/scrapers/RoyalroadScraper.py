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


from common import (
    write_to_logs,
    check_directory_exists,
    make_directory,
    remove_invalid_characters,
    remove_tags_from_title,
)

import Scraper
    
    
class RoyalRoadScraper(Scraper):
    async def fetch_novel_data(self, url):
        # RoyalRoad-specific logic
        return await self.RoyalRoad_Fetch_Novel_Data(url)
    
    async def RoyalRoad_Fetch_Novel_Data(self,novelURL):
        soup=await self.get_soup(novelURL)
        if (soup):
            try:
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

