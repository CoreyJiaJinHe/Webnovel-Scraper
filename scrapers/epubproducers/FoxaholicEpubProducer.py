import bs4
import re
import os
import logging
import asyncio
import io
from ebooklib import epub 
from PIL import Image
import aiohttp

import EpubProducer
from scrapers.FoxaholicScraper import FoxaholicScraper
from common import(
    store_chapter
)



class FoxaholicEpubProducer(EpubProducer):
    async def fetch_chapter_list(self, url):
        scraper = FoxaholicScraper()
        return await scraper.fetch_chapter_list(url)

    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count, new_epub):
        scraper = FoxaholicScraper()
        soup = await scraper.get_soup(chapter_url)
        chapter_title = await scraper.fetch_chapter_title(soup)
        chapter_content = scraper.foxaholic_scrape_chapter_page(soup)

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
        
        store_chapter(encoded_chapter_content.decode('utf-8'), book_title, chapter_title, chapter_id)

        return chapter_title, chapter_content, image_count
    
    #This grabs the first digit in the URL to treat as the ChapterID
    async def extract_chapter_ID(self, chapter_url):
        chapterID=chapter_url.split("/")
        chapterID=chapterID[len(chapterID)-2]
        chapterID=re.search(r'\d+',chapterID).group()
        return chapterID
    