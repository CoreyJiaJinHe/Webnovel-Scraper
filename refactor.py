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

logLocation=os.getenv("logs")


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
    






import bs4
import re
import os
import logging
import asyncio
import io
from ebooklib import epub 
from PIL import Image
import aiohttp

#from scrapers.epubproducers import EpubProducer


from scrapers.common import write_to_logs, check_directory_exists, make_directory, remove_invalid_characters, remove_tags_from_title, store_chapter, retrieve_cover_from_storage, storeEpub, basicHeaders

#from Scraper import Scraper
    
    
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
                
                bookTitle=remove_invalid_characters(bookTitle)
                        
                description=soup.find("div",{"class":"description"}).get_text()
                if ("\n" in description):
                    description=description.replace("\n","")
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
                return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle
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
        
        #self.write_order_of_contents(book_title,chapter_metadata)
        
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
    
    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count):
        soup = await self.get_soup(chapter_url)
        chapter_title = await self.fetch_chapter_title(soup)
        chapter_content = await self.fetch_chapter_content(soup)
        chapter_content = await self.remove_junk_links(chapter_content)
        
        currentImageCount=image_count
        # Process images
        # TODO: This needs modifying. 
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
                logging.warning(data)
                f.write(";".join(str(data))+ "\n")

    
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

#from scrapers.epubproducers.EpubProducer import EpubProducer


class RoyalRoadEpubProducer():
    
    #TODO: This needs modifying
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
                logging.warning(data)
                f.write(";".join(str(data))+ "\n")

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
        self.add_cover_image(book_title, new_epub)
        logging.warning("Finalizing epub")
        self.finalize_epub(new_epub, toc_list, book_title)

    async def retrieve_images_for_chapter(self, img_urls, save_directory, image_count, new_epub):
        try:
            for img_url in img_urls:
                image_path = f"{save_directory}image_{image_count}.png"
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
            return image_count
        except Exception as e:
            errorText=f"Failed to get save image. Function save_images_in_chapter Error: {e}"
            write_to_logs(errorText)





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

# Add these missing imports:
from scrapers.common import (
    setCookie,
    get_first_last_chapter,
    remove_invalid_characters,
    create_epub_directory_url
)


from mongodb import(
    check_existing_book,
    check_existing_book_Title,
    check_latest_chapter,
    check_recently_scraped
)


from mongodb import create_Entry, create_latest

async def main_interface(url, cookie):
    try:
        if (cookie):
            setCookie(cookie)
        epub_producer = None
        if "royalroad.com" in url:
            epub_producer = RoyalRoadEpubProducer()
        else:
            raise ValueError("Unsupported website")
        logging.warning(url)
        logging.warning('Creating scraper')
        scraper=RoyalRoadScraper()
        logging.warning('Fetching novel data')
        bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle= await scraper.fetch_novel_data(url)
        
        
        
        new_epub=epub.EpubBook()
        new_epub.set_identifier(bookID)
        new_epub.set_title(bookTitle)
        new_epub.set_language('en')
        new_epub.add_author(bookAuthor)
        style=open("style.css","r").read()
        default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)
        new_epub.add_item(default_css)
        
        bookID=remove_invalid_characters(bookID)
        bookID=f"rr{bookID}"
        
        #TODO: DONE If the book already exists, we should check if the latest chapter is the same as the one in the database.
        #To do this, I need to change the way latest chapters are stored in the database. I need to store the latest chapter's name and ID
        #and make the name be the one that is displayed on the front end, while using the ID to compare latest chapters
        if (check_existing_book(bookID) or check_existing_book_Title(bookTitle)):
            if not (check_recently_scraped(bookID)):
                if not (check_latest_chapter(bookID,bookTitle,latestChapterTitle)):
                    await scraper.process_new_book(url, bookTitle)
                else:
                    logging.warning(f"Book {bookTitle} already exists in the database with the latest chapter {latestChapterTitle}. No new chapters to scrape.")
            
        #TODO: I also need to modify SpacebattlesEpubProducer. Currently, the latest chapter is considered the last page of spacebattles reader mode.
        #Due to how spacebattles works, it does not check for new chapters added to the page. Meaning, I can store 5 threadmarks on last page, and the sixth won't be detected.
        #TODO: I also need to modify all the EpubProducers to handle broken images so that it won't break the epub generation.
        
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
        
        return directory
    
    
    except ValueError as e:
        logging.error(f"Error: {e}")
x=RoyalRoadScraper()
#logging.warning(asyncio.run (x.RoyalRoad_Fetch_Novel_Data("https://www.royalroad.com/fiction/100326/into-the-unown-pokemon-fanfiction-oc")))
logging.warning(asyncio.run (main_interface("https://www.royalroad.com/fiction/54046/final-core-a-holy-dungeon-core-litrpg", None)))