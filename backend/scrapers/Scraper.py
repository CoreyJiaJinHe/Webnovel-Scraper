import bs4
import aiohttp
from backend.common import write_to_logs
import os
import logging
import asyncio
import re

class Scraper:
    async def fetch_novel_data(self,url):
        raise NotImplementedError("Subclasses must implement this method.")
    async def fetch_chapter_list(self,url):
        raise NotImplementedError("Subclasses must implement this method.")
    async def fetch_chapter_content(self,soup):
        raise NotImplementedError("Subclasses must implement this method.")
    async def fetch_chapter_title(self,soup):
        raise NotImplementedError("Subclasses must implement this method.")
    
    async def fetch_cover_image(self, soup, bookTitle):
        raise NotImplementedError("Subclasses must implement this method.")

    async def process_new_book(self, book_url, book_title):
        raise NotImplementedError("Subclasses must implement this method.")

    async def process_new_chapter(self, chapter_url, book_title, chapter_id, image_count, new_epub):
        raise NotImplementedError("Subclasses must implement this method.")

    async def process_new_chapter_non_saved(self, chapter_url, book_title, chapter_id, image_count):
        raise NotImplementedError("Subclasses must implement this method.")
    
    async def query_site(self, title, additionalConditions, cookie):
        raise NotImplementedError("Subclasses must implement this method.")
    
    async def get_soup(self,url):
        try:
            async with aiohttp.ClientSession(headers = self.basicHeaders) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = bs4.BeautifulSoup(html, 'html.parser')
                        for script in soup(["script", "style"]):
                            script.decompose()    # rip it out
                        return soup
                    else:
                        errorText=f"Failed to get soup. Function get_soup Error: {response.status}"
                        write_to_logs(errorText)
        except Exception as e:
            errorText=f"Failed to get soup. Function get_soup Error: {e}, {url}"
            write_to_logs(errorText)
    
    def write_order_of_contents(self, book_title, chapter_metadata):
        file_location = f"./books/raw/{book_title}/order_of_chapters.txt"
        logging.warning(chapter_metadata)
        with open(file_location, "w") as f:
            for data in chapter_metadata:
                if isinstance(data, str):
                    data = data.strip().split(";")
                logging.warning(data)
                f.write(";".join(map(str, data))+ "\n")
                
    #These two function are from epubproducer. They are common.
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
            
    
    async def remove_junk_links_from_soup(self, chapter_content):
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
    

    def setCookie(self,cookie):
        self.basicHeaders["cookie"] = cookie

    basicHeaders={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
    }

    def interception (self, request):
        del request.headers['User-Agent']
        del request.headers['Accept']
        del request.headers['Accept-Language']
        del request.headers['Accept-Encoding']
        del request.headers['Cookie']

        request.headers['User-Agent']=self.basicHeaders["User-Agent"]
        request.headers['Accept']=self.basicHeaders["Accept"]
        request.headers['Accept-Language']=self.basicHeaders["Accept-Language"]
        request.headers['Accept-Encoding']=self.basicHeaders["Accept-Encoding"]
        request.headers['Cookie']=self.basicHeaders["cookie"]
        
        
        
    async def check_and_insert_missing_chapter_title(self, chapter_title, chapter_content):
    # Check if chapter_title is present as a heading (h1/h2/h3) in chapter_content
        logging.warning(f"chapter_content type: {type(chapter_content)}")
        if chapter_content is None:
            errorText = "chapter_content is None in check_and_insert_missing_chapter_title"
            write_to_logs(errorText)
            return
        try:
            heading_found = False
            for heading_tag in ['h1', 'h2', 'h3']:
                heading = chapter_content.find(heading_tag)
                if heading and chapter_title.strip() in (heading.get_text() or "").strip():
                    heading_found = True
                    break
            logging.warning(f"Heading found: {heading_found}")
            if not heading_found:
                # Try to create a new heading tag
                soup = getattr(chapter_content, 'soup', None)
                if soup is None:
                    soup = chapter_content if isinstance(chapter_content, bs4.BeautifulSoup) else bs4.BeautifulSoup(str(chapter_content), 'html.parser')
                new_heading = soup.new_tag("h1")
                new_heading.string = chapter_title
                logging.warning("Attempting to insert new heading at the top of chapter_content")
                # Insert at the top if possible, else append
                if hasattr(chapter_content, "insert"):
                    chapter_content.insert(0, new_heading)
                else:
                    chapter_content.append(new_heading)
                logging.warning("Heading inserted successfully.")
                #logging.warning(chapter_content.prettify())
        except Exception as e:
            errorText = f"Failed to check and insert missing chapter title. Function Scraper check_and_insert_missing_chapter_title Error: {e}"
            write_to_logs(errorText)
        return chapter_content