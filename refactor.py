

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







#: DONE Fuzzy search for if input is not link. If input is Title, send query, get results.
#API:https://www.royalroad.com/fictions/search?globalFilters=false&title=test&orderBy=popularity
#https://www.royalroad.com/fictions/search?globalFilters=false&title=test
#Two versions. Popularity, and Relevance.
#Relevance to get best possible match.
#Popularity for when results have similar names.


#div class="fiction-list"
#div class= "row fiction-list-item"
#h2 class="fiction-title"
#a href format="/fiction/#####/title"





import bs4
import re
import os, errno
import datetime
import logging
import asyncio
import io
from word2number import w2n

from ebooklib import epub 
from PIL import Image, ImageChops
import aiohttp
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
load_dotenv(env_path, override=True)
logLocation=os.getenv("logs")

# Add these missing imports:
from scrapers.common import (
    write_to_logs, 
    check_directory_exists, 
    make_directory, 
    remove_tags_from_title, 
    store_chapter, 
    retrieve_cover_from_storage, 
    storeEpub, 
    basicHeaders,
    
    setCookie,
    get_first_last_chapter,
    remove_invalid_characters,
    create_epub_directory_url,
    
    interception,
    generate_new_ID
)


from mongodb import(
    check_existing_book,
    check_existing_book_Title,
    check_latest_chapter,
    check_recently_scraped,
    create_Entry, 
    create_latest,
    get_all_book_titles,
    get_Entry_Via_Title,
    update_entry
)



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

# When creating the driver:
#driver = webdriver.Firefox(options=firefox_options)
#driver.install_addon(path_to_extension, temporary=True)





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
    






class RoyalRoadScraper():
    async def get_soup(self,url):
        try:
            async with aiohttp.ClientSession(headers = basicHeaders) as session:
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
    
    
    
    async def fetch_novel_data(self, novelURL):
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
                
                bookTitle=remove_invalid_characters(bookTitle)
                        
                description=soup.find("div",{"class":"description"}).get_text()
                if ("\n" in description):
                    description=description.replace("\n"," ")
                if ("  " in description):
                    description=description.replace("  "," ")
                lastScraped=datetime.datetime.now()
                
                chapterTable=soup.find("table",{"id":"chapters"})
                rows=chapterTable.find_all("tr")
                
                latestChapter = rows[-1]
                first_a = latestChapter.find("a")
                if first_a:
                    latestChapterTitle = first_a.get_text(strip=True)
                else:
                    latestChapterTitle = ""
                latestChapterTitle=remove_invalid_characters(latestChapterTitle)
                href=first_a["href"]
                latestChapterID=re.search(r'/fiction/(\d+)/', href).group(1)
                #logging.warning(f"Latest chapter title: {latestChapterTitle}")
                
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
                return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle,latestChapterID
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
        soup=await self.get_soup(url)
        try:
            chapterTable=soup.find("table",{"id":"chapters"})
            rows=chapterTable.find_all("tr")
            
            rooturl=re.search("https://([A-Za-z]+(.[A-Za-z]+)+)/",url)
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
    
    async def fetch_chapter_title_list(self,url):
        soup=await self.get_soup(url)
        try:
            chapterTable=soup.find("table",{"id":"chapters"})
            rows=chapterTable.find_all("tr")
            chapterListTitles=list()
            for row in rows[1:len(rows)]:
                processChapterURL=row.find("a")
                #Process into shortened link
                chapterListTitles.append(processChapterURL.get_text().strip())
            return chapterListTitles
        except Exception as error:
            errorText=f"Failed to get soup for processing. Function RoyalRoad_fetch_chapter_title_list Error: {error}"
            write_to_logs(errorText)

    
    async def fetch_chapter_content(self, soup):
        chapterContent = soup.find("div", {"class": "chapter-inner chapter-content"})
        
        if soup is None:
            errorText=f"Failed to get soup for processing. Function RoyalRoad_Fetch_Chapter Error: No soup"
            write_to_logs(errorText)
            return None
        elif chapterContent is None:
            errorText=f"Failed to get content. Function RoyalRoad_Fetch_Chapter Error: Soup has no chapter-inner"
            write_to_logs(errorText)
            return None
        return chapterContent#.encode('ascii')
    
    async def query_site(self,title,additionalConditions, cookie):
        option = additionalConditions.get("sort_by", None)
        return await self.query_royalroad(title,option)
    
    #option takes two values. None for default. "popularity" for popularity.
    async def query_royalroad(self,title, option):
        if (title.isspace() or title==""):
            errorText=f"Failed to search title. Function query_royalroad Error: No title inputted"
            write_to_logs(errorText)
            return "Invalid Title"
            
        if (option is None):
            querylink = f"https://www.royalroad.com/fictions/search?globalFilters=false&title={title}"
        elif (option == "popularity"):
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

    async def process_new_book(self, book_url,book_title):
        listofChapters= await self.fetch_chapter_list(book_url)
        if not listofChapters:
            errorText="Function: process_new_book. Error: No chapters found in the bookURL. Please check the URL or the book's availability."
            logging.warning(errorText)
            write_to_logs(errorText)
            return
        existingChapters = self.get_existing_order_of_contents(book_title)
        
        chapter_metadata = []
        image_counter=0 
        for chapter_url in listofChapters:
            chapter_id = await self.extract_chapter_ID(chapter_url)
            
            if (self.check_if_chapter_exists(chapter_id, existingChapters)):
                for line in existingChapters:
                    logging.warning("This is the line from the file")
                    logging.warning(line)
                    if line.startswith(f"{chapter_id};"):
                        chapter_metadata.append(line)
                    
                    break
                continue
            file_chapter_title,image_counter=await self.process_new_chapter(chapter_url, book_title, chapter_id,image_counter)
            chapter_metadata.append([chapter_id, chapter_url, f"./books/raw/{book_title}/{file_chapter_title}.html"])
        
        self.write_order_of_contents(book_title,chapter_metadata)
        
    async def remove_junk_links(self, chapter_content):
        hyperlinks=chapter_content.find_all('a',{'class':'link'})
        for link in hyperlinks:
            if ("emoji" in link):
                link.extract() #Remove emoji links
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
                chapter_content=bs4.BeautifulSoup(str(chapter_content),'html.parser')
        return chapter_content
    
    #TODO: Working on creating a new function to generate an epub with the selected chapters without actually storing them into the repository.
    async def process_new_chapter_non_saved(self, chapter_url, book_title,chapter_id,image_count):
        try:
            soup = await self.get_soup(chapter_url)
            chapter_title = await self.fetch_chapter_title(soup)
            chapter_content = await self.fetch_chapter_content(soup)
            chapter_content = await self.remove_junk_links(chapter_content)
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
        
    

    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count):
        soup = await self.get_soup(chapter_url)
        chapter_title = await self.fetch_chapter_title(soup)
        chapter_content = await self.fetch_chapter_content(soup)
        chapter_content = await self.remove_junk_links(chapter_content)
        
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
    
    async def save_images_in_chapter(self, img_urls, save_directory, image_count):
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
                        image_count += 1
                await asyncio.sleep(0.5)
            return image_count
        except Exception as e:
            errorText=f"Failed to get save image. Function save_images_in_chapter Error: {e}"
            write_to_logs(errorText)
            
            
    #Extracts the chapter ID from the URL. Royalroad has unique IDs that increase with each chapter.
    async def extract_chapter_ID(self,chapter_url):
        return chapter_url.split("/")[-2]
        

    
    def write_order_of_contents(self, book_title, chapter_metadata):
        file_location = f"./books/raw/{book_title}/order_of_chapters.txt"
        logging.warning(chapter_metadata)
        with open(file_location, "w") as f:
            for data in chapter_metadata:
                if isinstance(data, str):
                    data = data.strip().split(";")
                logging.warning(data)
                f.write(";".join(map(str, data))+ "\n")

    
    #These two function are from epubproducer. They may become a 'common' function
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


