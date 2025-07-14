

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
    get_Entry_Via_Title
)



from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from seleniumwire import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

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
    #TODO: Fix this. This is currently broken with an 'NoneType' error.
    
    async def produce_custom_epub(self, new_epub, book_title, css,book_chapter_urls):
        if not book_chapter_urls:
            errorText="Function: royalroad_produce_custom_epub. Error: No chapters found in the bookURL. Please check the URL or the book's availability."
            logging.warning(errorText)
            write_to_logs(errorText)
            return
        rrScraper=RoyalRoadScraper()
        
        toc_list = []
        image_counter=0
        current_image_counter=0
        try:
            for chapter_url in book_chapter_urls:
                logging.error(chapter_url)
                soup = await rrScraper.get_soup(chapter_url)
                #write_to_logs(str(soup).encode("ascii", "ignore").decode("ascii"))
                
                def extract_chapter_ID(chapter_url):
                    import re
                    match = re.search(r'/(\d+)/?$', chapter_url)
                    if match:
                        return match.group(1)

                chapter_id = extract_chapter_ID(chapter_url)
                chapter_title = await rrScraper.fetch_chapter_title(soup)
                chapter_title = remove_invalid_characters(chapter_title)
                # logging.warning(chapter_id)
                # logging.warning(chapter_title)
                file_chapter_title,image_counter,chapter_content=await rrScraper.process_new_chapter_non_saved(chapter_url, book_title, chapter_id,image_counter)
                #logging.warning(chapter_content)
                #chapter_conte_soup appears to not be working?
                chapter_content_soup=bs4.BeautifulSoup(str(chapter_content),'html.parser')
                #write_to_logs(str(chapter_content_soup).encode("ascii", "ignore").decode("ascii"))
                #logging.error(chapter_content_soup)
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
                latestChapterTitle=latestChapter.get_text()
                match=re.search(r'\b\d+(?:-\d+)?\b',latestChapterTitle)
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
                return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle,latestChapterID
            except Exception as e:
                errorText=f"Failed to get novel data. Function Spacebattles fetch_novel_data Error: {e}"
                write_to_logs(errorText)
    
    async def fetch_chapter_list(self,url):
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
    
    
    async def fetch_chapter_title_list(self, url):
        def normalize_spacebattles_url(url: str) -> str:
            # Find the last occurrence of digits/ and trim everything after
            match = re.search(r'(\d+/)', url)
            if match:
                idx = url.find(match.group(1)) + len(match.group(1))
                url = url[:idx]
            # Ensure it ends with threadmarks?per_page=200
            if not url.endswith('threadmarks?per_page=200'):
                url += 'threadmarks?per_page=200'
            return url
        url=normalize_spacebattles_url(url)
        
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


    #https://forums.spacebattles.com/search/104090354/?q=New+Normal&t=post&c[child_nodes]=1&c[nodes][0]=18&c[title_only]=1&o=date 
    #Basic format of search query
    #https://forums.spacebattles.com/search/104090768/?q=Cheese
    #& between each condition
    #c[title_only]
    #c[users]="Name"
    #o=date, or, o=word_count, or, o=relevance
    #This is for order
    async def query_spacebattles(self,title: str, sortby: str, additionalConditions: dict ,isSearchSearch: bool):
        try:
            if (title.isspace() or title==""):
                errorText=f"Failed to search title. Function query_spacebattles Error: No title inputted"
                write_to_logs(errorText)
                return "Invalid Title"
            #&t=post&c[child_nodes]=1&c[nodes][0]=18 is for forum: Creative Writing
            #&c[title_only]=1 is for title only search
            querylink = f"https://forums.spacebattles.com/search/104090354/?q={title}&t=post&c[child_nodes]=1&c[nodes][0]=18"
            for item in additionalConditions:
                querylink+=f"&{item}={additionalConditions[item]}"
                logging.warning(querylink)
            if (sortby not in ["date", "word_count", "relevance"]):
                errorText=f"Invalid sort-by condition. Continuing on with default. Function query_spacebattles Error: {sortby}"
                write_to_logs(errorText)
                sortby = "date"  # Default sort-by option
                querylink+=f"&o={sortby}"
                
                
            else:
                querylink+=f"&o={sortby}"
            logging.warning(querylink)
            
            async def get_soup(url):
                try:
                    driver = webdriver.Firefox(options=firefox_options)
                    driver.install_addon(path_to_extension, temporary=True)
                    driver.request_interceptor=interception
                    driver.get(url)
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
                resultLink=f"https://forums.spacebattles.com/threads{firstResult}"
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
    async def query_spacebattles_version_two(self,title: str, sortby: str, direction:str, additionalConditions: dict):
        try:
            if (title.isspace() or title==""):
                errorText=f"Failed to search title. Function query_spacebattles Error: No title inputted"
                write_to_logs(errorText)
                return "Invalid Title"
            
            querylink = f"https://forums.spacebattles.com/forums/creative-writing.18/?tags[0]={title}"
            if (sortby not in ["title", "reply_count", "view_count", "last_threadmark", "watchers"] and direction not in ["asc", "desc"]):
                errorText=f"Invalid sort-by condition. Continuing on with default. Function query_spacebattles_version_two Error: {sortby}"
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
                errorText=f"Search failed. Most likely reason: There wasn't any search results. Function query_spacebattles_version_two Error: {e}"
                write_to_logs(errorText)
                return "No Results Found"
        except Exception as e:
            errorText=f"Improper query attempt. Function query_spacebattles_version_two Error: {e} How did you even do this?"
            write_to_logs(errorText)
            return "Invalid Option"
        #These need to be added at the end to specify the forums.
        #THEY MUST BE at the end of the query.

    
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
    result = await spacebattles_scraper.query_spacebattles_version_two(title, sortby, direction, additionalConditions)
    #print(result)  # Should print the first search result link or an error message
    return result



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
    



