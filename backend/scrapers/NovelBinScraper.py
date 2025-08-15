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




class NovelBinScraper(Scraper):
    async def get_soup(self,url):
        try:
            driver = webdriver.Firefox()
            driver.request_interceptor=self.interception
            driver.install_addon(path_to_extension, temporary=True)
            driver.get(url)
            await asyncio.sleep(2) #Sleep is necessary because of the javascript loading elements on page
            soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
            driver.close()
            for script in soup(["script", "style"]):
                script.decompose()    # rip it out
            return soup
        except Exception as error:
            errorText=f"Failed to get soup from url. Function novelbin_get_soup Error: {error}"
            write_to_logs(errorText)
    
    #THIS FUNCTION IS UNIQUE TO NOVELBIN
    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count):
        soup = await self.get_soup(chapter_url)
        chapter_title = await self.fetch_chapter_title(soup)
        chapter_title=await self.generate_chapter_title(chapter_id)+" "+chapter_title
        chapter_content = await self.fetch_chapter_content(soup)
        
        chapter_content = await self.check_and_insert_missing_chapter_title(chapter_title, chapter_content)
        currentImageCount=image_count
        
        # Process images
        images=chapter_content.find_all('img')
        images=[image['src'] for image in images]
        image_dir = f"./books/raw/{book_title}/images/"
        if images:
            logging.warning(f"Images found in chapter content.{chapter_url}")
            image_count = await self.save_images_in_chapter(images, image_dir, image_count)
            for img,image in zip(chapter_content.find_all('img'),images):
                img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")       
                currentImageCount+=1
        else:
            logging.warning("No images found in chapter content.")
        encoded_chapter_content=chapter_content.encode('ascii')
        file_chapter_title = f"{book_title} - {chapter_id} - {remove_invalid_characters(chapter_title)}"
        store_chapter(encoded_chapter_content, book_title, chapter_title, chapter_id)

        return file_chapter_title, currentImageCount
    

    async def fetch_novel_data(self, novelURL):
        #CHECK: There is a problem with the title, it is getting cut off by commas
        try:
            soup=await self.get_soup(novelURL)
            
            bookTitle=soup.find("h3",{"class":"title"})
            bookTitle=bookTitle.get_text()
            bookTitle=remove_tags_from_title(bookTitle)
            logging.warning(bookTitle)
            
            bookID=str(generate_new_ID(bookTitle, "novelbin.com"))
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
            description=descriptionBox.find("div",{"class":"desc-text"})
            description=description.get_text()

            if (description.startswith("Description: ")):
                description=description[13:]
            description=description.strip()
            if ("\n" in description):
                description=description.replace("\n","")
            if ("  " in description):
                description=description.replace("  "," ")
            
            lastScraped=datetime.datetime.now()
            
            latestChapter = soup.find("div", {"class":"l-chapter"})
            latestChapterTitle=latestChapter.find("a")
            latestChapterTitle=latestChapterTitle.get_text()
            latestChapterTitle=remove_tags_from_title(latestChapterTitle)
            latestChapterID=await self.extract_chapter_ID(latestChapter.find("a")["href"])
            
            
        except Exception as error:
            errorText=f"Failed to get novel data. Function novelbin-fetch_novel_data Error: {error}"
            write_to_logs(errorText)
        
        try:
            img_url = soup.find("img",{"class":"lazy"})
            if (img_url):
                saveDirectory=f"./books/raw/{bookTitle}/"
                if not (check_directory_exists(f"./books/raw/{bookTitle}/cover_image.png")):
                    try:
                        await self.fetch_cover_image("cover_image",img_url,saveDirectory)
                    except Exception as e:
                        errorText=f"Failed to get cover image. There might be no cover. Or a different error. Function novelbin_fetch_novel_data Error: {e}"
                        write_to_logs(errorText)
        except Exception as error:
            errorText=f"Failed to find image, or save it. There might be no cover. Or a different error. Function novelbin_fetch_novel_data Error: {error}"
            write_to_logs(errorText)
            
        return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle,latestChapterID


    async def fetch_cover_image(self,title,img_url,saveDirectory):
        async with aiohttp.ClientSession(headers = self.basicHeaders
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
    
    async def fetch_chapter_title_list(self, url):
        soup = await self.get_soup(f"{url}#tab-chapters-title")
        
        try:
            #logging.warning(soup)
            chapterTable = soup.find("div", {"id": "list-chapter"})
            #logging.warning(chapterTable)
            rows= chapterTable.find_all("li")
            
            chapterListTitles=list()
            for row in rows[:len(rows)]:
                processChapterURL=row.find("a")
                chapterTitle=processChapterURL.get_text()
                chapterTitle=remove_invalid_characters(chapterTitle)
                chapterListTitles.append(chapterTitle)
            #logging.warning(chapterListURL)
            return chapterListTitles
        except Exception as error:
            errorText=f"Failed to get chapter titles from chapter list of page. Function novelbin_get_chapter_title_list Error: {error}"
            write_to_logs(errorText)
    
    
    async def fetch_chapter_content(self, soup):
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

    async def process_new_book(self, book_url,book_title):
        listofChapters= await self.fetch_chapter_list(book_url)
        if not listofChapters:
            errorText="Function: process_new_book. Error: No chapters found in the bookURL. Please check the URL or the book's availability."
            logging.warning(errorText)
            write_to_logs(errorText)
            return
        existingChapters= self.get_existing_order_of_contents(book_title)

        chapter_metadata = []
        image_counter=0 
        for chapter_url in listofChapters:
            chapter_id = await self.extract_chapter_ID(chapter_url)

            if (self.check_if_chapter_exists(chapter_id, existingChapters)):
                for line in existingChapters:
                    logging.warning("This is the line from the file")
                    logging.warning(line)
                    if line.startswith(f"{chapter_id};"):
                        logging.warning(f"Chapter {chapter_id} already exists. Skipping.")
                        chapter_metadata.append(line.strip().split(";"))
                        break
                continue
            
            file_chapter_title, image_counter = await self.process_new_chapter(chapter_url, book_title, chapter_id, image_counter)
            logging.warning(f"Processed chapter: {file_chapter_title}")
            logging.warning(f"Chapter URL: {chapter_url}")
            logging.warning(f"Chapter ID: {chapter_id}")
            logging.warning(f"File chapter title: {file_chapter_title}")
            chapter_metadata.append([chapter_id, chapter_url, f"./books/raw/{book_title}/{file_chapter_title}.html"])
            
        self.write_order_of_contents(book_title,chapter_metadata)

    async def generate_chapter_title(self, chapter_id):
        chapter_id=int(chapter_id)
        
        volume_number=int(chapter_id//10000)
        chapter_number=int(chapter_id%10000)
        
        return f"V{volume_number}Ch{chapter_number}"
    
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

    async def query_site(self, title, additionalConditions,cookie):
        if (self.basicHeaders.get("Cookie") is None and cookie is None):
            errorText=f"Failed to search title. Function query_site Error: Cookie is required for NovelBin. Please provide a cookie."
            logging.warning(errorText)
            write_to_logs(errorText)
            return None
        if (cookie):
            self.basicHeaders["Cookie"]=cookie

        return await self.query_novelbin(title)
        
        
    async def query_novelbin(self, title):
        if (title.isspace() or title==""):
            errorText=f"Failed to search title. Function query_novelbin Error: No title inputted"
            write_to_logs(errorText)
            return "Invalid Title"
        querylink=f"https://novelbin.com/search?keyword={title}"
        soup= await self.get_soup(querylink)
        try:
            resultContainer=soup.find ("div",{"class":"list-novel"})
            if not resultContainer:
                errorText=f"Failed to find result container. Function query_novelbin Error: No results found for the title {title}"
                write_to_logs(errorText)
                return "No Results Found"
            resultRows=resultContainer.find_all("div",{"class":"row"})
            bookTitles=resultRows.find_all("h3",{"class":"novel-title"})
            bookLinks=resultRows.find_all("a",{"class":"novel-link"})
            firstResult=bookLinks[0]["href"]
            return firstResult
        except Exception as error:
            errorText=f"Failed to query novelbin. Function query_novelbin Error: {error}"
            write_to_logs(errorText)
            return "Error Occurred"
    

    
    async def process_new_chapter_non_saved(self, chapter_url, book_title, chapter_id, image_count):
        try:
            soup = await self.get_soup(chapter_url)
            chapter_title = await self.fetch_chapter_title(soup)
            chapter_title= await self.generate_chapter_title(chapter_id)+" "+chapter_title
            chapter_content = await self.fetch_chapter_content(soup)
            chapter_content = await self.remove_junk_links_from_soup(chapter_content)
            
            chapter_content = await self.check_and_insert_missing_chapter_title(chapter_title, chapter_content)
            
            

            
            #logging.warning(chapter_content)
            #logging.warning(chapter_title)
            currentImageCount=image_count
            # Process images
            images=chapter_content.find_all('img')
            images=[image['src'] for image in images]
            logging.warning("The warning below is for images.")
            logging.warning(images)
            #Do not save these images permanent. Always overwrite.
            image_dir = f"./books/raw/temporary/images/"
            if images:
                image_count = await self.save_images_in_chapter(images, image_dir, image_count)
                for img,image in zip(chapter_content.find_all('img'),images):
                    img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")       
                    currentImageCount+=1
            
            file_chapter_title = f"{book_title} - {chapter_id} - {remove_invalid_characters(chapter_title)}"
            
            return file_chapter_title, currentImageCount, chapter_content
        except Exception as e:
            errorText=f"Failed to process new chapter. Function process_new_chapter_non_saved Error: {e}"
            write_to_logs(errorText)
        
        