class RoyalRoadEpubProducer():
    
    #TODO: DONE This needs modifying
    async def retrieve_images_in_chapter(self,images_url,image_dir,image_count,new_epub):
        current_image_count=image_count
        try:
            for img_url in images_url:
                image_path=f"{image_dir}/{img_url}"
                epubImage=Image.open(image_path)
                if (epubImage):
                    try:
                        b=io.BytesIO()
                        epubImage.save(b,'png')
                        b_image1=b.getvalue()
                        
                        image_item=epub.EpubItem(uid=f'image_{current_image_count}',file_name=f'images/image_{current_image_count}.png', media_type='image/png', content=b_image1)
                        new_epub.add_item(image_item)
                    except Exception as error:
                        errorText=f"Failed to add image to epub. Function retrieve_images_in_chapter. Error: {error}. Possibly image is corrupted or not saved at all."
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

    #this might become a common function
    #Nevermind. This one is different. It's not extracting the ID from the URL but frm the internal storage.
    def extract_chapter_ID(self, chapter_url):
        return chapter_url.split(";")[0]

    def extract_chapter_title(self, dir_location):
        return os.path.basename(dir_location).split(" - ")[-1].replace(".html", "")

    def create_epub_chapter(self, chapter_title,file_chapter_title,chapter_content, css):
        try:

            if not isinstance(chapter_content, str):
                chapter_content = str(chapter_content)
            #chapter_content=chapter_content.encode('ascii')
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
            b=io.BytesIO()
            try:
                img.save(b,'png')
                b_image=b.getvalue()
                cover_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image)
                new_epub.add_item(cover_item)
            except Exception as e:
                errorText=f"Failed to add cover image to epub. Function add_cover_image Error: {e}"
                logging.warning(errorText)
                write_to_logs(errorText)

    def finalize_epub(self, new_epub, toc_list, book_title):
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
                if isinstance(data, str):
                    data = data.strip().split(";")
                logging.warning(data)
                f.write(";".join(map(str, data))+ "\n")

    async def produce_epub(self, book_title, css, new_epub):
        already_saved_chapters = self.get_existing_order_of_contents(book_title)
        toc_list = []
        image_count = 0
        logging.warning("Producing epub for book, grabbing chapters")
        for chapter_url in already_saved_chapters:
            chapter_id = self.extract_chapter_ID(chapter_url)
            chapter_id, dir_location = self.get_chapter_from_saved(chapter_id, already_saved_chapters)
            chapter_content = self.get_chapter_contents_from_saved(dir_location)
            chapter_title = self.extract_chapter_title(dir_location)
            logging.warning(chapter_title)
            chapter_content_soup=bs4.BeautifulSoup(chapter_content,'html.parser')
            
            images=chapter_content_soup.find_all('img')
            images=[image['src'] for image in images]
            image_dir = f"./books/raw/{book_title}/"
            if images:
                image_count=await self.retrieve_images_in_chapter(images, image_dir,image_count,new_epub)
            
            file_chapter_title = f"{book_title} - {chapter_id} - {remove_invalid_characters(chapter_title)}"
            chapter = self.create_epub_chapter(chapter_title, file_chapter_title, chapter_content, css)
            toc_list.append(chapter)
            new_epub.add_item(chapter)

        logging.warning("Adding cover image")
        try:
            self.add_cover_image(book_title, new_epub)
        except Exception as e:
            errorText=f"Failed to add cover image. Function add_cover_image Error: {e}"
            write_to_logs(errorText)
        
        logging.warning("Finalizing epub")
        self.finalize_epub(new_epub, toc_list, book_title)

    
    #TODO: Working on creating a new function to generate an epub with the selected chapters without actually storing them into the repository.
    #DONE? TODO: Fix this. This is currently broken with an 'NoneType' error.
    #
    #Create an adaptor/interface for the produce_custom_epub functions
    async def produce_custom_epub_interface(self, new_epub, book_title, css,book_chapter_urls, mainBookURL,additionalConditions, cookie):
        scraper=RoyalRoadScraper()
        return await self.produce_custom_epub(new_epub, book_title, css, book_chapter_urls, mainBookURL, additionalConditions, scraper)
    
        
    async def produce_custom_epub(self, new_epub, book_title, css, book_chapter_urls, mainBookURL, additionalConditions, scraper):
        if not book_chapter_urls:
            errorText="Function: royalroad_produce_custom_epub. Error: No chapters found in the bookURL. Please check the URL or the book's availability."
            logging.warning(errorText)
            write_to_logs(errorText)
            return
        
        
        toc_list = []
        image_counter=0
        current_image_counter=0
        try:
            for chapter_url in book_chapter_urls:
                logging.error(chapter_url)
                soup = await scraper.get_soup(chapter_url)
                #write_to_logs(str(soup).encode("ascii", "ignore").decode("ascii"))
                
                def extract_chapter_ID(chapter_url):
                    import re
                    match = re.search(r'/(\d+)/?$', chapter_url)
                    if match:
                        return match.group(1)

                chapter_id = extract_chapter_ID(chapter_url)
                chapter_title = await scraper.fetch_chapter_title(soup)
                chapter_title = remove_invalid_characters(chapter_title)
                # logging.warning(chapter_id)
                # logging.warning(chapter_title)
                file_chapter_title,image_counter,chapter_content=await scraper.process_new_chapter_non_saved(chapter_url, book_title, chapter_id,image_counter)
                #logging.warning(chapter_content)
                #chapter_conte_soup appears to not be working?
                chapter_content_soup=bs4.BeautifulSoup(str(chapter_content),'html.parser')
                #write_to_logs(str(chapter_content_soup).encode("ascii", "ignore").decode("ascii"))
                #logging.error(chapter_content_soup)
                if (additionalConditions.get("exclude_images", False)):
                    # Remove images if exclude_images is True
                    for img in chapter_content_soup.find_all('img'):
                        img.decompose()
                else:
                    images=chapter_content_soup.find_all('img')
                    images=[image['src'] for image in images]
                    image_dir = f"./books/raw/temporary/"
                    
                    #TODO: Image counter error. After saving X images, we start at X instead of starting at 0.
                    if images:
                        current_image_counter=await self.retrieve_images_in_chapter(images, image_dir,current_image_counter,new_epub)
                
                logging.warning(chapter_title)
                logging.warning(file_chapter_title)
                
                #This function is not working for some odd reason.
                chapter = self.create_epub_chapter(chapter_title, file_chapter_title, chapter_content_soup, css)
                logging.error("This should be a chapter object below this line.")
                logging.error(chapter)
                toc_list.append(chapter)
                new_epub.add_item(chapter)
        except Exception as e:
            errorText=f"Failed to process chapter for custom epub. Function produce_custom_epub Error: {e}"
            write_to_logs(errorText)
        dirLocation=f"./books/raw/temporary/cover_image.png"
        cover_image=None
        if os.path.exists(dirLocation):
            try:
                cover_image= Image.open(dirLocation)
            except Exception as e:
                errorText=f"Failed to retrieve cover image. Function retrieve_cover_from_storage. Error: {e}"
                write_to_logs(errorText)
        if cover_image:
            b=io.BytesIO()
            try:
                cover_image.save(b,'png')
                b_image=b.getvalue()
                cover_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image)
                new_epub.add_item(cover_item)
            except Exception as e:
                errorText=f"Failed to add cover image to epub. Function add_cover_image Error: {e}"
                logging.warning(errorText)
                write_to_logs(errorText)

        new_epub.toc = toc_list
        new_epub.spine = toc_list
        new_epub.add_item(epub.EpubNcx())
        new_epub.add_item(epub.EpubNav())

        try:
            dirLocation="./books/epubs/temporary/"+book_title+".epub"
            if (check_directory_exists(dirLocation)):
                os.remove(dirLocation)
            epub.write_epub(dirLocation,new_epub)
        except Exception as e:
            errorText=f"Error with storing epub. Function store_epub. Error: {e}"
            write_to_logs(errorText)
        return dirLocation





