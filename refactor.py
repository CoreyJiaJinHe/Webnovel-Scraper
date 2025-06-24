

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
    get_all_book_titles
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
            latestChapterID=latestChapter.find("a")
            latestChapterID=latestChapterID.get_text()
            latestChapterID=remove_tags_from_title(latestChapterID)
            
            try:
                img_url = soup.find("div",{"class":"summary_image"}).find("img")
                if (img_url):
                    saveDirectory=f"./books/raw/{bookTitle}/"
                    if not (check_directory_exists(f"./books/raw/{bookTitle}/cover_image.png")):
                        await self.foxaholic_save_cover_image("cover_image",img_url,saveDirectory)
            except Exception as e:
                errorText=f"Failed to get cover image. There might be no cover. Or a different error. Function foxaholic_fetch_novel_data Error: {e}"
                write_to_logs(errorText)
                
                            
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
            latestChapterID=latestChapter.find("a")
            latestChapterID=latestChapterID.get_text()
            latestChapterID=remove_tags_from_title(latestChapterID)
            
            
            
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
            
        bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle= await scraper.fetch_novel_data(url)
        
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
        
        new_epub=instantiate_new_epub(bookID,bookTitle,bookAuthor)
        
        bookID=remove_invalid_characters(bookID)
        
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
    
#option takes two values 0 or 1. 0 for relevance. 1 for popularity.
async def query_royalroad(title, option):
    if (title.isspace() or title==""):
        return "Invalid Title"
        
    if (option ==0):
        querylink = f"https://www.royalroad.com/fictions/search?globalFilters=false&title={title}"
    elif (option==1):
        querylink = f"https://www.royalroad.com/fictions/search?globalFilters=false&title={title}&orderBy=popularity"
    else:
        return ("Invalid Option")

    soup=await RoyalRoadScraper.getSoup(querylink)
    resultTable=soup.find("div",{"class":"fiction-list"})
    bookTable=resultTable.find("h2",{"class":"fiction-title"})
    bookRows=bookTable.find_all("a")
    firstResult=bookRows[0]['href']
    #formatting
    resultLink=f"https://www.royalroad.com{firstResult}"
    return resultLink



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
    if not check_directory_exists(dirLocation):
        make_directory(dirLocation)

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
fileName="DRR 3 - Fragments of Time - Silver Linings.epub"
dirLocation= f"./books/imported/{fileName}"

def remove_tags_from_inside_brackets(text):
    """
    Removes all text inside brackets, including the brackets themselves.
    """
    return re.sub(r'[\[\(].*?[\]\)]', '', text)

async def fetch_novel_data_from_epub(fileName):
    
    try:
        dirLocation= f"./books/imported/epubs/{fileName}"
        #logging.warning(f"Importing from epub: {dirLocation}")
        book = epub.read_epub(dirLocation)
        #logging.warning(book)
        
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
        
        bookAuthor = book.get_metadata('DC', 'creator')
        if bookAuthor and isinstance(bookAuthor, list) and len(bookAuthor) > 0:
            bookAuthor = bookAuthor[0][0]
        else:
            bookAuthor = ""

            
        bookDescription = book.get_metadata('DC', 'description') if book.get_metadata('DC', 'description') else ""
        
        # for item in book.get_items():
        #     if item.get_type() == ebooklib.ITEM_DOCUMENT:
        #         print('==================================')
        #         print('NAME : ', item.get_name())
        #         print('----------------------------------')
        #         #print(item.get_content())
        #         #print('==================================')
                
        #         soup= bs4.BeautifulSoup(item.get_content(), 'html.parser')
                
        #         title =soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
        #         if title=="":
        #             title=soup.find('h2').get_text(strip=True) if soup.find('h2') else ""
        #         if title=="":
        #             title=soup.find('h3').get_text(strip=True) if soup.find('h3') else ""
        #         if title=="":
        #             continue

        #         chapterContent=soup
        #         logging.warning(f"Chapter Title: {title}")
                
        #         fileTitle= f"{bookTitle} - {remove_invalid_characters(title)}"
        #         logging.warning(f"File Title: {fileTitle}")
                
        #         store_chapter_version_two(chapterContent, bookTitle, fileTitle)
            
            #await save_page_content(soup, bookTitle, title)
                
        # Create directory for the book
        #make_directory(f"./books/raw/{bookTitle}")
        
        return bookTitle, bookAuthor, bookDescription
    except Exception as e:
        errorText=f"Failed to import from epub: {e}"
        logging.error(errorText)
        write_to_logs(errorText)
        return None, None, None



def get_files_inside_folder():
    dirLocation= "./books/imported/epubs"
    dir_list=os.listdir(dirLocation)
    print(f"Files in {dirLocation}:")
    print(dir_list)
    return dir_list

dir_list=get_files_inside_folder()


def compare_existing_with_import(dir_list):
    existingBookTitles=get_all_book_titles()
    matchingBooks=[]
    
    for item in dir_list:
        if item.endswith('.epub'):
            logging.warning(f"Extracting from file: {item}")
            bookTitle, bookAuthor, bookDescription = asyncio.run(fetch_novel_data_from_epub(item))
            if bookTitle:
                logging.warning(f"Read: {bookTitle} by {bookAuthor}")
            else:
                errorText=f"Failed to import from {item}"
                write_to_logs(errorText)
                logging.warning(errorText)
            bookMatch,bookScore=fuzzy_similarity(bookTitle, existingBookTitles)
            if (bookScore>=0.8):
                #logging.warning(f"Book {bookTitle} is similar to existing book {bookMatch} with score {bookScore}. Skipping.")
                matchingBooks.append(bookTitle)
                continue
    return matchingBooks
logging.warning(compare_existing_with_import(dir_list))
# logging.warning(asyncio.run(import_from_epub("Legendary Shadow Blacksmith Ch1-102.epub")))

    