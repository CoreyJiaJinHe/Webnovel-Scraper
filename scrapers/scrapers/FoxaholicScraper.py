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
from common import(
    interception,
    write_to_logs,
    generate_new_ID,
    remove_tags_from_title,
    check_directory_exists,
    make_directory,
    remove_invalid_characters
)


class FoxaholicScraper(Scraper):
    async def get_soup(self,url):
        try:
            driver = webdriver.Firefox()
            driver.request_interceptor=interception
            driver.get(url)
            soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
            driver.close()
            for script in soup(["script", "style"]):
                script.decompose()    # rip it out
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

    