class SpaceBattlesScraper():
    async def get_soup(self,url): 
        try:
            async with aiohttp.ClientSession(headers = basicHeaders) as session:
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

    async def fetch_cover_image(self, soup, bookTitle):
        try:
            if not isinstance(soup, bs4.BeautifulSoup):
                # Check if soup is a valid URL
                url_pattern = re.compile(r'^(https?://|www\.)', re.IGNORECASE)
                if isinstance(soup, str) and url_pattern.match(soup.strip()):
                    # If it's a valid URL, fetch the soup for that URL
                    soup = await self.get_soup(soup)
                else:
                    errorText = f"Provided object is neither a BeautifulSoup object nor a valid URL: {soup}"
                    write_to_logs(errorText)
                    return None
            
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
            errorText=f"Failed to get cover image. Function fetch_cover_image Error: {e}"
            write_to_logs(errorText)

    def normalize_spacebattles_url(self, url: str) -> str:
        """Find the last occurrence of digits/ and trim everything after"""
        match = re.search(r'(\d+/)', url)
        if match:
            idx = url.find(match.group(1)) + len(match.group(1))
            url = url[:idx]
        # Ensure it ends with threadmarks?per_page=200
        if not url.endswith('threadmarks?per_page=200'):
            url += 'threadmarks?per_page=200'
        return url
    
    def threadmarks_to_reader(self, url: str) -> str:
        """
        Replace 'threadmarks?per_page=200' at the end of a SpaceBattles thread URL with 'reader/'.
        """
        if url.endswith('threadmarks?per_page=200'):
            url = url[: -len('threadmarks?per_page=200')]
            if not url.endswith('/'):
                url += '/'
            url += 'reader/'
        return url
    
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
                logging.warning(rows)
                latestChapter=rows[len(rows)-1]
                latestChapterTitle=latestChapter.get_text()
                logging.warning(latestChapterTitle)
                
                
                match = re.search(
                    r'\b(\d+(?:-\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|'
                    r'eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|'
                    r'thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)\b',
                    latestChapterTitle,
                    re.IGNORECASE
                )
                latestChapterID = None
                if match:
                    value = match.group(1).lower()
                    try:
                        # Try to convert directly to int (for digit matches)
                        latestChapterID = int(value)
                    except ValueError:
                        try:
                            # If not a digit, convert written number to int
                            latestChapterID = w2n.word_to_num(value)
                        except Exception:
                            latestChapterID = value  # fallback: keep as string if conversion fails
                    
            
                try:
                    self.fetch_cover_image(soup, bookTitle)
                except Exception as e:
                    errorText=f"Failed to get cover image. There might be no cover. Or a different error. Function fetch_novel_data Error: {e}"
                    write_to_logs(errorText)
                #logging.warning(bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID)
                return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle,latestChapterID
            except Exception as e:
                errorText=f"Failed to get novel data. Function Spacebattles fetch_novel_data Error: {e}"
                write_to_logs(errorText)
    
    #This doesn't actually return chapters. It just returns the pages.
    #Page numbers are to generated under the assumption that each page can hold 10 threadmarks.
    async def fetch_chapter_list(self,url):
        url=self.normalize_spacebattles_url(url)
        
        url = self.threadmarks_to_reader(url)
        logging.warning(url)
        
        soup=await self.get_soup(url)
        last=0
        try:
            pagelist=soup.find("ul",{"class":"pageNav-main"})
            for anchor in pagelist.find_all("a"):
                pagenum=anchor.get_text()
                if pagenum.isdigit():
                    last = max(last,int(pagenum))
            logging.warning(f"Last page: {last}")
            return last
        except Exception as e:
            errorText=f"Failed to get total number of pages. Function Spacebattles fetch_chapter_list Error: {e}"
            write_to_logs(errorText)
    
    #While this returns the threadmark titles.
    async def fetch_chapter_title_list(self, url):
        url=self.normalize_spacebattles_url(url)
        
        soup=await self.get_soup(url)
        logging.warning(url)
        try:
            #logging.warning(soup)
            chapterListTitles=list()
            pageNav=soup.find("div",{"class":"pageNav"})
            logging.warning(pageNav)
            if not pageNav:
                threadmarkBody=soup.find("div",{"class":"structItemContainer"})
                #logging.warning(threadmarkBody)
                rows= threadmarkBody.find_all("ul",{"class":"listInline listInline--bullet"})
                for row in rows[:len(rows)]:
                    #logging.warning(row)
                    
                    threadmarkItem = row.find("a")
                    if threadmarkItem is not None:
                        #logging.warning(threadmarkItem)
                        chapterTitle = threadmarkItem.get_text()
                        chapterTitle = remove_invalid_characters(chapterTitle)
                        #logging.warning(f"Title:{chapterTitle}")
                        chapterListTitles.append(chapterTitle)
                    else:
                        logging.warning("No <a> tag found in row!")
            else:
                pageNavMain=pageNav.find("ul",{"class":"pageNav-main"})
                pages = pageNavMain.find_all("li")
                #logging.warning(pageNav)
                for page in range(1,len(pages)+1):
                    url=f"{url}&page={page}/"
                    logging.warning(page)
                    soup=await self.get_soup(url)
                    
                    threadmarkBody=soup.find("div",{"class":"structItemContainer"})

                    rows= threadmarkBody.find_all("ul",{"class":"listInline listInline--bullet"})
                    for row in rows[:len(rows)]:
                        #logging.warning(row)
                        
                        threadmarkItem = row.find("a")
                        if threadmarkItem is not None:
                            #logging.warning(threadmarkItem)
                            chapterTitle = threadmarkItem.get_text()
                            chapterTitle = remove_invalid_characters(chapterTitle)
                            #logging.warning(f"Title:{chapterTitle}")
                            chapterListTitles.append(chapterTitle)
                        else:
                            logging.warning("No <a> tag found in row!")
                
            return chapterListTitles
        except Exception as error:
            errorText=f"Failed to get chapter titles from chapter list of page. Function Spacebattles_get_chapter_title_list Error: {error}"
            write_to_logs(errorText)
    
    
    
    
    async def process_new_book(self, book_url,book_title):
        listofChapters = await self.fetch_chapter_list(book_url)
        if not listofChapters:
            errorText="Function: process_new_book. Error: No chapters found in the bookURL. Please check the URL or the book's availability."
            logging.warning(errorText)
            write_to_logs(errorText)
            return
        existingChapters = self.get_existing_order_of_contents(book_title)
        chapter_metadata=[]
        image_counter=0
        for pageNum in range(1, listofChapters+1):
            page_url = f"{book_url}page-{pageNum}/"
        
        
            #This needs to be modified. There is a very specific case where this will not work.
            #If on Spacebattles, the latest update creates the next page. Any updates on the previous page will not be saved as it will be skipped.
            #Basically, if chapter 4 gets the last threadmark and chapter 5 is created before we notice, chapter 4's latest update won't be saved because the below code will skip it.
            if not (pageNum == listofChapters):
                if (self.check_if_chapter_exists(str(pageNum), existingChapters)):
                    for line in existingChapters:
                        if line.startswith(f"{pageNum};"):
                            chapter_metadata.append(line.strip().split(";"))
                    continue
            
        
            await asyncio.sleep(1)
            soup= await self.get_soup(page_url)
            articles=soup.find_all("article",{"class":"message"})
            
            pageContent=""
            if (articles):
                for article in articles:
                    threadmarkTitle=article.find("span",{"class":"threadmarkLabel"})
                    title=threadmarkTitle.get_text()
                    title=remove_tags_from_title(title)
                    logging.warning(title)
                    
                    chapter_content=article.find("div",{"class":"message-userContent"})
                    chapter_content=await self.spacebattles_remove_garbage_from_chapter(chapter_content)
                    chapter_content = await self.remove_junk_links(chapter_content)
                    
                    
                    currentImageCount=image_counter
                    
                    
                    images=[]
                    seen = set()
                    for image in chapter_content.find_all('img'):
                        # Prefer a valid http(s) URL from data-src or src
                        img_url = None
                        for attr in ['data-src', 'src']:
                            candidate = image.get(attr)
                            if candidate and re.match(r'^https?://', candidate):
                                img_url = candidate
                                break# Get the image URL from 'src' or fallback to 'data-src'
                        # Add the URL to the list if it's valid and not already seen
                        if img_url and img_url not in seen:
                            images.append(img_url)
                            seen.add(img_url)
                    
                    image_dir = f"./books/raw/{book_title}/images/"
                    if images:
                        start_idx = image_counter  # Save the starting index
                        image_counter = await self.save_images_in_chapter(images, image_dir, image_counter)
                        # Replace all img srcs with local file path
                        for idx, img in enumerate(chapter_content.find_all('img')):
                            if idx < len(images):
                                img['src'] = f"images/image_{start_idx + idx}.png"
                    
                    stringChapterContent=str(chapter_content)
                    pageContent+=f"<div id='chapter-start'><title>{title}</title>{stringChapterContent}</div>"
                    
                    
            fileTitle=book_title+" - "+str(pageNum)
            pageContent=bs4.BeautifulSoup(pageContent,'html.parser')
            
            await self.save_page_content(pageContent,book_title,fileTitle)
            chapter_metadata.append([str(pageNum),page_url,f"./books/raw/{book_title}/{fileTitle}.html"])
        logging.warning(chapter_metadata)
        self.write_order_of_contents(book_title,chapter_metadata)
    
    async def remove_junk_links(self, chapter_content):    
        hyperlinks=chapter_content.find_all('a',{'class':'link'})
        for link in hyperlinks:
            if ("emoji" in link):
                link.extract() #Remove emoji links
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
                chapter_content=bs4.BeautifulSoup(str(chapter_content),'html.parser')
        return chapter_content
    
    
    async def save_images_in_chapter(self, img_urls, save_directory, image_count):
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
                        image_count += 1
                await asyncio.sleep(0.5)
            return image_count
        except Exception as e:
            errorText=f"Failed to get save image. Function save_images_in_chapter Error: {e}"
            write_to_logs(errorText)
    
    
    async def fetch_chapter_title(self,soup):
        try:
            threadmarkTitle=soup.find("span",{"class":"threadmarkLabel"})
            return threadmarkTitle.get_text()
        except Exception as e:
            errorText=f"Failed to get chapter title. Function Spacebattles fetch_chapter_title Error: {e}"
            write_to_logs(errorText)
    
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
    
    async def save_page_content(self,chapterContent,bookTitle,fileTitle):
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

    #These two function are from epubproducer. They may become a 'common' function
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

    def write_order_of_contents(self, book_title, chapter_metadata):
        file_location = f"./books/raw/{book_title}/order_of_chapters.txt"
        logging.warning(chapter_metadata)
        with open(file_location, "w") as f:
            for data in chapter_metadata:
                if isinstance(data, str):
                    data = data.strip().split(";")
                logging.warning(data)
                f.write(";".join(map(str, data))+ "\n")


    async def query_site(self,title:str,additionalConditions: dict, cookie):
        isSearchSearch = additionalConditions.get("true_search", False)
        sortby= additionalConditions.get("order", None)
        
        def normalize_title(title: str) -> str:
            """Convert spaces in a title to underscores."""
            title = title.lower()
            return title.replace(" ", "+")
        title = normalize_title(title)
        if (isSearchSearch): #This will decide what sort of search.
            #the first search is a search of the forums, the second is a filter of the forums
            return await self.query_spacebattles_search_version(title,sortby, additionalConditions)
        else:
            return await self.query_spacebattles_filter_version(title,sortby,additionalConditions)
    
    #https://forums.spacebattles.com/search/104090354/?q=New+Normal&t=post&c[child_nodes]=1&c[nodes][0]=18&c[title_only]=1&o=date 
    #Basic format of search query
    #https://forums.spacebattles.com/search/104090768/?q=Cheese
    #& between each condition
    #c[title_only]
    #c[users]="Name"
    #o=date, or, o=word_count, or, o=relevance
    #This is for order
    
    #This function only takes certain parameters.
    #c[title_only]=1 or 0.
    #c[users]="Name"
    #o=date/word_count/relevance
    async def query_spacebattles_search_version(self,title: str, sortby: str, additionalConditions: dict):
        try:
            if (title.isspace() or title==""):
                errorText=f"Failed to search title. Function query_spacebattles_search_version Error: No title inputted"
                write_to_logs(errorText)
                return "Invalid Title"
            #&t=post&c[child_nodes]=1&c[nodes][0]=18 is for forum: Creative Writing
            #&c[title_only]=1 is for title only search
            querylink = f"https://forums.spacebattles.com/search/104090354/?q={title}&t=post&c[child_nodes]=1&c[nodes][0]=18"
            for item in additionalConditions:
                querylink+=f"&{item}={additionalConditions[item]}"
                logging.warning(querylink)
            if (sortby not in ["relevance","date",  "last_update", "replies", "word_count"]):
                errorText=f"Invalid sort-by condition. Continuing on with default. Function query_spacebattles_search_version Error: {sortby}"
                write_to_logs(errorText)
                sortby = "date"  # Default sort-by option
            querylink+=f"&o={sortby}"
            logging.warning(querylink)
            
            async def get_soup(url):
                try:
                    driver = webdriver.Firefox(options=firefox_options)
                    driver.install_addon(path_to_extension, temporary=True)
                    driver.request_interceptor=interception
                    driver.get(url)
                    WebDriverWait(driver, 10).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    await asyncio.sleep(2) #Sleep is necessary because of the javascript loading elements on page
                    soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
                    driver.close()
                    return soup
                except Exception as error:
                    errorText=f"Failed to get soup from url. Function spacebattles_get_soup Error: {error}"
                    write_to_logs(errorText)
            
            #Needs to be selenium because the 'search url' result is dynamically generated...
            #Basically... Spacebattles generates the result and then sends its as a webpage. Instead of a static page hosting the results.
            #https://forums.spacebattles.com/search/104096825/?q=Trails+Of&t=post&c[child_nodes]=1&c[nodes][0]=18&c[title_only]=1&o=date
            #But everything after those numbers is just for you to see. The numbers are the actual search results.
            #for some god forsaken reason, spacebattles indexes the search results. 
            #If you want to search, you have to use their form and button. Which I can't do since I am using url-based search
            soup=await get_soup(querylink)
            try:
                resultTable=soup.find("div",{"class":"block-container"})
                bookTable=resultTable.find("ol",{"class":"block-body"})
                bookRows=bookTable.find_all("h3", {"class":"contentRow-title"})
                bookLinks=bookRows[0].find("a")['href']
                firstResult=bookLinks
                #formatting
                resultLink = f"https://forums.spacebattles.com{firstResult}"
                resultLink = re.sub(r'(#|\?).*$', '', resultLink)
                return resultLink
            except Exception as error:
                errorText=f"Search failed. Most likely reason: There wasn't any search results. Function query_royalroad Error: {error}"
                write_to_logs(errorText)
        except Exception as e:
            errorText=f"Improper query attempt. Function query_spacebattles Error: Invalid query option. {e}"
            write_to_logs(errorText)
            return ("Invalid Option")
    
    #this one uses a different search system. It's not really a search but rather a filter.
    #Search via main tag, and get the results. It's more dependent on the additional filter conditions to do the search.
    #The additional filter conditions are:
    #sortby: title, reply_count, view_count, last_threadmark, watchers
    #direction: asc, desc
    #&threadmark_index_statuses[0]=incomplete
    #&threadmark_index_statuses[1]=complete
    #&threadmark_index_statuses[2]=hiatus
    #min_word_count=0
    #max_word_count=10000000
    async def query_spacebattles_filter_version(self,title: str, sortby: str, additionalConditions: dict):
        try:
            if (title.isspace() or title==""):
                errorText=f"Failed to search title. Function query_spacebattles Error: No title inputted"
                write_to_logs(errorText)
                return "Invalid Title"
            
            direction = additionalConditions.get("direction", "desc")
            if direction not in ["asc", "desc"]:
                errorText=f"Invalid direction condition. Continuing on with default. Function query_spacebattles_filter_version Error: {direction}"
                write_to_logs(errorText)
                direction = "desc"
            
            querylink = f"https://forums.spacebattles.com/forums/creative-writing.18/?tags[0]={title}"
            if (sortby not in ["title", "reply_count", "view_count", "last_threadmark", "watchers"] and direction not in ["asc", "desc"]):
                errorText=f"Invalid sort-by condition. Continuing on with default. Function query_spacebattles_filter_version Error: {sortby}"
                write_to_logs(errorText)
                sortby = "last_threadmark"  # Default sort-by option
                querylink+=f"&order={sortby}&direction=desc"
            else:
                querylink+=f"&order={sortby}&direction={direction}"
            for item in additionalConditions:
                querylink+=f"&{item}={additionalConditions[item]}"
                logging.warning(querylink)
            logging.warning(querylink)
            querylink+="&nodes[0]=48&nodes[1]=169&nodes[2]=40&nodes[3]=115"
            
            
            
            soup=await self.get_soup(querylink)
            try:
                resultTable=soup.find("div",{"class":"structItemContainer"})
                bookTable=resultTable.find("div",{"class":"js-threadList"})
                bookRows=bookTable.find_all("div", {"class":"structItem"})
                #logging.warning(bookRows)
                firstResult=bookRows[0].find("div", {"class":"structItem-title"})
                logging.warning("=================")
                logging.warning(firstResult.get_text())
                
                if (firstResult):
                    links=firstResult.find_all("a")
                    if (links):
                        logging.warning(links)
                        for link in links:
                            if link.get_text(strip=True) == "Jump to New":
                                continue
                            # If we find a link that is not "Jump to New", we take it
                            firstResultLink=link['href']
                            break
                        #formatting
                        resultLink=f"https://forums.spacebattles.com/{firstResultLink}"
                        return resultLink
                return "No Results Found"
            except Exception as e:
                errorText=f"Search failed. Most likely reason: There wasn't any search results. Function query_spacebattles_filter_version Error: {e}"
                write_to_logs(errorText)
                return "No Results Found"
        except Exception as e:
            errorText=f"Improper query attempt. Function query_spacebattles_filter_version Error: {e} How did you even do this?"
            write_to_logs(errorText)
            return "Invalid Option"
        #These need to be added at the end to specify the forums.
        #THEY MUST BE at the end of the query.

    
    #TODO: Working on creating a new function to generate an epub with the selected chapters without actually storing them into the repository.
    async def process_new_chapter_non_saved(self, soup, book_title,chapter_id,image_count, exclude_images):
        try:
            soup = soup
            chapter_title = await self.fetch_chapter_title(soup)
            chapter_content= soup.find("div", {"class": "message-userContent"})
            if not chapter_content:
                errorText=f"Failed to find chapter content. Function process_new_chapter_non_saved Error: No content found for page {chapter_id} in book {book_title}."
                write_to_logs(errorText)
                return None, image_count, None
            chapter_content = await self.spacebattles_remove_garbage_from_chapter(chapter_content)
            chapter_content = await self.remove_junk_links(chapter_content)
            if not chapter_content:
                errorText=f"Failed to clean chapter content. Function process_new_chapter_non_saved Error: No valid content found for page {chapter_id} in book {book_title}."
                write_to_logs(errorText)
                return None, image_count, None
            
            currentImageCount=image_count
            # Process images
            if exclude_images:
                for img in chapter_content.find_all('img'):
                    img.decompose()
            else:
                images=[]
                seen = set()
                for image in chapter_content.find_all('img'):
                    # Prefer a valid http(s) URL from data-src or src
                    img_url = None
                    for attr in ['data-src', 'src']:
                        candidate = image.get(attr)
                        if candidate and re.match(r'^https?://', candidate):
                            img_url = candidate
                            break
                        if img_url and img_url not in seen:
                            images.append(img_url)
                            seen.add(img_url)
                image_dir = f"./books/raw/temporary/images/"
                #Do not save these images permanent. Always overwrite.
                if images:
                    start_idx = image_counter  # Save the starting index
                    image_counter = await self.save_images_in_chapter(images, image_dir, image_counter)
                    # Replace all img srcs with local file path
                    for idx, img in enumerate(chapter_content.find_all('img')):
                        if idx < len(images):
                            img['src'] = f"images/image_{start_idx + idx}.png"
            
            file_chapter_title = f"{book_title} - {chapter_id} - {remove_invalid_characters(chapter_title)}"
            
            return file_chapter_title, currentImageCount, chapter_content
        except Exception as e:
            errorText=f"Failed to process new chapter. Function spacebattles_process_new_chapter_non_saved Error: {e}"
            write_to_logs(errorText)