def fuzzy_similarity(newBookTitle, existingBookTitles):
    """
    Returns the string from existingBookTitles with the highest similarity to newBookTitle,
    based on the longest common subsequence ratio.
    """
    def normalize_string(s):
        return re.sub(r'[\W_]+', '', s).lower()  # removes all non-alphanumeric chars and lowercases

    # Dynamic programming approach for LCS
    def levenshtein_distance(s1, s2):
        m, n = len(s1), len(s2)
        # Initialize distance matrix
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        # Compute distances
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,      # Deletion
                    dp[i][j - 1] + 1,      # Insertion
                    dp[i - 1][j - 1] + cost  # Substitution
                )
        return dp[m][n]

    best_match = None
    best_score = 0.0
    newBookTitle = normalize_string(newBookTitle)
    for book in existingBookTitles:
        if not newBookTitle or not book:
            continue
        book= normalize_string(book)
        #logging.warning(f"Comparing '{newBookTitle}' with '{book}'")
        lev_dist = levenshtein_distance(newBookTitle, book)
        max_len = max(len(newBookTitle), len(book))
        score = 1 - (lev_dist / max_len) if max_len > 0 else 0.0
        if score > best_score:
            best_score = score
            best_match = book
    #logging.warning(f"Best match for '{newBookTitle}' is '{best_match}' with score {best_score:.2f}")
    return best_match, best_score



def store_chapter_version_two(chapterContent,bookTitle,fileTitle):
    bookDirLocation = "./books/imported/" + bookTitle+"/"
    if not check_directory_exists(bookDirLocation):
        make_directory(bookDirLocation)

    # Check if the chapter already exists
    dirLocation = f"./books/imported/{bookTitle}/{fileTitle}.html"
    if check_directory_exists(dirLocation):
        return

    # Write the chapter content to the file with UTF-8 encoding
    chapterDirLocation = "./books/imported/" + bookTitle + "/"
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


import ebooklib
import xml.etree.ElementTree as ET

