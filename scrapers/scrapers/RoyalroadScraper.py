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

import Scraper
    
    
class RoyalRoadScraper(Scraper):
    async def get_soup(self,url):
        return await Scraper.get_soup(url)
    async def remove_junk_links_from_soup(self, soup):
        return await Scraper.remove_junk_links_from_soup(soup)
    
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
                
                
                
                try:
                    self.fetch_cover_image(soup, bookTitle)
                
                except Exception as e:
                    errorText=f"Failed to get cover image for Royalroad. Function fetch_cover_image Error: {e}"
                    write_to_logs(errorText)
                return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle,latestChapterID
            except Exception as e:
                errorText=f"Failed to get novel data. Function royalroad_fetch_novel_data Error: {e}"
                write_to_logs(errorText)
        else:
            errorText=f"Failed to get soup for processing. Function RoyalRoad_Fetch_Novel_Data Error: No soup"
            write_to_logs(errorText)
            return None
    
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
        except Exception as error:
            errorText=f"Failed to get image for processing. Function RoyalRoad_save_cover_image Error: {error}"
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
      
    
    
    #TODO: Working on creating a new function to generate an epub with the selected chapters without actually storing them into the repository.
    async def process_new_chapter_non_saved(self, chapter_url, book_title,chapter_id,image_count):
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
        
    

    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count):
        soup = await self.get_soup(chapter_url)
        chapter_title = await self.fetch_chapter_title(soup)
        chapter_content = await self.fetch_chapter_content(soup)
        chapter_content = await self.remove_junk_links_from_soup(chapter_content)
        
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
    
    
            
    #Extracts the chapter ID from the URL. Royalroad has unique IDs that increase with each chapter.
    async def extract_chapter_ID(self,chapter_url):
        return chapter_url.split("/")[-2]
        


    
    