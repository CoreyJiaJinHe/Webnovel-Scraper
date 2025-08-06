import bs4
import re
import os
import logging
import asyncio
import io
from ebooklib import epub 
from PIL import Image
import aiohttp

# Use absolute imports for clarity and reliability
from backend.epubproducers.EpubProducer import EpubProducer
from backend.scrapers.RoyalRoadScraper import RoyalRoadScraper
from backend.common import (
    store_chapter,
    write_to_logs, 
    check_directory_exists,
    store_chapter, 
    retrieve_cover_from_storage, 
    remove_invalid_characters,
)

class RoyalRoadEpubProducer(EpubProducer):
    #Unique ChapterID extraction for RoyalRoad
    def extract_chapter_ID(self, chapter_url):
        return chapter_url.split(";")[0]

    async def produce_epub(self, book_title, css, new_epub):
        return await EpubProducer.produce_epub(self, book_title, css, new_epub)
    
    async def produce_custom_epub_interface(self, new_epub, book_title, css,book_chapter_urls, mainBookURL,additionalConditions, cookie):
        scraper=RoyalRoadScraper()
        return await self.produce_custom_epub(new_epub, book_title, css, book_chapter_urls, mainBookURL, additionalConditions, scraper)

    async def produce_custom_epub(self, new_epub, book_title, css,book_chapter_urls, mainBookURL,additionalConditions, scraper):
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
                        #No need to update the image sources in the soup. It has already been done as part of process_new_chapter_non_saved.
                
                # logging.warning(chapter_title)
                # logging.warning(file_chapter_title)
                
                #This function is ~~not~~ working for some odd reason. It is working now
                chapter = self.create_epub_chapter(chapter_title, file_chapter_title, chapter_content_soup, css)
                # logging.error("This should be a chapter object below this line.")
                # logging.error(chapter)
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


