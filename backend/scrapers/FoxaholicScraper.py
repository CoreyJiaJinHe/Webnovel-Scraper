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
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
logging.getLogger('seleniumwire').setLevel(logging.WARNING)
firefox_options = FirefoxOptions()

# Path to .xpi extension file
path_to_extension = os.getenv("LOCAL_ADBLOCK_EXTENSION")

from backend.scrapers.Scraper import Scraper
from backend.common import(
    write_to_logs, 
    check_directory_exists, 
    make_directory, 
    remove_tags_from_title, 
    store_chapter, 
    retrieve_cover_from_storage, 
    storeEpub,
    get_first_last_chapter,
    remove_invalid_characters,
    create_epub_directory_url,
    
    generate_new_ID
)



class FoxaholicScraper(Scraper):
    def __init__(self, cookie=None):
        super().__init__()
        self.cookie = cookie  # Store the cookie for later use
    
        
    async def get_soup(self,url):
        try:
            driver = webdriver.Firefox(options=firefox_options)
            driver.install_addon(path_to_extension, temporary=True)
            driver.request_interceptor=self.interception
            driver.get(url)
            soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
            driver.close()
            return soup
        except Exception as error:
            errorText=f"Failed to get soup Function foxaholic_get_soup Error: {error}"
            write_to_logs(errorText)
        return None
    
    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count):
        soup = await self.get_soup(chapter_url)
        chapter_title = await self.fetch_chapter_title(soup)
        chapter_content = await self.fetch_chapter_content(soup)
        chapter_content = await self.check_and_insert_missing_chapter_title(chapter_title, chapter_content)
        currentImageCount=image_count
        # Process images
        images=chapter_content.find_all('img')
        images=[image['src'] for image in images]
        logging.warning(images)
        image_dir = f"./books/raw/{book_title}/images/"
        if images:
            image_count = await self.save_images_in_chapter(images, image_dir, image_count)
            for img,image in zip(chapter_content.find_all('img'),images):
                img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")       
                currentImageCount+=1
        
        encoded_chapter_content=chapter_content.encode('ascii')
        file_chapter_title = f"{book_title} - {chapter_id} - {remove_invalid_characters(chapter_title)}"
        store_chapter(encoded_chapter_content, book_title, chapter_title, chapter_id)

        return file_chapter_title, currentImageCount

    async def fetch_novel_data(self, novelURL):
        try:
            soup=await self.get_soup(novelURL)
            
            bookData=soup.find("div",{"class":"post-content"})
            novelData=bookData.find_all("div",{"class":"summary-content"}) or bookData.find_all("div",{"class":"summary_content"})

            bookTitle=soup.find("div",{"class":"post-title"}).get_text() or soup.find("div",{"class":"post_title"}).get_text()
            bookAuthor=novelData[2].get_text()
            #logging.warning(bookTitle)
            bookTitle=remove_tags_from_title(bookTitle)
            
            bookID=str(generate_new_ID(bookTitle,"foxaholic.com"))
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
            latestChapterTitle=latestChapter.find("a")
            latestChapterTitle=latestChapterTitle.get_text()
            latestChapterTitle=remove_tags_from_title(latestChapterTitle)
            href=latestChapter.find("a")["href"]
            latestChapterID=self.extract_chapter_ID(href)
            
            try:
                img_url = soup.find("div",{"class":"summary_image"}).find("img")
                if (img_url):
                    saveDirectory=f"./books/raw/{bookTitle}/"
                    if not (check_directory_exists(f"./books/raw/{bookTitle}/cover_image.png")):
                        try:
                            await self.fetch_cover_image("cover_image",img_url,saveDirectory)
                        except Exception as e:
                            errorText=f"Failed to get cover image. There might be no cover. Or a different error. Function foxaholic_fetch_novel_data Error: {e}"
                            write_to_logs(errorText)
            except Exception as e:
                errorText=f"Failed to get cover image. There might be no cover. Or a different error. Function foxaholic_fetch_novel_data Error: {e}"
                write_to_logs(errorText)
                
                            
            return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle,latestChapterID
        except Exception as error:
            errorText=f"Failed to extract noveldata from soup. Function foxaholic_fetch_novel_data Error: {error}"
            write_to_logs(errorText)
        return None


    async def fetch_cover_image(self,title,img_url,saveDirectory):
        try:
            driver = webdriver.Firefox()
            driver.request_interceptor=self.interception
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
        soup = await self.get_soup(url)
        
        try:
            #logging.warning(soup)
            chapterTable = soup.find_all("ul",class_='main version-chap no-volumn')[0]
            #logging.warning(chapterTable)
            rows= chapterTable.find_all("li", {"class":"wp-manga-chapter free-chap"})
            chapterListURL=list()
            for row in rows[0:len(rows)]:
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
            
    async def fetch_chapter_title_list(self, url):
        soup = await self.get_soup(f"{url}#tab-chapters-title")
        
        try:
            #logging.warning(soup)
            chapterTable = soup.find_all("ul",class_='main version-chap no-volumn')[0]
            #logging.warning(chapterTable)
            rows= chapterTable.find_all("li", {"class":"wp-manga-chapter free-chap"})
            
            chapterListTitles=list()
            for row in rows[:len(rows)]:
                chapterData=row.find("a").contents[0].strip()
                chapterTitle=chapterData
                chapterTitle=remove_invalid_characters(chapterTitle)
                chapterListTitles.append(chapterTitle)
            #logging.warning(chapterListURL)
            chapterListTitles=list(reversed(chapterListTitles))
            return chapterListTitles
        except Exception as error:
            errorText=f"Failed to get chapter titles from chapter list of page. Function foxaholic_get_chapter_title_list Error: {error}"
            write_to_logs(errorText)
    
    async def fetch_chapter_content(self, soup):
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
    #This grabs the first digit in the URL to treat as the ChapterID
    def extract_chapter_ID(self, chapter_url):
        chapterID=chapter_url.split("/")
        chapterID=chapterID[len(chapterID)-2]
        chapterID=re.search(r'\d+',chapterID).group()
        return chapterID
    
    async def process_new_book(self, book_url,book_title):
        listofChapters = await self.fetch_chapter_list(book_url)
        logging.warning(f"List of chapters:")
        logging.warning(listofChapters)
        if not listofChapters:
            errorText="Function: process_new_book. Error: No chapters found in the bookURL. Please check the URL or the book's availability."
            logging.warning(errorText)
            write_to_logs(errorText)
            return
        existingChapters = self.get_existing_order_of_contents(book_title)
        chapter_metadata=[]
        image_counter=0

        for chapter_url in listofChapters:
            chapter_id = self.extract_chapter_ID(chapter_url)
            if (self.check_if_chapter_exists(chapter_id, existingChapters)):
                for line in existingChapters:
                    if line.startswith(f"{chapter_id};"):
                        logging.warning(f"Chapter {chapter_id} already exists. Skipping.")
                        chapter_metadata.append(line.strip().split(";"))
                continue
            await asyncio.sleep(1)
            file_chapter_title,image_counter= await self.process_new_chapter(chapter_url, book_title, chapter_id, image_counter)
            chapter_metadata.append([chapter_id, chapter_url, f"./books/raw/{book_title}/{file_chapter_title}.html"])
        self.write_order_of_contents(book_title, chapter_metadata)
    
    
    async def process_new_chapter_non_saved(self, chapter_url, book_title, chapter_id, image_count):
        try:
            soup = await self.get_soup (chapter_url)
            chapter_title=await self.fetch_chapter_title(soup)
            chapter_content=await self.fetch_chapter_content(soup)
            chapter_content= await self.remove_junk_links_from_soup(chapter_content)
            chapter_content = await self.check_and_insert_missing_chapter_title(chapter_title, chapter_content)
            currentImageCount=image_count
            # Process images
            images=chapter_content.find_all('img')
            images=[image['src'] for image in images]
            image_dir=f"./books/raw/{book_title}/images/"
            if images:
                image_count=await self.save_images_in_chapter(images, image_dir, image_count)
                for img,image in zip(chapter_content.find_all('img'),images):
                    img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")       
                    currentImageCount+=1
            
            file_chapter_title = f"{book_title} - {chapter_id} - {remove_invalid_characters(chapter_title)}"
            return file_chapter_title, currentImageCount, chapter_content
        except Exception as e:
            errorText=f"Failed to process new chapter. Function foxaholic_process_new_chapter_non_saved Error: {e}"
            write_to_logs(errorText)
            return None, image_count, None
        
                    
            
        