def extract_series_from_epub(book):
    try:
        # 1. Try to find 'series' in book.metadata (all namespaces)
        for ns, meta_dict in book.metadata.items():
            for key, values in meta_dict.items():
                if 'series' in key.lower():
                    for value, attrs in values:
                        # Try 'content' in attrs first
                        if isinstance(attrs, dict) and 'content' in attrs and attrs['content']:
                            return attrs['content']
                        # Try value itself if it's a string and not None
                        if value:
                            return value
        # 2. Try to find in OPF XML <meta> tags
        opf_item = None
        for item in book.get_items():
            if item.file_name.endswith('.opf'):
                opf_item = item
                break
        if opf_item:
            opf_xml = opf_item.get_content()
            root = ET.fromstring(opf_xml)
            # Find <metadata> element (namespace-agnostic)
            metadata_elem = None
            for elem in root.iter():
                if elem.tag.lower().endswith('metadata'):
                    metadata_elem = elem
                    break
            if metadata_elem is not None:
                for meta in metadata_elem.iter():
                    if meta.tag.lower().endswith('meta'):
                        # Check both 'name' and 'property' attributes for 'series'
                        for attr in ['name', 'property']:
                            if attr in meta.attrib and 'series' in meta.attrib[attr].lower():
                                if 'content' in meta.attrib:
                                    return meta.attrib['content']
                                elif meta.text:
                                    return meta.text
    except Exception as e:
        errorText=f"Failed to extract series from epub. Function extract_series_from_epub Error: {e}, book:{book.get_metadata('DC', 'title')}"
        #logging.error(errorText)
        write_to_logs(errorText)
        
    # Not found
    return ""

# Usage in your import_from_epub:
#fileName="DRR 3 - Fragments of Time - Silver Linings.epub"
#dirLocation= f"./books/imported/{fileName}"

def remove_tags_from_inside_brackets(text):
    """
    Removes all text inside brackets, including the brackets themselves.
    """
    return re.sub(r'[\[\(].*?[\]\)]', '', text)

async def process_book_title(book):
    series = extract_series_from_epub(book)
    series = remove_invalid_characters(series)
    if series and series !="":
        bookTitle = series
    else:
        # Fallback to dc:title
        bookTitle = book.get_metadata('DC', 'title') 
        if bookTitle and isinstance(bookTitle, list) and len(bookTitle) > 0:
            bookTitle = bookTitle[0][0]
            bookTitle= remove_tags_from_inside_brackets(bookTitle)
            bookTitle=remove_invalid_characters(bookTitle)
        else:
            bookTitle = ""
    return bookTitle


def detect_epub_source(book):
    """
    Attempts to detect the source website of an epub by searching for known domains
    in the OPF file, stylesheets, and chapter HTML content.
    Returns the source as a string, or 'Unknown' if not found.
    """

    # List of known sources and their identifying keywords/domains
    known_sources = {
        "royalroad.com": ["royalroad.com"],
        "scribblehub.com": ["scribblehub.com"],
        "forums.spacebattles.com": ["spacebattles.com"],
        "novelbin.me": ["novelbin.me", "novelbin.com"],
        "foxaholic.com": ["foxaholic.com"],
        # Add more as needed
    }

    # Helper to check for keywords in a string
    def find_source_in_text(text):
        for source, keywords in known_sources.items():
            for keyword in keywords:
                if keyword in text:
                    return source
        return None

    # 1. Check OPF file (metadata)
    opf_item = None
    for item in book.get_items():
        if item.file_name.endswith('.opf'):
            opf_item = item
            break
    if opf_item:
        opf_content = opf_item.get_content().decode(errors="ignore")
        found = find_source_in_text(opf_content)
        if found:
            return found

    # 2. Check all stylesheets
    for item in book.get_items_of_type(ebooklib.ITEM_STYLE):
        style_content = item.get_content().decode(errors="ignore")
        found = find_source_in_text(style_content)
        if found:
            return found

    # 3. Check all HTML chapters
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        html_content = item.get_content().decode(errors="ignore")
        found = find_source_in_text(html_content)
        if found:
            return found

    # 4. Check all images (sometimes watermarks or URLs)
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        if hasattr(item, 'file_name') and find_source_in_text(item.file_name):
            return find_source_in_text(item.file_name)

    # 5. Fallback
    return "Unknown"


