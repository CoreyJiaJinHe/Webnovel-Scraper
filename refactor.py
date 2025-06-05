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
    create_epub_directory_url
)


from mongodb import(
    check_existing_book,
    check_existing_book_Title,
    check_latest_chapter,
    check_recently_scraped,
    create_Entry, 
    create_latest
)

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
                logging.warning(data)
                f.write(";".join(map(str, data))+ "\n")

























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
    






async def main_interface(url, cookie):
    try:
        if (cookie):
            setCookie(cookie)
        epub_producer = None
        if "royalroad.com" in url:
            epub_producer = RoyalRoadEpubProducer()
            logging.warning('Creating scraper')
            scraper=RoyalRoadScraper()
        elif "spacebattles.com" in url:
            epub_producer=SpaceBattlesEpubProducer()
            logging.warning('Creating scraper')
            scraper=SpaceBattlesScraper()
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
        
        
        if "royalroad.com" in url:
            bookID=f"rr{bookID}"
        elif "spacebattles.com" in url:
            bookID=f"sb{bookID}"
        
        #TODO: DONE If the book already exists, we should check if the latest chapter is the same as the one in the database.
        #To do this, I need to change the way latest chapters are stored in the database. I need to store the latest chapter's name and ID
        #and make the name be the one that is displayed on the front end, while using the ID to compare latest chapters
        if (check_existing_book(bookID) or check_existing_book_Title(bookTitle)):
            logging.warning(f"Book {bookTitle} already exists in the database with ID {bookID}. Checking for new chapters.")
            if not (check_recently_scraped(bookID)):
                logging.warning(f"Book {bookTitle} has not been scraped recently. Processing new book.")
                if not (check_latest_chapter(bookID,bookTitle,latestChapterTitle)):
                    logging.warning(f"Latest chapter {latestChapterTitle} is not the same as the one in the database. Processing new book.")
                    await scraper.process_new_book(url, bookTitle)
                else:
                    logging.warning(f"Book {bookTitle} already exists in the database with the latest chapter {latestChapterTitle}. No new chapters to scrape.")
        
        #TODO: DONE I also need to modify SpacebattlesEpubProducer. Currently, the latest chapter is considered the last page of spacebattles reader mode.
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
logging.warning(asyncio.run (main_interface("https://forums.spacebattles.com/threads/quahinium-industries-shipworks-kancolle-si.1103320/reader/", None)))