class SpaceBattlesEpubProducer():
    #These two function are from epubproducer. They may become a 'common' function
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

    #TODO: DONE This needs modifying
    async def retrieve_images_in_chapter(self,images_url,image_dir,image_count,new_epub):
        current_image_count=image_count
        try:
            for img_url in images_url:
                image_path=f"{image_dir}/{img_url}"
                epubImage=Image.open(image_path)
                if (epubImage):
                    try:
                        b=io.BytesIO()
                        epubImage.save(b,'png')
                        b_image1=b.getvalue()
                        
                        image_item=epub.EpubItem(uid=f'image_{current_image_count}',file_name=f'images/image_{current_image_count}.png', media_type='image/png', content=b_image1)
                        new_epub.add_item(image_item)
                    except Exception as error:
                        errorText=f"Failed to add image to epub. Function retrieve_images_in_chapter. Error: {error}. Possibly image is corrupted or not saved at all."
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

    #this might become a common function
    #Nevermind. This one is different. It's not extracting the ID from the URL but frm the internal storage.
    def extract_chapter_ID(self, chapter_url):
        return chapter_url.split(";")[0]

    def extract_chapter_title(self, dir_location):
        return os.path.basename(dir_location).split(" - ")[-1].replace(".html", "")

    def create_epub_chapter(self, chapter_title,file_chapter_title,chapter_content, css):
        try:
            #chapter_content=chapter_content.encode('ascii')
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
            b=io.BytesIO()
            try:
                img.save(b,'png')
                b_image=b.getvalue()
                cover_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image)
                new_epub.add_item(cover_item)
            except Exception as e:
                errorText=f"Failed to add cover image to epub. Function add_cover_image Error: {e}"
                logging.warning(errorText)
                write_to_logs(errorText)

    def finalize_epub(self, new_epub, toc_list, book_title):
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
                if isinstance(data, str):
                    data = data.strip().split(";")
                logging.warning(data)
                f.write(";".join(map(str, data))+ "\n")
                
                
    #Overrides existing produce_epub
    async def produce_epub(self,book_title,css,new_epub):
        logging.warning('Starting produce_epub in overwritten method')
        already_saved_chapters = self.get_existing_order_of_contents(book_title)
        toc_list = []
        image_count = 0
        logging.warning("Producing epub for book, grabbing chapters")
        logging.warning(f"Already saved chapters: {already_saved_chapters}")
        if not already_saved_chapters:
            errorText="Function produce_epub. Error: No chapters found in the bookURL. Please check the URL or the book's availability."
            logging.warning(errorText)
            write_to_logs(errorText)
            return
        logging.warning(f"Already saved chapters: {already_saved_chapters}")
        for chapter_url in already_saved_chapters:
        # for pageNum in range(len(already_saved_chapters+1)):
        #     page_url = f"{novelURL}page-{pageNum}/"
            pageNum=chapter_url.split(";")[0]
            logging.warning (chapter_url)
            #Retrieval does not work at the moment
            chapter_id, dir_location = self.get_chapter_from_saved(pageNum, already_saved_chapters)
            logging.warning(f"Processing chapter. {dir_location}")
            page_content = self.get_chapter_contents_from_saved(dir_location)
            page_soup=bs4.BeautifulSoup(page_content,'html.parser')
            #logging.warning(page_soup)
            all_chapters=page_soup.find_all('div',{'id':'chapter-start'})
            for chapter_soup in all_chapters:
                chapter_title=chapter_soup.find('title')
                chapter_title=chapter_title.get_text()
                
                images=chapter_soup.find_all('img')
                images=[image['src'] for image in images]
                image_dir = f"./books/raw/{book_title}/"
                if images:
                    image_count=await self.retrieve_images_in_chapter(images, image_dir,image_count,new_epub)
                
                file_chapter_title=f"{book_title} - {pageNum} - {chapter_title}"
                chapter_content=chapter_soup.encode('ascii')
                chapter = self.create_epub_chapter(chapter_title, file_chapter_title, chapter_content, css)
                
                toc_list.append(chapter)
                new_epub.add_item(chapter)
            # else:
            #     chapter_title=f"Chapter is MISSING"
            #     file_chapter_title=f"{book_title} - {pageNum} - {chapter_title}"
            #     chapter_content="<p>MISSING CONTENT</p>"
            #     chapter = self.create_epub_chapter(chapter_title, file_chapter_title, chapter_content, css)
        
        logging.warning("Adding cover image")
        try:
            self.add_cover_image(book_title, new_epub)
        except Exception as e:
            errorText=f"Failed to add cover image. Function add_cover_image Error: {e}"
            write_to_logs(errorText)
        logging.warning("Finalizing epub")
        self.finalize_epub(new_epub, toc_list, book_title)
        # logging.warning("Attempting to store epub")
        storeEpub(book_title, new_epub)
        
    

    #TODO: Modify to work with specific Threadmarks
    #TODO: Test if it works
    async def produce_custom_epub(self, new_epub, book_title, css, book_chapter_titles, mainBookURL, additionalConditions):
        if not book_chapter_titles:
            errorText="Function: spacebattles_produce_custom_epub. Error: No chapters found in the requested book. Please check the URL or the book's availability."
            logging.warning(errorText)
            write_to_logs(errorText)
            return
        sbScraper=SpaceBattlesScraper()
        
        existingPages=await sbScraper.fetch_chapter_list(mainBookURL)
        if not existingPages:
            errorText="Function: spacebattles_produce_custom_epub. Error: No chapters found in the requested book. Please check the URL or the book's availability."
            logging.warning(errorText)
            write_to_logs(errorText)
            return

        try:
            await sbScraper.fetch_cover_image(mainBookURL, book_title)
        except Exception as e:
            errorText=f"Failed to fetch cover image. Function fetch_cover_image Error: {e}"
            write_to_logs(errorText)
        
        url = sbScraper.normalize_spacebattles_url(mainBookURL)
        url = sbScraper.threadmarks_to_reader(url)
              
        toc_list = []
        image_counter=0
        exclude_images= additionalConditions.get("exclude_images", False)
        try:
            for pageNum in range (1, existingPages+1):
                page_url = f"{url}page-{pageNum}/"
                logging.warning(f"Processing page: {page_url}")
                await asyncio.sleep(1)
                soup = await sbScraper.get_soup(page_url)
                #logging.warning(soup)
                
                found_titles = []
                for span in soup.find_all("span", {"class": "threadmarkLabel"}):
                    title = span.get_text(strip=True)
                    found_titles.append(title)

                # Check which found_titles are in book_chapter_titles
                matched_titles = [title for title in found_titles if title in book_chapter_titles]
                if not matched_titles:
                    # No requested chapters on this page, move to next page
                    continue

                threadmarkArticles = soup.find_all("article", {"class": "message"})
                if not threadmarkArticles:
                    errorText = f"Failed to retrieve threadmark body. Function produce_custom_epub Error: No threadmark body found for page {pageNum}."
                    write_to_logs(errorText)
                    continue
                #logging.warning(threadmarkBody)
                
                for threadmarkArticle in threadmarkArticles:
                    threadmarkTitle=threadmarkArticle.find("span",{"class":"threadmarkLabel"})
                    if not threadmarkTitle:
                        errorText=f"Failed to retrieve threadmark title. Function produce_custom_epub Error: No threadmark title found for page {pageNum}."
                        write_to_logs(errorText)
                        continue
                    chapter_title = remove_tags_from_title(threadmarkTitle.get_text())
                    logging.warning(f"Processing chapter: {chapter_title}")
                    
                    if chapter_title in matched_titles:
                        file_chapter_title, image_counter, chapter_content = await sbScraper.process_new_chapter_non_saved(
                            threadmarkArticle, book_title, pageNum, image_counter, exclude_images
                        )
                        if not file_chapter_title:
                            errorText = f"Failed to process threadmark article. Function produce_custom_epub Error: No valid chapter title found for page {pageNum}."
                            write_to_logs(errorText)
                            continue

                        stringChapterContent=str(chapter_content)
                        pageContent=f"<div id='chapter-start'><title>{chapter_title}</title>{stringChapterContent}</div>"
                        #fileTitle=book_title+" - "+str(pageNum)
                        pageContent=bs4.BeautifulSoup(str(pageContent),'html.parser')
                        logging.warning(pageContent)
                        logging.warning(file_chapter_title)
                        
                        chapter_content=pageContent.encode('ascii')
                        #It needs to be encoded. No idea why again.
                        chapter=self.create_epub_chapter(chapter_title, file_chapter_title, chapter_content, css)                            
                        toc_list.append(chapter)
                        new_epub.add_item(chapter)
                        
                        # Remove the found title from book_chapter_titles
                        book_chapter_titles.remove(chapter_title)
                        
                        # If no more titles to scrape, break out of the page loop
                        if not book_chapter_titles:
                            logging.warning("All requested chapter titles have been scraped. Ending loop early.")
                            break
                if not book_chapter_titles:
                    logging.warning("All requested chapter titles have been scraped. Ending loop early.")
                    break                
        except Exception as e:
            errorText=f"Failed to process chapter for custom epub. Function spacebattles produce_custom_epub Error: {e}"
            write_to_logs(errorText)
            
        
        dirLocation=f"./books/raw/temporary/cover_image.png"
        cover_image=None
        if os.path.exists(dirLocation):
            try:
                cover_image= Image.open(dirLocation)
            except Exception as e:
                errorText=f"Failed to retrieve cover image. Function retrieve_cover_from_storage. Error: {e}"
                write_to_logs(errorText)
        if cover_image:
            b=io.BytesIO()
            try:
                cover_image.save(b,'png')
                b_image=b.getvalue()
                cover_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image)
                new_epub.add_item(cover_item)
            except Exception as e:
                errorText=f"Failed to add cover image to epub. Function add_cover_image Error: {e}"
                logging.warning(errorText)
                write_to_logs(errorText)

        new_epub.toc = toc_list
        new_epub.spine = toc_list
        new_epub.add_item(epub.EpubNcx())
        new_epub.add_item(epub.EpubNav())
        dirLocation="./books/epubs/temporary/"+book_title+".epub"
        try:
            
            if (check_directory_exists(dirLocation)):
                os.remove(dirLocation)
            epub.write_epub(dirLocation,new_epub)
        except Exception as e:
            errorText=f"Error with storing epub. Function store_epub. Error: {e}"
            write_to_logs(errorText)
        return dirLocation