async def fetch_novel_data_from_epub(dirLocation):
    
    try:
        #logging.warning(f"Importing from epub: {dirLocation}")
        book = epub.read_epub(dirLocation)
        #logging.warning(book)
        bookTitle=await process_book_title(book)
        
        bookAuthor = book.get_metadata('DC', 'creator')
        if bookAuthor and isinstance(bookAuthor, list) and len(bookAuthor) > 0:
            bookAuthor = bookAuthor[0][0]
        else:
            bookAuthor = ""

            
        bookDescription = book.get_metadata('DC', 'description') if book.get_metadata('DC', 'description') else ""
        bookDescription= bookDescription[0][0] if isinstance(bookDescription, list) and len(bookDescription) > 0 else bookDescription
        if ("\n" in bookDescription):
            bookDescription=bookDescription.replace("\n"," ")
        if ("  " in bookDescription):
            bookDescription=bookDescription.replace("  "," ")
                    
        origin=detect_epub_source(book)
        
        bookID=str(generate_new_ID(bookTitle,origin))
        lastScraped = datetime.datetime.now()
        latestChapterTitle = ""
        try:
            chapters = list(book.get_items())
            # Find the last non-cover.xhtml document with a valid title
            idx = len(chapters) - 1
            latestChapterTitle = ""
            while idx >= 0:
                last_chapter = chapters[idx]
                # Skip if it's a cover.xhtml file
                if last_chapter.get_name().lower().endswith("cover.xhtml"):
                    idx -= 1
                    continue
                soup = bs4.BeautifulSoup(last_chapter.get_content(), 'html.parser')
                # Try to find the latest chapter title from headings
                title = ""
                for tag in ['h1', 'h2', 'h3']:
                    heading = soup.find(tag)
                    if heading and heading.get_text(strip=True):
                        title = heading.get_text(strip=True)
                        break
                if title:
                    latestChapterTitle = remove_invalid_characters(title)
                    break  # Found a valid title, exit loop
                idx -= 1
            if not latestChapterTitle:
                latestChapterTitle = "N/A"
                
        
        
        except Exception as e:
            errorText=f"Failed to extract latest chapter title from epub. Function fetch_novel_data_from_epub Error: {e}, file: {dirLocation}"
            logging.error(errorText)
            write_to_logs(errorText)
            # Fallback if not found
            latestChapterTitle="N/A"

        
        
        latestChapterID="N/A"
        
        #Regular Format: bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle
        return bookID, bookTitle, bookAuthor, bookDescription, origin, lastScraped, latestChapterTitle,latestChapterID



    except Exception as e:
        errorText=f"Failed to import from epub: {e}"
        logging.error(errorText)
        write_to_logs(errorText)
        return None, None, None,None,None,None,None



def get_epubs_to_import():
    dirLocation= "./books/imported/epubs"
    dir_list=os.listdir(dirLocation)
    #print(f"Files in {dirLocation}:")
    #print(dir_list)
    override=True
    if (override):
        filtered_list = [f for f in dir_list if "DIE RESPAWN REPEAT" in f]
        return filtered_list
        
        #return sorted(dir_list)[:10]
    return dir_list

#dir_list=get_epubs_to_import()

def get_all_files_in_directory(directory):
    dir_list=os.listdir(directory)
    print(f"Files in {directory}:")
    print(dir_list)
    return dir_list

def compare_files_in_directory(directory):
    dir_list=get_all_files_in_directory(directory)
    with open("{directory}/order_of_chapters.txt", "r") as f:
        order_of_contents_chapters= f.readlines()
    file_names = []
    for line in order_of_contents_chapters:
        parts = line.strip().split(";")
        if len(parts) >= 3:
            file_path = parts[2]
            file_name = os.path.basename(file_path)
            file_names.append(file_name)
    extra_files = [f for f in dir_list if f not in file_names]

    print("Files in directory not listed in order_of_chapters.txt:")
    for f in extra_files:
        print(f)
    
    
    
def get_existing_order_of_contents(book_title):
        # Default implementation
        dir_location = f"./books/imported/{book_title}/order_of_chapters.txt"
        if os.path.exists(dir_location):
            with open(dir_location, "r") as f:
                return f.readlines()
        return []

