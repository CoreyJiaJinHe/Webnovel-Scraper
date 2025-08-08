import bs4
import re
import os
import logging
import asyncio
import io
from ebooklib import epub 
from PIL import Image
import aiohttp


from backend.epubproducers.EpubProducer import EpubProducer
from backend.scrapers.NovelBinScraper import NovelBinScraper
from backend.common import(
    store_chapter,
    write_to_logs, 
    check_directory_exists,
    store_chapter, 
    retrieve_cover_from_storage,
    remove_invalid_characters,
)


class NovelBinEpubProducer(EpubProducer):
    #this might become a common function
    #Nevermind. This one is different. It's not extracting the ID from the URL but frm the internal storage.
    def extract_chapter_ID(self, chapter_url):
        return chapter_url.split(";")[0]

    
    async def fetch_chapter_list(self, url):
        scraper = NovelBinScraper().setCookie(self.basicHeaders.get("cookie", ""))
        return await scraper.fetch_chapter_list(url)
    
    async def generate_chapter_title(self, chapter_id):
        chapter_id=int(chapter_id)
        
        volume_number=int(chapter_id//10000)
        chapter_number=int(chapter_id%10000)
        
        return f"V{volume_number}Ch{chapter_number}"
    
    
    async def produce_custom_epub_interface(self, new_epub, book_title, css,book_chapter_urls, mainBookURL,additionalConditions, cookie):
        scraper=NovelBinScraper()
        scraper.setCookie(self.basicHeaders.get("cookie", ""))
        logging.warning(type(scraper))
        logging.warning(f"Cookie set: {scraper.basicHeaders.get('cookie', '')}")
        return await self.produce_custom_epub(
            new_epub, book_title, css, book_chapter_urls, mainBookURL, additionalConditions, scraper)

    async def produce_custom_epub(self, new_epub, book_title, css, book_chapter_urls, mainBookURL, additionalConditions, scraper):
        if not book_chapter_urls:
            errorText="Function produce_custom_epub. Error: No chapters provided for the custom epub."
            logging.warning(errorText)
            write_to_logs(errorText)
            return
        
        toc_list=[]
        image_counter=0
        current_image_counter=0

        try:
            for chapter_url in book_chapter_urls:
                logging.error (chapter_url)
                soup=await scraper.get_soup(chapter_url)
                
                chapter_id= await scraper.extract_chapter_ID(chapter_url)
                chapter_title=await scraper.fetch_chapter_title(soup)
                chapter_title = remove_invalid_characters(chapter_title)

                file_chapter_title, image_counter, chapter_content = await scraper.process_new_chapter_non_saved(chapter_url, book_title, chapter_id, image_counter)
                chapter_content_soup=bs4.BeautifulSoup(str(chapter_content),'html.parser')
                await self.check_and_insert_missing_chapter_title(chapter_title, chapter_content_soup)
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
                
    