class FoxaholicScraper():
    #These four functions appear to be a common function.
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
    
    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count):
        soup = await self.get_soup(chapter_url)
        chapter_title = await self.fetch_chapter_title(soup)
        chapter_content = await self.fetch_chapter_content(soup)
        
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

    async def save_images_in_chapter(self, img_urls, save_directory, image_count):
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
                        image_count += 1
                await asyncio.sleep(0.5)
            return image_count
        except Exception as e:
            errorText=f"Failed to get save image. Function save_images_in_chapter Error: {e}"
            write_to_logs(errorText)
            
            
    
    def write_order_of_contents(self, book_title, chapter_metadata):
        file_location = f"./books/raw/{book_title}/order_of_chapters.txt"
        logging.warning(chapter_metadata)
        with open(file_location, "w") as f:
            for data in chapter_metadata:
                
                if isinstance(data, str):
                    data = data.strip().split(";")
                logging.warning(data)
                f.write(";".join(map(str, data))+ "\n")
    #These four functions appear to be a common function.
    
    async def get_soup(self,url):
        try:
            driver = webdriver.Firefox(options=firefox_options)
            driver.install_addon(path_to_extension, temporary=True)
            driver.request_interceptor=interception
            driver.get(url)
            soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
            driver.close()
            return soup
        except Exception as error:
            errorText=f"Failed to get soup Function foxaholic_get_soup Error: {error}"
            write_to_logs(errorText)
        return None
    
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
                        await self.foxaholic_save_cover_image("cover_image",img_url,saveDirectory)
            except Exception as e:
                errorText=f"Failed to get cover image. There might be no cover. Or a different error. Function foxaholic_fetch_novel_data Error: {e}"
                write_to_logs(errorText)
                
                            
            return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle,latestChapterID
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
        
                    
            
            
            
            
            
            
            
            

class FoxaholicEpubProducer():
    #This grabs the first digit in the URL to treat as the ChapterID
    def extract_chapter_ID(self, chapter_url):
        chapterID=chapter_url.split("/")
        chapterID=chapterID[len(chapterID)-2]
        chapterID=re.search(r'\d+',chapterID).group()
        return chapterID
    
    #These two function are from epubproducer. They may become a 'common' function
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
    
    #TODO: DONE This needs modifying
    async def retrieve_images_in_chapter(self,images_url,image_dir,image_count,new_epub):
        current_image_count=image_count
        try:
            for img_url in images_url:
                image_path=f"{image_dir}/{img_url}"
                epubImage=Image.open(image_path)
                if (epubImage):
                    try:
                        b=io.BytesIO()
                        epubImage.save(b,'png')
                        b_image1=b.getvalue()
                        
                        image_item=epub.EpubItem(uid=f'image_{current_image_count}',file_name=f'images/image_{current_image_count}.png', media_type='image/png', content=b_image1)
                        new_epub.add_item(image_item)
                    except Exception as error:
                        errorText=f"Failed to add image to epub. Function retrieve_images_in_chapter. Error: {error}. Possibly image is corrupted or not saved at all."
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

    def extract_chapter_title(self, dir_location):
        return os.path.basename(dir_location).split(" - ")[-1].replace(".html", "")

    def create_epub_chapter(self, chapter_title,file_chapter_title,chapter_content, css):
        try:
            #chapter_content=chapter_content.encode('ascii')
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
            b=io.BytesIO()
            try:
                img.save(b,'png')
                b_image=b.getvalue()
                cover_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image)
                new_epub.add_item(cover_item)
            except Exception as e:
                errorText=f"Failed to add cover image to epub. Function add_cover_image Error: {e}"
                logging.warning(errorText)
                write_to_logs(errorText)

    def finalize_epub(self, new_epub, toc_list, book_title):
        #logging.warning(toc_list)
        new_epub.toc = toc_list
        new_epub.spine = toc_list
        new_epub.add_item(epub.EpubNcx())
        new_epub.add_item(epub.EpubNav())
        storeEpub(book_title, new_epub)

                
    
    async def produce_epub(self,book_title,css,new_epub):
        already_saved_chapters = self.get_existing_order_of_contents(book_title)
        toc_list = []
        image_count = 0
        logging.warning("Producing epub for book, grabbing chapters")
        for chapter in already_saved_chapters:
            chapter_url=chapter.split(";")[1]
            logging.warning(f"Processing chapter: {chapter_url}")
            
            
            
            chapter_id = self.extract_chapter_ID(chapter_url)
            chapter_id, dir_location = self.get_chapter_from_saved(chapter_id, already_saved_chapters)
            chapter_content = self.get_chapter_contents_from_saved(dir_location)
            chapter_title = self.extract_chapter_title(dir_location)
            logging.warning(chapter_title)
            chapter_content_soup=bs4.BeautifulSoup(chapter_content,'html.parser')
            
            images=chapter_content_soup.find_all('img')
            images=[image['src'] for image in images]
            image_dir = f"./books/raw/{book_title}/"
            if images:
                image_count=await self.retrieve_images_in_chapter(images, image_dir,image_count,new_epub)
            
            file_chapter_title = f"{book_title} - {chapter_id} - {remove_invalid_characters(chapter_title)}"
            chapter = self.create_epub_chapter(chapter_title, file_chapter_title, chapter_content, css)
            toc_list.append(chapter)
            new_epub.add_item(chapter)

        logging.warning("Adding cover image")
        try:
            self.add_cover_image(book_title, new_epub)
        except Exception as e:
            errorText=f"Failed to add cover image. Function add_cover_image Error: {e}"
            write_to_logs(errorText)
        
        logging.warning("Finalizing epub")
        self.finalize_epub(new_epub, toc_list, book_title)

    async def produce_custom_epub(self, new_epub, book_title, css, book_chapter_urls, mainBookURL, additionalConditions):
        if not book_chapter_urls:
            errorText="Function produce_custom_epub. Error: No chapters provided for the custom epub."
            logging.warning(errorText)
            write_to_logs(errorText)
            return
        
        fxScraper= FoxaholicScraper()
        toc_list=[]
        image_counter=0
        current_image_counter=0

        try:
            for chapter_url in book_chapter_urls:
                logging.error (chapter_url)
                soup=await fxScraper.get_soup(chapter_url)
                
                chapter_id= await fxScraper.extract_chapter_ID(chapter_url)
                chapter_title=await fxScraper.fetch_chapter_title(soup)
                chapter_title = remove_invalid_characters(chapter_title)

                file_chapter_title, image_counter, chapter_content = await fxScraper.process_new_chapter_non_saved(chapter_url, book_title, chapter_id, image_counter)
                chapter_content_soup=bs4.BeautifulSoup(str(chapter_content),'html.parser')
                
                if (additionalConditions.get("exclude_images", False)):
                    for img in chapter_content_soup.find_all('img'):
                        img.decompose()
                else:
                    images=chapter_content_soup.find_all('img')
                    images=[image['src'] for image in images]
                    image_dir = f"./books/raw/temporary/"
                    if images:
                        current_image_counter=await self.retrieve_images_in_chapter(images, image_dir, current_image_counter, new_epub)
                chapter=self.create_epub_chapter(chapter_title, file_chapter_title, chapter_content_soup, css)
                toc_list.append(chapter)
                new_epub.add_item(chapter)
        except Exception as e:
            errorText=f"Failed to produce custom epub. Function produce_custom_epub Error: {e}"
            write_to_logs(errorText)
            return
        
        
        dirLocation=f"./books/raw/temporary/cover_image.png"
        cover_image=None
        if os.path.exists(dirLocation):
            try:
                cover_image= Image.open(dirLocation)
            except Exception as e:
                errorText=f"Failed to retrieve cover image. Function retrieve_cover_from_storage. Error: {e}"
                write_to_logs(errorText)
        if cover_image:
            b=io.BytesIO()
            try:
                cover_image.save(b,'png')
                b_image=b.getvalue()
                cover_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image)
                new_epub.add_item(cover_item)
            except Exception as e:
                errorText=f"Failed to add cover image to epub. Function add_cover_image Error: {e}"
                logging.warning(errorText)
                write_to_logs(errorText)

        self.finalize_epub(new_epub, toc_list, book_title)

        try:
            dirLocation="./books/epubs/temporary/"+book_title+".epub"
            if (check_directory_exists(dirLocation)):
                os.remove(dirLocation)
            epub.write_epub(dirLocation,new_epub)
        except Exception as e:
            errorText=f"Error with storing epub. Function store_epub. Error: {e}"
            write_to_logs(errorText)
        return dirLocation
                
    




