async def compare_existing_with_import(dir_list,condition):
    existingBookTitles=get_all_book_titles()
    matchingBooks = set()  # Use a set for uniqueness
    
    for item in dir_list:
        if item.endswith('.epub'):
            #logging.warning(f"Extracting from file: {item}")
            dirLocation= f"./books/imported/epubs/{item}"
            bookID, bookTitle, bookAuthor, bookDescription, origin, lastScraped, latestChapterTitle = await fetch_novel_data_from_epub(dirLocation)
            if bookTitle:
                #logging.warning(f"Read: {bookTitle} by {bookAuthor}")
                bookMatch,bookScore=fuzzy_similarity(bookTitle, existingBookTitles)
                if (condition):
                    if (bookScore>=0.8):
                        #logging.warning(f"Book {bookTitle} is similar to existing book {bookMatch} with score {bookScore}. Skipping.")
                        
                        matchingBooks.add(bookTitle)  # Add to set
                else:
                    if (bookScore<0.8):
                        #logging.warning(f"Book {bookTitle} is not similar to existing book {bookMatch} with score {bookScore}. Adding to matching books.")
                        matchingBooks.add(bookTitle)
                
            else:
                errorText=f"Failed to import from {item}"
                write_to_logs(errorText)
                logging.warning(errorText)
            
    return matchingBooks
#logging.warning(asyncio.run(compare_existing_with_import(dir_list)))
# logging.warning(asyncio.run(import_from_epub("Legendary Shadow Blacksmith Ch1-102.epub")))

