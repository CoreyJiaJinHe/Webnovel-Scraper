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
from scrapers.RoyalRoadScraper import RoyalRoadScraper
from common import(
    store_chapter
)




class RoyalRoadEpubProducer(EpubProducer):
    async def fetch_chapter_list(self, url):
        scraper = RoyalRoadScraper()
        return await scraper.fetch_chapter_list(url)

    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count, new_epub):
        scraper = RoyalRoadScraper()
        soup = await scraper.get_soup(chapter_url)
        #logging.warning(soup)
        chapter_title = await scraper.fetch_chapter_title(soup)
        #logging.warning(chapter_title)
        chapter_content = await scraper.fetch_chapter_content(soup)
        # Save chapter content
        
        
        
        hyperlinks=chapterContent.find_all('a',{'class':'link'})
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
                chapterContent=bs4.BeautifulSoup(str(chapterContent),'html.parser')
        
        
        
        currentImageCount=image_count
        # Process images
        # TODO: This needs modifying. 
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

    #Extracts the chapter ID from the URL. Royalroad has unique IDs that increase with each chapter.
    async def extract_chapter_ID(self,chapter_url):
        return chapter_url.split("/")[-2]