class NovelBinScraper():
    #These four functions appear to be a common function.
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
    
    #THIS FUNCTION IS UNIQUE TO NOVELBIN
    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count):
        soup = await self.get_soup(chapter_url)
        chapter_title = await self.fetch_chapter_title(soup)
        chapter_title=await self.generate_chapter_title(chapter_id)+" "+chapter_title
        chapter_content = await self.fetch_chapter_content(soup)
        
        currentImageCount=image_count
        chapterInsert=f'<h1>{chapter_title}</h1>'
        chapter_content=chapterInsert+str(chapter_content)
        chapter_content=bs4.BeautifulSoup(chapter_content,'html.parser')
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

    async def save_images_in_chapter(self, img_urls, save_directory, image_count):
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
                        image_count += 1
                await asyncio.sleep(0.5)
            return image_count
        except Exception as e:
            errorText=f"Failed to get save image. Function save_images_in_chapter Error: {e}"
            write_to_logs(errorText)
            
            
    
    def write_order_of_contents(self, book_title, chapter_metadata):
        file_location = f"./books/raw/{book_title}/order_of_chapters.txt"
        logging.warning(chapter_metadata)
        with open(file_location, "w") as f:
            for data in chapter_metadata:
                
                if isinstance(data, str):
                    data = data.strip().split(";")
                logging.warning(data)
                f.write(";".join(map(str, data))+ "\n")
    #These four functions appear to be a common function.
    
    
    
    async def get_soup(self,url):
        try:
            #driver = webdriver.Firefox()
                        
            driver = webdriver.Firefox(options=firefox_options)
            driver.install_addon(path_to_extension, temporary=True)
            driver.request_interceptor=interception
            driver.get(url)
            await asyncio.sleep(2) #Sleep is necessary because of the javascript loading elements on page
            soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
            driver.close()
            return soup
        except Exception as error:
            errorText=f"Failed to get soup from url. Function novelbin_get_soup Error: {error}"
            write_to_logs(errorText)

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
            latestChapterID=self.extract_chapter_ID(latestChapter.find("a")["href"])
            
            
        except Exception as error:
            errorText=f"Failed to get novel data. Function novelbin-fetch_novel_data Error: {error}"
            write_to_logs(errorText)
        
        try:
            img_url = soup.find("img",{"class":"lazy"})
            if (img_url):
                saveDirectory=f"./books/raw/{bookTitle}/"
                if not (check_directory_exists(f"./books/raw/{bookTitle}/cover_image.png")):
                    await self.novelbin_save_cover_image("cover_image",img_url,saveDirectory)
        except Exception as error:
            errorText=f"Failed to find image, or save it. There might be no cover. Or a different error. Function novelbin_fetch_novel_data Error: {error}"
            write_to_logs(errorText)
            
        return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle,latestChapterID


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
                processChapterURL=row.find("a")["href"]
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
            chapter_content = await self.fetch_chapter_content(soup)
            chapter_content = await self.remove_junk_links_from_soup(chapter_content)
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
        
        
        
        
        
        
        
        
        
        
        

class NovelBinEpubProducer():
    #These two function are from epubproducer. They may become a 'common' function
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
    
    
    #TODO: DONE This needs modifying
    async def retrieve_images_in_chapter(self,images_url,image_dir,image_count,new_epub):
        current_image_count=image_count
        try:
            for img_url in images_url:
                image_path=f"{image_dir}/{img_url}"
                epubImage=Image.open(image_path)
                if (epubImage):
                    try:
                        b=io.BytesIO()
                        epubImage.save(b,'png')
                        b_image1=b.getvalue()
                        
                        image_item=epub.EpubItem(uid=f'image_{current_image_count}',file_name=f'images/image_{current_image_count}.png', media_type='image/png', content=b_image1)
                        new_epub.add_item(image_item)
                    except Exception as error:
                        errorText=f"Failed to add image to epub. Function retrieve_images_in_chapter. Error: {error}. Possibly image is corrupted or not saved at all."
                current_image_count+=1
            return current_image_count
        except Exception as error:
            errorText=f"Failed to retrieve images for chapter to add to epub object. Function retrieve_images_in_chapter Error: {error}"
            write_to_logs(errorText)
    
    def get_chapter_from_saved(self, chapter_id, saved_chapters):
        for chapter in saved_chapters:
            chapter = chapter.split(";")
            if str(chapter_id) == str(chapter[0]):
                return chapter[0], chapter[2].strip()
        return None, None

    def get_chapter_contents_from_saved(self, dir_location):
        with open(dir_location, "r") as f:
            return f.read()

    #this might become a common function
    #Nevermind. This one is different. It's not extracting the ID from the URL but frm the internal storage.
    def extract_chapter_ID(self, chapter_url):
        return chapter_url.split(";")[0]

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
            b=io.BytesIO()
            try:
                img.save(b,'png')
                b_image=b.getvalue()
                cover_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image)
                new_epub.add_item(cover_item)
            except Exception as e:
                errorText=f"Failed to add cover image to epub. Function add_cover_image Error: {e}"
                logging.warning(errorText)
                write_to_logs(errorText)

    def finalize_epub(self, new_epub, toc_list, book_title):
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
                
                if isinstance(data, str):
                    data = data.strip().split(";")
                logging.warning(data)
                f.write(";".join(map(str, data))+ "\n")

    async def produce_epub(self, book_title, css, new_epub):
        already_saved_chapters = self.get_existing_order_of_contents(book_title)
        toc_list = []
        image_count = 0
        logging.warning("Producing epub for book, grabbing chapters")
        for chapter_url in already_saved_chapters:
            chapter_id = self.extract_chapter_ID(chapter_url)
            chapter_id, dir_location = self.get_chapter_from_saved(chapter_id, already_saved_chapters)
            chapter_content = self.get_chapter_contents_from_saved(dir_location)
            chapter_title = self.extract_chapter_title(dir_location)
            logging.warning(chapter_title)
            chapter_content_soup=bs4.BeautifulSoup(chapter_content,'html.parser')
            
            #TODO: THIS NEEDS MODIFYING
            images=chapter_content_soup.find_all('img')
            images=[image['src'] for image in images]
            image_dir = f"./books/raw/{book_title}/"
            if images:
                image_count=await self.retrieve_images_in_chapter(images, image_dir,image_count,new_epub)
            
            file_chapter_title = f"{book_title} - {chapter_id} - {remove_invalid_characters(chapter_title)}"
            chapter = self.create_epub_chapter(chapter_title, file_chapter_title, chapter_content, css)
            toc_list.append(chapter)
            new_epub.add_item(chapter)

        logging.warning("Adding cover image")
        try:
            self.add_cover_image(book_title, new_epub)
        except Exception as e:
            errorText=f"Failed to add cover image. Function add_cover_image Error: {e}"
            write_to_logs(errorText)
        
        logging.warning("Finalizing epub")
        self.finalize_epub(new_epub, toc_list, book_title)


    async def produce_custom_epub(self, new_epub, book_title, css, book_chapter_urls, mainBookURL, additionalConditions):
        if not book_chapter_urls:
            errorText="Function produce_custom_epub. Error: No chapters provided for the custom epub."
            logging.warning(errorText)
            write_to_logs(errorText)
            return
        
        nbScraper= NovelBinScraper()
        toc_list=[]
        image_counter=0
        current_image_counter=0

        try:
            for chapter_url in book_chapter_urls:
                logging.error (chapter_url)
                soup=await nbScraper.get_soup(chapter_url)
                
                chapter_id= await nbScraper.extract_chapter_ID(chapter_url)
                chapter_title=await nbScraper.fetch_chapter_title(soup)
                chapter_title = remove_invalid_characters(chapter_title)
                
                file_chapter_title, image_counter, chapter_content = await nbScraper.process_new_chapter_non_saved(chapter_url, book_title, chapter_id, image_counter)  
                chapter_content_soup=bs4.BeautifulSoup(str(chapter_content),'html.parser')
                
                if (additionalConditions.get("exclude_images", False)):
                    for img in chapter_content_soup.find_all('img'):
                        img.decompose()
                else:
                    images=chapter_content_soup.find_all('img')
                    images=[image['src'] for image in images]
                    image_dir = f"./books/raw/temporary/"
                    if images:
                        current_image_counter=await self.retrieve_images_in_chapter(images, image_dir, current_image_counter, new_epub)
                chapter=self.create_epub_chapter(chapter_title, file_chapter_title, chapter_content_soup, css)
                toc_list.append(chapter)
                new_epub.add_item(chapter)
        except Exception as e:
            errorText=f"Failed to produce custom epub. Function produce_custom_epub Error: {e}"
            write_to_logs(errorText)
            return
        
        
        dirLocation=f"./books/raw/temporary/cover_image.png"
        cover_image=None
        if os.path.exists(dirLocation):
            try:
                cover_image= Image.open(dirLocation)
            except Exception as e:
                errorText=f"Failed to retrieve cover image. Function retrieve_cover_from_storage. Error: {e}"
                write_to_logs(errorText)
        if cover_image:
            b=io.BytesIO()
            try:
                cover_image.save(b,'png')
                b_image=b.getvalue()
                cover_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image)
                new_epub.add_item(cover_item)
            except Exception as e:
                errorText=f"Failed to add cover image to epub. Function add_cover_image Error: {e}"
                logging.warning(errorText)
                write_to_logs(errorText)

        new_epub.toc = toc_list
        new_epub.spine = toc_list
        new_epub.add_item(epub.EpubNcx())
        new_epub.add_item(epub.EpubNav())

        try:
            dirLocation="./books/epubs/temporary/"+book_title+".epub"
            if (check_directory_exists(dirLocation)):
                os.remove(dirLocation)
            epub.write_epub(dirLocation,new_epub)
        except Exception as e:
            errorText=f"Error with storing epub. Function store_epub. Error: {e}"
            write_to_logs(errorText)
        return dirLocation
                







