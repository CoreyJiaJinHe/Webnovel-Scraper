import bs4
import re
import logging

import EpubProducer
from scrapers.NovelBinScraper import NovelBinScraper
from common import(
    store_chapter
)



class NovelBinEpubProducer(EpubProducer):
    async def fetch_chapter_list(self, url):
        scraper = NovelBinScraper()
        return await scraper.fetch_chapter_list(url)
    
    async def generate_chapter_title(self, chapter_id):
        chapter_id=int(chapter_id)
        
        volume_number=int(chapter_id//10000)
        chapter_number=int(chapter_id%10000)
        
        return f"V{volume_number}Ch{chapter_number}"
        
    
    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count, new_epub):
        scraper = NovelBinScraper()
        soup = await scraper.get_soup(chapter_url)
        chapter_title = await scraper.fetch_chapter_title(soup)
        chapter_title=await self.generate_chapter_title(chapter_id)+" "+chapter_title
        
        chapter_content = scraper.novelbin_scrape_chapter_page(soup)
        chapterInsert=f'<h1>{chapter_title}</h1>'
        chapter_content=chapterInsert+str(chapter_content)
        chapter_content=bs4.BeautifulSoup(chapter_content,'html.parser')
        # Save chapter content
        currentImageCount=image_count
        # Process images
        images=chapter_content.find_all('img')
        images=[image['src'] for image in images]
        logging.warning(images)
        image_dir = f"./books/raw/{book_title}/images/"
        if images:
            image_count = await self.save_images_in_chapter(images, image_dir, image_count, new_epub)
            for img,image in zip(chapter_content.find_all('img'),images):
                img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")       
                currentImageCount+=1
        
        encoded_chapter_content=chapter_content.encode('ascii')
        store_chapter(encoded_chapter_content, book_title, chapter_title, chapter_id)

        return chapter_title, chapter_content, image_count
    
    
    
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