async def extract_chapter_from_book(dirLocation):
    
    fileName=dirLocation.split("/")[-1]
    if not fileName.endswith('.epub'):
        errorText=f"Function extract_chapter_from_book Error: {fileName} is not an epub file."
        write_to_logs(errorText)
        return
    
    def extract_volume_or_book_number(fileName):
        """
        Extracts the volume or book number from a fileName string.
        Looks for patterns like 'vol5', 'vol_5', 'vol-5', 'book5', 'book_5', 'book-5', case-insensitive.
        Returns the number as an integer if found, otherwise None.
        """
        match = re.search(r'(?:vol|book)[\s\-_]*([0-9]+)', fileName, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None
    volume_number = extract_volume_or_book_number(fileName)
    chapterID=0
    if volume_number:
        chapterID = volume_number * 10000
    
    chapter_metadata = []
    book = epub.read_epub(dirLocation)
    bookTitle=await process_book_title(book)
    def get_existing_order_of_contents(book_title):
        # Default implementation
        dir_location = f"./books/imported/{book_title}/order_of_chapters.txt"
        if os.path.exists(dir_location):
            with open(dir_location, "r") as f:
                return f.readlines()
        return []
    
    existingChapters = get_existing_order_of_contents(bookTitle)
    existingChapters = [line.strip().split(";") for line in existingChapters if line.strip()]
    
    
    image_dir = f"./books/imported/{bookTitle}/images/"
    cover_dir=f"./books/imported/{bookTitle}/"
    try:
        numberofImages=os.listdir(image_dir)
        currentImageCounter=len(numberofImages)-1 if numberofImages else 0
    except Exception as e:
        errorText=f"Failed to get number of images in {image_dir}. Function extract_chapter_from_book Error: {e}"
        logging.error(errorText)
        write_to_logs(errorText)
        currentImageCounter=0
        numberofImages=[]
                
    
    #Cover Image Only
    images = book.get_items_of_type(ebooklib.ITEM_IMAGE)
    if images:
        for image in images:
            if ("cover" in image.file_name):
                image_path = f"{cover_dir}cover_image.png"
                if not os.path.exists(cover_dir):
                    os.makedirs(cover_dir)
                if not os.path.exists(image_path):
                    with open(image_path, "wb") as f:
                        f.write(image.get_content())
                else:
                    image_bytes = image.get_content()
                    if not is_image_duplicate(image_bytes,image_dir):
                        existingImages=get_all_files_in_directory(cover_dir)
                        cover_image_count = sum(1 for f in existingImages if "cover_image" in f)
                        image_path = f"{cover_dir}cover_image_{cover_image_count}.png"
                        try:
                            with open(image_path, "wb") as f:
                                f.write(image.get_content())
                        except Exception as e:
                            errorText=f"Failed to write cover image bytes to file. Function extract_chapter_from_book Error: {e}, file:{bookTitle}"
                            write_to_logs(errorText)
                            continue
                    else:
                        logging.warning(f"Cover Image already exists in {image_dir}. Skipping.")
    
    #reset counter
    currentImageCounter=len(numberofImages)-1 if numberofImages else 0
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            print('==================================')
            print('NAME : ', item.get_name())
            print('----------------------------------')
            #print(item.get_content())
            #print('==================================')
            
            soup= bs4.BeautifulSoup(item.get_content(), 'html.parser')
            
            title =soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
            if title=="":
                title=soup.find('h2').get_text(strip=True) if soup.find('h2') else ""
            if title=="":
                title=soup.find('h3').get_text(strip=True) if soup.find('h3') else ""
            if title=="":
                continue
            
            chapterContent = soup
            img_tags = chapterContent.find_all('img')
            image_dir = f"./books/imported/{bookTitle}/images/"
            if not os.path.exists(image_dir):
                os.makedirs(image_dir)
            images = [img['src'] for img in img_tags if img.has_attr('src')]
            if (images):
                logging.warning(images)

            # Get all image items in the book for matching
            image_items = {img_item.file_name: img_item for img_item in book.get_items_of_type(ebooklib.ITEM_IMAGE)}

            for img in img_tags:
                img_src = img['src']
                # Try to find the corresponding image item in the epub
                matched_item = None
                for file_name, img_item in image_items.items():
                    if img_src in file_name or file_name in img_src:
                        matched_item = img_item
                        break
                if not matched_item:
                    continue  # Skip if not found in epub

                image_bytes = matched_item.get_content()
                image_path = f"{image_dir}image_{currentImageCounter}.png"

                # Check for duplicate in directory
                if not is_image_duplicate(image_bytes, image_dir):
                    # Save new image and update src
                    with open(image_path, "wb") as f:
                        logging.warning(f"Saving image {currentImageCounter} to {image_path}")
                        try:
                            f.write(image_bytes)
                            img['src'] = f"images/image_{currentImageCounter}.png"
                            currentImageCounter += 1

                        except Exception as e:
                            errorText=f"Failed to write image bytes to file. Function extract_chapter_from_book Error: {e}"
                            write_to_logs(errorText)
                            continue
                else:
                    # If duplicate, find the existing image index to point to
                    # Loop through files to find the match and set src accordingly
                    for idx, file in enumerate(sorted(os.listdir(image_dir))):
                        file_path = os.path.join(image_dir, file)
                        epub_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                        existing_img = Image.open(file_path).convert("RGB")
                        try:
                            if epub_img.size == existing_img.size:
                                diff = ImageChops.difference(epub_img, existing_img)
                                if not diff.getbbox():
                                    img['src'] = f"images/{file}"
                                    break
                        except Exception:
                            continue
            
            
            #logging.warning(f"Chapter Title: {title}")
            fileTitle= f"{bookTitle} - {remove_invalid_characters(title)}"
            logging.warning(f"File Title: {fileTitle}")
            store_chapter_version_two(chapterContent, bookTitle, fileTitle)
            chapter_metadata.append([chapterID,title,f"./books/imported/{bookTitle}/{fileTitle}.html"])
            chapterID+=1
            
    
    
    def merge_chapter_lists_preserve_order(list1, list2):
        """
        Merge two lists of chapters, preserving order and removing duplicates.
        Duplicates are detected by chapter title (case-insensitive, stripped).
        Returns a merged list with unique chapters, order: all from list1, then unique from list2.
        """
        def chapter_key(chapter):
            # chapter_metadata is saved as [ID, Title, FilePath]
            # We assume the title is always at index 1, and it can be a list
            if isinstance(chapter, list):
                return chapter[1].strip().lower()
            return chapter.strip().lower()

        seen = set()
        merged = []
        chapterID=0
        # Add all chapters from list1, marking them as seen
        for chapter in list1:
            key = chapter_key(chapter)
            if key not in seen:
                merged.append(chapter)
                seen.add(key)
                chapterID+=1

        # Add only new chapters from list2
        for chapter in list2:
            key = chapter_key(chapter)
            if key not in seen:
                chapter=[chapterID,chapter[1],chapter[2]]
                merged.append(chapter)
                seen.add(key)
                chapterID+=1
        logging.warning(merged)
        return merged
    
    merged_chapter_metadata=merge_chapter_lists_preserve_order(existingChapters, chapter_metadata)
    #logging.warning(merged_chapter_metadata)
    def write_order_of_contents(book_title, chapter_metadata):
        file_location = f"./books/imported/{book_title}/order_of_chapters.txt"
        #logging.warning(chapter_metadata)
        with open(file_location, "w") as f:
            for data in chapter_metadata:
                if isinstance(data, str):
                    data = data.strip().split(";")
                #logging.warning(data)
                f.write(";".join(map(str, data))+ "\n")
    write_order_of_contents(bookTitle, merged_chapter_metadata)
    
    #Create directory for the book
    #make_directory(f"./books/imported/{bookTitle}")


async def importing_main_interface():
    dir_list=get_epubs_to_import()
    logging.warning(f"Files to import: {dir_list}")
    matches=await compare_existing_with_import(dir_list, True) 
    #Second parameter dictates whether we receive a list of matching books
    #or a list of non-matching books, with matching being with existing books in the database.
    for fileName in dir_list:
        logging.warning(f"Processing file: {fileName}")
        logging.warning(await fetch_novel_data_from_epub(f"./books/imported/epubs/{fileName}"))
        bookID, bookTitle, bookAuthor, bookDescription, origin, lastScraped, latestChapterTitle=await fetch_novel_data_from_epub(f"./books/imported/epubs/{fileName}")
        
        await extract_chapter_from_book(f"./books/imported/epubs/{fileName}")
        
        first,last,total=get_first_last_chapter(bookTitle)
        
        directory = create_epub_directory_url(bookTitle)
        
        def get_prefix_from_origin(origin):
            """
            Returns the correct prefix for a given origin.
            """
            origin_prefix_map = {
                "royalroad.com": "rr",
                "scribblehub.com": "sb",
                "forums.spacebattles.com": "sb",
                "novelbin.me": "nb",
                "foxaholic.com": "fx",
                "Unknown": "un"
            }
            # Normalize origin to lower-case for matching
            return origin_prefix_map.get(str(origin).lower(), "un")
        prefix=get_prefix_from_origin(origin)
        
        
        def ensure_bookid_prefix(bookID, prefix):
            """
            Ensures the bookID starts with one of the valid prefixes ('rr', 'sb', 'fx').
            If not, prepends the given prefix.
            """
            valid_prefixes = ("rr", "sb", "fx","nb","un")
            if any(bookID.startswith(p) for p in valid_prefixes):
                return bookID
            return f"{prefix}{bookID}"
        
        bookID=ensure_bookid_prefix(bookID, prefix)
        
        def merge_book_entries(existing, new):
            """
            Merge two book records (dicts), preferring valid data from 'existing'.
            If 'existing' has an empty string, None, "N/A", or "Unknown", use the value from 'new'.
            """
            merged = {}
            invalid_values = ("", None, "N/A", "Unknown")
            for key in set(existing.keys()).union(new.keys()):
                old_val = existing.get(key, "")
                new_val = new.get(key, "")
                # Special handling for bookID
                if key == "bookID":
                # If old is 'un...' and new is not, use new
                    if str(old_val).startswith("un") and not str(new_val).startswith("un") and new_val:
                        merged[key] = new_val
                    else:
                        merged[key] = old_val if old_val not in invalid_values else new_val
                else:
                    merged[key] = old_val if old_val not in invalid_values else new_val
                # Use old value if it's not in invalid_values, otherwise use new value
                merged[key] = old_val if old_val not in invalid_values else new_val
            return merged

        existing_entry= get_Entry_Via_Title(bookTitle)
        
        new_entry = {
            "bookID": bookID,
            "bookName": bookTitle,
            "bookAuthor": bookAuthor,
            "bookDescription": bookDescription,
            "websiteHost": origin,
            "firstChapter": first,
            "lastChapterID": last,
            "lastChapterTitle": latestChapterTitle,
            "lastScraped": lastScraped,
            "totalChapters": total,
            "directory": directory
        }
        
        
        if existing_entry:
            merged_entry = merge_book_entries(existing_entry, new_entry)
        else:
            merged_entry = new_entry
        create_Entry(
            bookID=merged_entry["bookID"],
            bookName=merged_entry["bookName"],
            bookAuthor=merged_entry["bookAuthor"],
            bookDescription=merged_entry["bookDescription"],
            websiteHost=merged_entry["websiteHost"],
            firstChapter=merged_entry["firstChapter"],
            lastChapterID=merged_entry["lastChapterID"],
            lastChapterTitle=merged_entry["lastChapterTitle"],
            lastScraped=merged_entry["lastScraped"],
            totalChapters=merged_entry["totalChapters"],
            directory=merged_entry["directory"]
        )
        # if fileName.endswith('.epub'):
        #     dirLocation= f"./books/imported/epubs/{fileName}"
        #     logging.warning(f"Extracting from file: {fileName}")
        #     await extract_chapter_from_book(dirLocation)
        # else:
        #     logging.warning(f"Skipping non-epub file: {fileName}")


def is_image_duplicate(epub_image_bytes, directory):
    """
    Compare the given image bytes with all images in the directory.
    Returns True if a duplicate is found, False otherwise.
    """
    try:
        epub_img = Image.open(io.BytesIO(epub_image_bytes)).convert("RGB")
    except Exception as e:
        # If the image can't be opened, treat as new
        return False
    try:
        for file in os.listdir(directory):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                file_path = os.path.join(directory, file)
                try:
                    dir_img = Image.open(file_path).convert("RGB")
                    # Compare size first for speed
                    if epub_img.size != dir_img.size:
                        continue
                    diff = ImageChops.difference(epub_img, dir_img)
                    if not diff.getbbox():
                        return True  # Duplicate found
                except Exception:
                    continue
    except Exception as e:
        errorText=f"Failed to compare images in directory {directory}. Function is_image_duplicate Error: {e}"
        logging.error(errorText)
        write_to_logs(errorText)
        return False # No duplicate found

#asyncio.run(importing_main_interface())
#compare_images()
#asyncio.run(extract_chapter_from_book("./books/imported/epubs/DRR 4 - Paradoxical Ties - Silver Linings.epub"))



async def search_page(input: str, selectedSite: str, cookie):
    
    if selectedSite=="royalroad":
        scraper=RoyalRoadScraper()
        prefix="rr"
    elif selectedSite=="spacebattles":
        scraper=SpaceBattlesScraper()
        prefix="sb"
    elif selectedSite=="foxaholic":
        scraper=FoxaholicScraper()
        prefix="fx"
        if (cookie is None):
            errorText="Function search_page. Error: Cookie is required for Foxaholic. Please provide a cookie."
            logging.warning(errorText)
            write_to_logs(errorText)
            return None
    elif selectedSite=="novelbin":
        scraper=NovelBinScraper()
        prefix="nb"
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
        #If input is not a URL, treat it as a search query
        #default search query will be Royalroad
        scraper = RoyalRoadScraper()
        prefix = "rr"
        url=await scraper.query_royalroad(input.strip(), None)
        
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
        "chapterUrls": listofChapters
    }