#https://www.reddit.com/r/learnpython/comments/4zzn69/how_do_i_get_adblockplus_to_work_with_selenium/
#ADBLOCKING METHOD





async def main_interface(url, cookie):
    try:
        if (cookie):
            setCookie(cookie)
        epub_producer = None
        if "royalroad.com" in url:
            epub_producer = RoyalRoadEpubProducer()
            logging.warning('Creating scraper')
            scraper=RoyalRoadScraper()
            prefix="rr"
        elif "spacebattles.com" in url:
            epub_producer=SpaceBattlesEpubProducer()
            logging.warning('Creating scraper')
            scraper=SpaceBattlesScraper()
            prefix="sb"
            normalized_url = url if url.endswith('/') else url + '/'
            if re.search(r'/reader/page-\d+/$',normalized_url):
                url = re.sub(r'/reader/page-\d+/?$', '/reader/', url)
            elif not url.rstrip('/').endswith('/reader'):
                if url.endswith('/'):
                    url += 'reader/'
                else:
                    url += '/reader/'
        elif "foxaholic.com" in url:
            epub_producer = FoxaholicEpubProducer()
            logging.warning('Creating scraper')
            scraper=FoxaholicScraper()
            prefix="fx"
            if (cookie is None):
                errorText="Function main_interface. Error: Cookie is required for Foxaholic. Please provide a cookie."
                logging.warning(errorText)
                write_to_logs(errorText)
                return None
        elif "novelbin.com" or "novelbin.me" in url:
            epub_producer = NovelBinEpubProducer()
            logging.warning('Creating scraper')
            scraper=NovelBinScraper()
            prefix="nb"
            if (cookie is None):
                errorText="Function main_interface. Error: Cookie is required for NovelBin. Please provide a cookie."
                logging.warning(errorText)
                write_to_logs(errorText)
                return None
        else:
            raise ValueError("Unsupported website")
        logging.warning(url)
        logging.warning('Fetching novel data')
        
        bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle, latestChapterID= await scraper.fetch_novel_data(url)
        
        style=open("style.css","r").read()
        default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)
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
        bookID=remove_invalid_characters(bookID)
        new_epub=await instantiate_new_epub(bookID,bookTitle,bookAuthor,default_css)
        
        
        
        def ensure_bookid_prefix(bookID, prefix):
            """
            Ensures the bookID starts with one of the valid prefixes ('rr', 'sb', 'fx').
            If not, prepends the given prefix.
            """
            valid_prefixes = ("rr", "sb", "fx","nb")
            if any(bookID.startswith(p) for p in valid_prefixes):
                return bookID
            return f"{prefix}{bookID}"
        
        bookID=ensure_bookid_prefix(bookID, prefix)
        
        override = True
        #TODO: DONE If the book already exists, we should check if the latest chapter is the same as the one in the database.
        #To do this, I need to change the way latest chapters are stored in the database. I need to store the latest chapter's name and ID
        #and make the name be the one that is displayed on the front end, while using the ID to compare latest chapters
        if (override):
            await scraper.process_new_book(url, bookTitle)
            
        else:
            if (check_existing_book(bookID) or check_existing_book_Title(bookTitle)):
                logging.warning(f"Book {bookTitle} already exists in the database with ID {bookID}. Checking for new chapters.")
                if not (check_recently_scraped(bookID)):
                    logging.warning(f"Book {bookTitle} has not been scraped recently. Checking to see if latest is already stored.")
                    if not (check_latest_chapter(bookID,bookTitle,latestChapterTitle)):
                        logging.warning(f"Latest chapter {latestChapterTitle} is not the same as the one in the database. Processing new book.")
                        await scraper.process_new_book(url, bookTitle)
                    else:
                        logging.warning(f"Book {bookTitle} already exists in the database with the latest chapter {latestChapterTitle}. No new chapters to scrape.")
        
        #TODO: DONE I also need to modify SpacebattlesEpubProducer. Currently, the latest chapter is considered the last page of spacebattles reader mode.
        #Due to how spacebattles works, it does not check for new chapters added to the page. Meaning, I can store 5 threadmarks on last page, and the sixth won't be detected.
        #TODO: DONE I also need to modify all the EpubProducers to handle broken images so that it won't break the epub generation.
        
        await epub_producer.produce_epub(bookTitle,default_css,new_epub)
        rooturl=""
        
        match = re.search(r"https://(?:www\.)?([A-Za-z0-9.-]+)", url)
        if match:
            rooturl=match.group(1)
        first,last,total=get_first_last_chapter(bookTitle)
        
        directory = create_epub_directory_url(bookTitle)
        create_Entry(
            bookID=bookID,
            bookName=bookTitle,
            bookAuthor=bookAuthor,
            bookDescription=description,
            websiteHost=rooturl,
            firstChapter=first,
            lastChapterID=last,
            lastChapterTitle=latestChapterTitle,
            lastScraped=lastScraped,
            totalChapters=total,
            directory=directory
        )
        
        create_latest(
            bookID="-1",
            bookName=bookTitle,
            bookAuthor=bookAuthor,
            bookDescription=description,
            websiteHost=rooturl,
            firstChapter=first,
            lastChapterID=last,
            lastChapterTitle=latestChapterTitle,
            lastScraped=lastScraped,
            totalChapters=total,
            directory=directory
        )
        
        return directory
    
    
    except ValueError as e:
        logging.error(f"Error: {e}")
#logging.warning(asyncio.run (x.RoyalRoad_Fetch_Novel_Data("https://www.royalroad.com/fiction/100326/into-the-unown-pokemon-fanfiction-oc")))
cookie="cf_clearance=4YNHzi6yQ9hGxpibli5x.Gz6iZ5HO78TvmjYgbXRwaM-1749503301-1.2.1.1-xCTfyddFqJIvgB9vWQ_H.t9qcdeyo_83iQVimjkpEPymUFbXWEqfNVUGEpmYyWb6nGc09DCoXYoDW0MjhHqyiNjYsMYpy51B3m5pjBLwTtCvkhfriZK0Hl2L0WX8gUQiyc1MXwwOxYBPhNjzKnL0XvYhQ7L0RhL86pXtRuNOljMyRFMugA8zDbJYTmhGLPwV4_Pq96hFpbk5vduZJJkrsYjj0inCAKpTbtQgkBQNW.dbqSba9HJrvdG8F6bwQzT90paRM.Fc_yVCAVBU2SuHnYFuPFUftQDHqGuA6OLjgVeMVZvI5XRF0BzufIkC42tE_t6wV8ERlcsy_XEJ1BhTN.3k6_At0SKbVU.jom268.Y"
#logging.warning(asyncio.run (main_interface("https://novelbin.me/novel-book/raising-orphans-not-assassins", cookie or None)))
# x=NovelBinScraper()
# logging.warning(asyncio.run (x.fetch_novel_data("https://novelbin.me/novel-book/raising-orphans-not-assassins")))

















#royalroad cookie: .AspNetCore.Identity.Application
rrcookie=os.getenv("ROYALROAD_ACCOUNT_COOKIE")

specialHeaders={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "cookie":rrcookie
}

async def royalroad_follow_list_soup(url, specialHeaders):
    async with aiohttp.ClientSession(headers = specialHeaders) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = bs4.BeautifulSoup(html, 'html.parser')
                    return soup
                
async def retrieve_from_royalroad_follow_list():
    soup=await royalroad_follow_list_soup("https://www.royalroad.com/my/follows", specialHeaders)
    bookTitles=soup.find_all("h2",{"class":"fiction-title"})
    bookLinks=[]
    for title in bookTitles:
        a_tag = title.find("a")
        if a_tag and "href" in a_tag.attrs:
            bookLinks.append(f"https://www.royalroad.com{a_tag["href"]}")
    logging.warning(bookLinks)
    for link in bookLinks:
        logging.warning(await main_interface(link))
    




