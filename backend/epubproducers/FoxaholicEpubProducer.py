import bs4
import re
import os
import logging
import io
from ebooklib import epub 
from PIL import Image

from backend.epubproducers.EpubProducer import EpubProducer
from backend.scrapers.FoxaholicScraper import FoxaholicScraper
from backend.common import(
    write_to_logs, 
    check_directory_exists, 
    remove_tags_from_title, 
    retrieve_cover_from_storage, 
    storeEpub,
    remove_invalid_characters
)


class FoxaholicEpubProducer(EpubProducer):
    #This grabs the first digit in the URL to treat as the ChapterID
    def extract_chapter_ID(self, chapter_url):
        chapterID=chapter_url.split("/")
        chapterID=chapterID[len(chapterID)-2]
        chapterID=re.search(r'\d+',chapterID).group()
        return chapterID
    
    async def produce_custom_epub_interface(self, new_epub, book_title, css,book_chapter_urls, mainBookURL,additionalConditions, cookie):
        scraper=FoxaholicScraper(cookie=cookie)
        return await self.produce_custom_epub(new_epub, book_title, css, book_chapter_urls, mainBookURL, additionalConditions, scraper)
    
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