async def search_page_scrape_interface(bookID, bookTitle, bookAuthor, selectedSite, cookie, book_chapter_urls):
    if selectedSite=="royalroad":
        epub_producer=RoyalRoadEpubProducer()
        prefix="rr"
    # elif selectedSite=="spacebattles":
    #     epub_producer=SpaceBattlesEpubProducer()
    #     prefix="sb"
    # elif selectedSite=="foxaholic":
    #     epub_producer=FoxaholicEpubProducer()
    #     prefix="fx"
    #     if (cookie is None):
    #         errorText="Function search_page_scrape_interface. Error: Cookie is required for Foxaholic. Please provide a cookie."
    #         logging.warning(errorText)
    #         write_to_logs(errorText)
    #         return None
    # elif selectedSite=="novelbin":
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
    

    dirLocation= await epub_producer.produce_custom_epub(new_epub,bookTitle,default_css,book_chapter_urls)
    logging.error(dirLocation)    
    return dirLocation
# scraper = SpaceBattlesScraper()
# url="https://forums.spacebattles.com/threads/the-new-normal-a-pok%C3%A9mon-elite-4-si.1076757/threadmarks?"
# result=asyncio.run(scraper.fetch_chapter_title_list(url))
# logging.warning("Results:")
# logging.warning(result)
#NOTE TO SELF. TEST THE NEW FETCH_CHAPTER_TITLE_LIST FUNCTIONS FOR EACH SITE