async def search_page(input: str, selectedSite: str, searchConditions:dict, cookie):
    if "royalroad"in selectedSite:
        scraper=RoyalRoadScraper()
    elif "spacebattles" in selectedSite:
        scraper=SpaceBattlesScraper()
    elif "foxaholic" in selectedSite:
        scraper=FoxaholicScraper()
        if (cookie is None):
            errorText="Function search_page. Error: Cookie is required for Foxaholic. Please provide a cookie."
            logging.warning(errorText)
            write_to_logs(errorText)
            return None
    elif "novelbin" in selectedSite:
        scraper=NovelBinScraper()
        if (cookie is None):
            errorText="Function search_page. Error: Cookie is required for NovelBin. Please provide a cookie."
            logging.warning(errorText)
            write_to_logs(errorText)
            return None
    else:
        raise ValueError("Unsupported website")
    
    
    
    url_pattern = re.compile(r'^(https?://|www\.)', re.IGNORECASE)
    if url_pattern.match(input.strip()):
        url=input
        if (scraper is SpaceBattlesScraper()):
            normalized_url = url if url.endswith('/') else url + '/'
            if re.search(r'/reader/page-\d+/$',normalized_url):
                url = re.sub(r'/reader/page-\d+/?$', '/reader/', url)
            elif not url.rstrip('/').endswith('/reader'):
                if url.endswith('/'):
                    url += 'reader/'
                else:
                    url += '/reader/'

    else:
        def adapt_search_conditions(search_conditions):
            """
            Converts search_conditions dict to the adapted format for SpaceBattles/RoyalRoad queries.
            Only includes keys that are present and valid.
            """
            adapted_conditions = {}
            if not isinstance(search_conditions, dict) or not search_conditions:
                return adapted_conditions  # Return empty dict if no conditions

            # Handle threadmark_status as indexed keys if it's a list
            threadmark_status = search_conditions.get("threadmark_status", [])
            if isinstance(threadmark_status, list):
                for idx, status in enumerate(threadmark_status):
                    adapted_conditions[f"threadmark_index_statuses[{idx}]"] = status

            search_scope = search_conditions.get("search_scope", "title")
            if isinstance(search_scope, dict):
                for k, v in search_scope.items():
                    adapted_conditions[k] = v

            # Directly copy over other relevant keys if present
            for key in ["min_word_count", "max_word_count", "sort_by", "direction", "true_search"]:
                if key in search_conditions:
                    # For "sort_by", convert to "order" as required by some endpoints
                    if key == "sort_by":
                        adapted_conditions["order"] = search_conditions[key]
                    else:
                        adapted_conditions[key] = search_conditions[key]
                
            return adapted_conditions
        searchConditions=adapt_search_conditions(searchConditions)
        
        #If input is not a URL, treat it as a search query
        #I need to standardize the query_site function 
        url=await scraper.query_site(input.strip(), searchConditions,cookie)
        logging.warning(f"Search URL: {url}")
    
    if not url_pattern.match(url.strip()):
        errorText=f"Function search_page. Error: There was no result. Please check the input or the search conditions."
        logging.warning(errorText)
        write_to_logs(errorText)
        return None
    bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle,latestChapterID= await scraper.fetch_novel_data(url)
    bookID=remove_invalid_characters(bookID)
    listofChapterTitles=await scraper.fetch_chapter_title_list(url)
    listofChapters = await scraper.fetch_chapter_list(url)
    logging.warning(listofChapters)
    return {
        "bookID": bookID,
        "bookTitle": bookTitle,
        "bookAuthor": bookAuthor,
        "bookDescription": description,
        "latestChapterTitle": latestChapterTitle,
        "chapterTitles": listofChapterTitles,
        "chapterUrls": listofChapters,
        "mainURL": url,
    }





#available additionalConditions for search-filter
#&t=post&c[child_nodes]=1&c[nodes][0]=18 is for forum: Creative Writing
#&c[title_only]=1 is for title only search
#https://forums.spacebattles.com/forums/creative-writing.18/?tags[0]=trails+series&nodes[0]=48&nodes[1]=169&nodes[2]=115
#tag searching: ?tags[0]=trails+series
#forums: &nodes[0]=48&nodes[1]=169&nodes[2]=40&nodes[3]=115
#48 is original writing, 169 is unlisted original fiction, 40 is creative writing archives, and 115 is worm.
#word count filters: &min_word_count=1000&max_word_count=1000000
#sort by options:
#order=title, reply_count,view_count, last_threadmark, watchers
#&direction=desc/asc
#threadmark status
#&threadmark_index_statuses[0]=incomplete
#&threadmark_index_statuses[1]=complete
#&threadmark_index_statuses[2]=hiatus

#available additionalConditions for search-search
#https://forums.spacebattles.com/search/104096825/?q=Trails+Of&t=post&c[child_nodes]=1&c[nodes][0]=18&c[title_only]=1&o=date
#&c[container_only]=1
#&c[gifts_only]=1 (0/1 False/True)
#&c[tags]=word1+word2
#&c[threadmark_only]=1
#&c[title_only]=1
#&c[users]=String_Name
async def test(url):
    spacebattles_scraper=SpaceBattlesScraper()
    threadmarks=await spacebattles_scraper.fetch_chapter_title_list(url)
    logging.warning(threadmarks)

#asyncio.run(test("https://forums.spacebattles.com/threads/quahinium-industries-shipworks-kancolle-si.1103320/reader/"))


#title: query argument, sortby: query sort argument, direction: ascending or descending, additionalConditions: additional parameters in key-value pairs
async def spacebattles_search_interface(title:str, sortby: str, direction: str,additionalConditions: dict):
    spacebattles_scraper = SpaceBattlesScraper()
    title = title.replace(" ", "+")
    title = title.lower()
    def clean_conditions(conditions):
        filtered_conditions = {}
        for key, value in conditions.items():
            if value not in (0, "", None):
                if isinstance(value, str):
                    filtered_conditions[key] = value.replace(" ", "+")
                else:
                    filtered_conditions[key] = value
        return filtered_conditions
    additionalConditions = clean_conditions(additionalConditions)
    
    
    #result = await spacebattles_scraper.query_spacebattles(title, sortby, direction, additionalConditions)
    result = await spacebattles_scraper.query_spacebattles_filter_version(title, sortby, direction, additionalConditions)
    #print(result)  # Should print the first search result link or an error message
    return result
    #returns a link


# result=asyncio.run(spacebattles_search_interface("Trails Of", "date", {
#     "c[container_only]": 0,
#     "c[gifts_only]": 0,
#     "c[tags]": "",
#     "c[threadmark_only]": 0,
#     "c[title_only]": 1,
#     "c[users]": ""
# }))

# result = asyncio.run(spacebattles_search_interface("Trails series", "", "" ,{
#     "min_word_count": 5000,
#     "threadmark_index_statuses[0]":"incomplete",
#     "threadmark_index_statuses[1]":"complete"}))

# logging.warning(result)

class MissingBookDataException(Exception):
    def __init__(self, missing_keys):
        message = f"Missing required keys in book dict: {', '.join(missing_keys)}"
        super().__init__(message)
        self.missing_keys = missing_keys


async def search_page_scrape_interface(book: dict, cookie: str, additionalConditions: dict):
    try:
        bookID=book["bookID"]
        bookTitle=book["bookTitle"]
        bookAuthor=book["bookAuthor"]
        websiteHost=book["websiteHost"]
        book_chapter_urls=book["book_chapter_urls"]
        mainBookURL=book["mainBookURL"]
    except KeyError as e:
        missing = [str(e)]
        raise MissingBookDataException(missing)


    if websiteHost=="royalroad":
        epub_producer=RoyalRoadEpubProducer()
    elif websiteHost=="forums.spacebattles":
        epub_producer=SpaceBattlesEpubProducer()
    #TODO: Make the rest of it work by copying the royalroad method
    
    
    # elif websiteHost=="foxaholic":
    #     epub_producer=FoxaholicEpubProducer()
    #     prefix="fx"
    #     if (cookie is None):
    #         errorText="Function search_page_scrape_interface. Error: Cookie is required for Foxaholic. Please provide a cookie."
    #         logging.warning(errorText)
    #         write_to_logs(errorText)
    #         return None
    # elif websiteHost=="novelbin":
    #     epub_producer=NovelBinEpubProducer()
    #     prefix="nb"
    #     if (cookie is None):
    #         errorText="Function search_page_scrape_interface. Error: Cookie is required for NovelBin. Please provide a cookie."
    #         logging.warning(errorText)
    #         write_to_logs(errorText)
    #         return None
    else:
        raise ValueError("Unsupported website")
    
    style=open("style.css","r").read()
    default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)
    
    async def instantiate_new_epub(bookID,bookTitle,bookAuthor):
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
    
    bookID=remove_invalid_characters(bookID)
    new_epub=await instantiate_new_epub(bookID,bookTitle,bookAuthor)
    

    dirLocation= await epub_producer.produce_custom_epub(new_epub,bookTitle,default_css,book_chapter_urls, mainBookURL, additionalConditions)
    logging.error(dirLocation)    
    return dirLocation
# scraper = SpaceBattlesScraper()
# url="https://forums.spacebattles.com/threads/the-new-normal-a-pok%C3%A9mon-elite-4-si.1076757/threadmarks?"
# result=asyncio.run(scraper.fetch_chapter_title_list(url))
# logging.warning("Results:")
# logging.warning(result)
#NOTE TO SELF. TEST THE NEW FETCH_CHAPTER_TITLE_LIST FUNCTIONS FOR EACH SITE

async def update_book(book: dict):
    try:
        bookID=book["bookID"]
        bookTitle=book["bookTitle"]
        orderOfContents=book["orderOfContents"]
    except KeyError as e:
        missing = [str(e)]
        raise MissingBookDataException(missing)
    
    if ((check_existing_book_Title(bookTitle) or check_existing_book(bookID)) and orderOfContents):
        logging.warning(f"Book {bookTitle} already exists in the database. Updating the book.")
        def write_order_of_contents(book_title, chapter_metadata):
            file_location = f"./books/raw/{book_title}/order_of_chapters.txt"
            logging.warning(chapter_metadata)
            with open(file_location, "w") as f:
                for data in chapter_metadata:
                    if isinstance(data, str):
                        data = data.strip().split(";")
                    logging.warning(data)
                    f.write(";".join(map(str, data))+ "\n")
        
        write_order_of_contents(bookTitle, orderOfContents)
        
        try:
            latestChapterTitle=orderOfContents[-1].split(";")[2].strip() if orderOfContents else "N/A"
            def strip_latest_chapter_title(latestChapterTitle: str) -> str:
                """
                For a string like:
                "Beneath the Dragoneye Moons/Beneath the Dragoneye Moons - 2230094 - Chapter 622 - Overthrowing the Tyrants XV.html"
                returns: "Chapter 622 - Overthrowing the Tyrants XV"
                """
                # Get the last part after the last '/'
                last_part = latestChapterTitle.split("/")[-1]
                # Split on ' - ' and get everything after the second dash
                parts = last_part.split(" - ")
                # Find the index of the part that starts with 'Chapter'
                chapter_idx = next((i for i, p in enumerate(parts) if p.strip().startswith("Chapter")), None)
                if chapter_idx is not None:
                    # Join 'Chapter ###' and everything after
                    chapter_title = " - ".join(parts[chapter_idx:])
                    # Remove .html if present
                    if chapter_title.endswith(".html"):
                        chapter_title = chapter_title[:-5]
                    return chapter_title.strip()
                # Fallback: just remove .html and return last part
                return last_part.replace(".html", "").strip()
            latestChapterTitle=strip_latest_chapter_title(latestChapterTitle)
        except Exception as e:
            errorText=f"Failed to retrieve latest chapter title from order of contents. Error: {e}"
            logging.warning(errorText)
            write_to_logs(errorText)
            latestChapterTitle="N/A"
        
        first,last,total=get_first_last_chapter(bookTitle)
        
        updated_book={
            "bookID": bookID,
            "bookTitle": bookTitle,
            "firstChapter": first,
            "lastChapterID": last,
            "totalChapters": total,
            "lastChapterTitle": latestChapterTitle,
        }
        update_entry(updated_book)
        return True
    else:
        errorText=f"Book {bookTitle} does not exist in the database. Please provide a valid book ID or title."
        logging.warning(errorText)
        write_to_logs(errorText)
        return None
        
        

















