import bs4
import re
import os
import logging
import asyncio
import io
from ebooklib import epub 
from PIL import Image
import aiohttp

from common import(
    write_to_logs,
    remove_invalid_characters,
    retrieve_cover_from_storage,
    storeEpub,
    basicHeaders
)



class EpubProducer:
    async def fetch_chapter_list(self, url):
        raise NotImplementedError("Subclasses must implement this method.")

    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count, new_epub):
        raise NotImplementedError("Subclasses must implement this method.")

    async def extract_chapter_ID(self,chapter_url):
        raise NotImplementedError("Subclasses must implement this method.")
    
    async def retrieve_images_in_chapter(self,images_url,image_dir,image_count,new_epub):
        current_image_count=image_count
        try:
            for img_url in images_url:
                image_path=f"{image_dir}/{img_url}"
                epubImage=Image.open(image_path)
                if (epubImage):
                    b=io.BytesIO()
                    epubImage.save(b,'png')
                    b_image1=b.getvalue()
                    
                    image_item=epub.EpubItem(uid=f'image_{current_image_count}',file_name=f'images/image_{current_image_count}.png', media_type='image/png', content=b_image1)
                    new_epub.add_item(image_item)
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
            if not isinstance(chapter_content, str):
                chapter_content = str(chapter_content)
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

    def finalize_epub(self, new_epub, toc_list, book_title, chapter_metadata):
        self.write_order_of_contents(book_title, chapter_metadata)
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

    #This is a common function that can be used by all EpubProducer classes, unless it is Spacebattles. In that case, it will be overridden.
    async def produce_epub(self, url, book_title, css, new_epub):
        already_saved_chapters = self.get_existing_order_of_contents(book_title)
        chapter_list = await self.fetch_chapter_list(url)
        chapter_metadata = []
        toc_list = []
        image_count = 0
        logging.warning(chapter_list)
        for chapter_url in chapter_list:
            logging.warning(chapter_url)
            chapter_id = await self.extract_chapter_ID(chapter_url)
            if self.check_if_chapter_exists(chapter_id, already_saved_chapters):
                chapter_id, dir_location = self.get_chapter_from_saved(chapter_id, already_saved_chapters)
                chapter_content = self.get_chapter_contents_from_saved(dir_location)
                chapter_title = self.extract_chapter_title(dir_location)
                chapter_content_soup=bs4.BeautifulSoup(chapter_content,'html.parser')
                # Extract images from the chapter content
                images=chapter_content_soup.find_all('img')
                images=[image['src'] for image in images]
                image_dir = f"./books/raw/{book_title}/"
                if images:
                    image_count=await self.retrieve_images_in_chapter(images, image_dir,image_count,new_epub)
            else:
                chapter_title, chapter_content, image_count = await self.process_new_chapter(
                    chapter_url, book_title, chapter_id, image_count, new_epub
                )
                
            file_chapter_title = f"{book_title} - {chapter_id} - {remove_invalid_characters(chapter_title)}"
            chapter_metadata.append([chapter_id, chapter_url, f"./books/raw/{book_title}/{file_chapter_title}.html"])
            
            chapter = self.create_epub_chapter(chapter_title, file_chapter_title, chapter_content, css)
            toc_list.append(chapter)
            new_epub.add_item(chapter)

        self.add_cover_image(book_title, new_epub)
        self.finalize_epub(new_epub, toc_list, book_title, chapter_metadata)

    async def save_images_in_chapter(self, img_urls, save_directory, image_count, new_epub):
        if not os.path.exists(save_directory):
            os.makedirs(save_directory)
        #logging.warning(img_urls)
        try:
            for img_url in img_urls:
                if ("emoji" in img_url):
                    continue
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
                await asyncio.sleep(0.5)
            return image_count
        except Exception as e:
            errorText=f"Failed to get save image. Function save_images_in_chapter Error: {e}"
            write_to_logs(errorText)
            
    async def produce_custom_epub(self, new_epub, book_title, css,book_chapter_urls, mainBookURL,additionalConditions):
        raise NotImplementedError("Subclasses must implement this method.")
            