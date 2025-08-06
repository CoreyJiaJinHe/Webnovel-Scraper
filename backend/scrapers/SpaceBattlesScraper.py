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


from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from seleniumwire import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
logging.getLogger('seleniumwire').setLevel(logging.WARNING)

firefox_options = FirefoxOptions()

# Path to .xpi extension file
path_to_extension = os.getenv("LOCAL_ADBLOCK_EXTENSION")

from word2number import w2n


from backend.scrapers.Scraper import Scraper
from backend.common import(
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




class SpaceBattlesScraper(Scraper):

    def normalize_spacebattles_url(self, url: str) -> str:
        """Find the last occurrence of digits/ and trim everything after"""
        match = re.search(r'(\d+/)', url)
        if match:
            idx = url.find(match.group(1)) + len(match.group(1))
            url = url[:idx]
        # Ensure it ends with threadmarks?per_page=200
        if not url.endswith('threadmarks?per_page=200'):
            url += 'threadmarks?per_page=200'
        return url
    
    def threadmarks_to_reader(self, url: str) -> str:
        """
        Replace 'threadmarks?per_page=200' at the end of a SpaceBattles thread URL with 'reader/'.
        """
        if url.endswith('threadmarks?per_page=200'):
            url = url[: -len('threadmarks?per_page=200')]
            if not url.endswith('/'):
                url += '/'
            url += 'reader/'
        return url
    
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
                logging.warning(rows)
                latestChapter=rows[len(rows)-1]
                latestChapterTitle=latestChapter.get_text()
                logging.warning(latestChapterTitle)
                
                
                match = re.search(
                    r'\b(\d+(?:-\d+)?|one|two|three|four|five|six|seven|eight|nine|ten|'
                    r'eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|'
                    r'thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand)\b',
                    latestChapterTitle,
                    re.IGNORECASE
                )
                latestChapterID = None
                if match:
                    value = match.group(1).lower()
                    try:
                        # Try to convert directly to int (for digit matches)
                        latestChapterID = int(value)
                    except ValueError:
                        try:
                            # If not a digit, convert written number to int
                            latestChapterID = w2n.word_to_num(value)
                        except Exception:
                            latestChapterID = value  # fallback: keep as string if conversion fails
                    
            
                try:
                    self.fetch_cover_image(soup, bookTitle)
                except Exception as e:
                    errorText=f"Failed to get cover image. There might be no cover. Or a different error. Function fetch_novel_data Error: {e}"
                    write_to_logs(errorText)
                #logging.warning(bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterID)
                return bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle,latestChapterID
            except Exception as e:
                errorText=f"Failed to get novel data. Function Spacebattles fetch_novel_data Error: {e}"
                write_to_logs(errorText)
                
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
            errorText=f"Failed to get cover image. Function fetch_cover_image Error: {e}"
            write_to_logs(errorText)
    #This doesn't actually return chapters. It just returns the pages.
    #Page numbers are to generated under the assumption that each page can hold 10 threadmarks.
    async def fetch_chapter_list(self,url):
        url=self.normalize_spacebattles_url(url)
        
        url = self.threadmarks_to_reader(url)
        logging.warning(url)
        
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
    
    #While this returns the threadmark titles.
    async def fetch_chapter_title_list(self, url):
        url=self.normalize_spacebattles_url(url)
        
        soup=await self.get_soup(url)
        logging.warning(url)
        try:
            #logging.warning(soup)
            chapterListTitles=list()
            pageNav=soup.find("div",{"class":"pageNav"})
            logging.warning(pageNav)
            if not pageNav:
                threadmarkBody=soup.find("div",{"class":"structItemContainer"})
                #logging.warning(threadmarkBody)
                rows= threadmarkBody.find_all("ul",{"class":"listInline listInline--bullet"})
                for row in rows[:len(rows)]:
                    #logging.warning(row)
                    
                    threadmarkItem = row.find("a")
                    if threadmarkItem is not None:
                        #logging.warning(threadmarkItem)
                        chapterTitle = threadmarkItem.get_text()
                        chapterTitle = remove_invalid_characters(chapterTitle)
                        #logging.warning(f"Title:{chapterTitle}")
                        chapterListTitles.append(chapterTitle)
                    else:
                        logging.warning("No <a> tag found in row!")
            else:
                pageNavMain=pageNav.find("ul",{"class":"pageNav-main"})
                pages = pageNavMain.find_all("li")
                #logging.warning(pageNav)
                for page in range(1,len(pages)+1):
                    url=f"{url}&page={page}/"
                    logging.warning(page)
                    soup=await self.get_soup(url)
                    
                    threadmarkBody=soup.find("div",{"class":"structItemContainer"})

                    rows= threadmarkBody.find_all("ul",{"class":"listInline listInline--bullet"})
                    for row in rows[:len(rows)]:
                        #logging.warning(row)
                        
                        threadmarkItem = row.find("a")
                        if threadmarkItem is not None:
                            #logging.warning(threadmarkItem)
                            chapterTitle = threadmarkItem.get_text()
                            chapterTitle = remove_invalid_characters(chapterTitle)
                            #logging.warning(f"Title:{chapterTitle}")
                            chapterListTitles.append(chapterTitle)
                        else:
                            logging.warning("No <a> tag found in row!")
                
            return chapterListTitles
        except Exception as error:
            errorText=f"Failed to get chapter titles from chapter list of page. Function Spacebattles_get_chapter_title_list Error: {error}"
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
                    chapter_content = await self.remove_junk_links_from_soup(chapter_content)
                    
                    
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

    async def query_site(self,title:str,additionalConditions: dict, cookie):
        isSearchSearch = additionalConditions.get("true_search", False)
        sortby= additionalConditions.get("order", None)
        
        def normalize_title(title: str) -> str:
            """Convert spaces in a title to underscores."""
            title = title.lower()
            return title.replace(" ", "+")
        title = normalize_title(title)
        if (isSearchSearch): #This will decide what sort of search.
            #the first search is a search of the forums, the second is a filter of the forums
            return await self.query_spacebattles_search_version(title,sortby, additionalConditions)
        else:
            return await self.query_spacebattles_filter_version(title,sortby,additionalConditions)
    
    #https://forums.spacebattles.com/search/104090354/?q=New+Normal&t=post&c[child_nodes]=1&c[nodes][0]=18&c[title_only]=1&o=date 
    #Basic format of search query
    #https://forums.spacebattles.com/search/104090768/?q=Cheese
    #& between each condition
    #c[title_only]
    #c[users]="Name"
    #o=date, or, o=word_count, or, o=relevance
    #This is for order
    
    #This function only takes certain parameters.
    #c[title_only]=1 or 0.
    #c[users]="Name"
    #o=date/word_count/relevance
    async def query_spacebattles_search_version(self,title: str, sortby: str, additionalConditions: dict):
        try:
            if (title.isspace() or title==""):
                errorText=f"Failed to search title. Function query_spacebattles_search_version Error: No title inputted"
                write_to_logs(errorText)
                return "Invalid Title"
            #&t=post&c[child_nodes]=1&c[nodes][0]=18 is for forum: Creative Writing
            #&c[title_only]=1 is for title only search
            querylink = f"https://forums.spacebattles.com/search/104090354/?q={title}&t=post&c[child_nodes]=1&c[nodes][0]=18"
            for item in additionalConditions:
                querylink+=f"&{item}={additionalConditions[item]}"
                logging.warning(querylink)
            if (sortby not in ["relevance","date",  "last_update", "replies", "word_count"]):
                errorText=f"Invalid sort-by condition. Continuing on with default. Function query_spacebattles_search_version Error: {sortby}"
                write_to_logs(errorText)
                sortby = "date"  # Default sort-by option
            querylink+=f"&o={sortby}"
            logging.warning(querylink)
            
            async def get_soup(url):
                try:
                    driver = webdriver.Firefox(options=firefox_options)
                    driver.install_addon(path_to_extension, temporary=True)
                    driver.request_interceptor=interception
                    driver.get(url)
                    WebDriverWait(driver, 10).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                    await asyncio.sleep(2) #Sleep is necessary because of the javascript loading elements on page
                    soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
                    driver.close()
                    return soup
                except Exception as error:
                    errorText=f"Failed to get soup from url. Function spacebattles_get_soup Error: {error}"
                    write_to_logs(errorText)
            
            #Needs to be selenium because the 'search url' result is dynamically generated...
            #Basically... Spacebattles generates the result and then sends its as a webpage. Instead of a static page hosting the results.
            #https://forums.spacebattles.com/search/104096825/?q=Trails+Of&t=post&c[child_nodes]=1&c[nodes][0]=18&c[title_only]=1&o=date
            #But everything after those numbers is just for you to see. The numbers are the actual search results.
            #for some god forsaken reason, spacebattles indexes the search results. 
            #If you want to search, you have to use their form and button. Which I can't do since I am using url-based search
            soup=await get_soup(querylink)
            try:
                resultTable=soup.find("div",{"class":"block-container"})
                bookTable=resultTable.find("ol",{"class":"block-body"})
                bookRows=bookTable.find_all("h3", {"class":"contentRow-title"})
                bookLinks=bookRows[0].find("a")['href']
                firstResult=bookLinks
                #formatting
                resultLink = f"https://forums.spacebattles.com{firstResult}"
                resultLink = re.sub(r'(#|\?).*$', '', resultLink)
                return resultLink
            except Exception as error:
                errorText=f"Search failed. Most likely reason: There wasn't any search results. Function query_royalroad Error: {error}"
                write_to_logs(errorText)
        except Exception as e:
            errorText=f"Improper query attempt. Function query_spacebattles Error: Invalid query option. {e}"
            write_to_logs(errorText)
            return ("Invalid Option")
    
    #this one uses a different search system. It's not really a search but rather a filter.
    #Search via main tag, and get the results. It's more dependent on the additional filter conditions to do the search.
    #The additional filter conditions are:
    #sortby: title, reply_count, view_count, last_threadmark, watchers
    #direction: asc, desc
    #&threadmark_index_statuses[0]=incomplete
    #&threadmark_index_statuses[1]=complete
    #&threadmark_index_statuses[2]=hiatus
    #min_word_count=0
    #max_word_count=10000000
    async def query_spacebattles_filter_version(self,title: str, sortby: str, additionalConditions: dict):
        try:
            if (title.isspace() or title==""):
                errorText=f"Failed to search title. Function query_spacebattles Error: No title inputted"
                write_to_logs(errorText)
                return "Invalid Title"
            
            direction = additionalConditions.get("direction", "desc")
            if direction not in ["asc", "desc"]:
                errorText=f"Invalid direction condition. Continuing on with default. Function query_spacebattles_filter_version Error: {direction}"
                write_to_logs(errorText)
                direction = "desc"
            
            querylink = f"https://forums.spacebattles.com/forums/creative-writing.18/?tags[0]={title}"
            if (sortby not in ["title", "reply_count", "view_count", "last_threadmark", "watchers"] and direction not in ["asc", "desc"]):
                errorText=f"Invalid sort-by condition. Continuing on with default. Function query_spacebattles_filter_version Error: {sortby}"
                write_to_logs(errorText)
                sortby = "last_threadmark"  # Default sort-by option
                querylink+=f"&order={sortby}&direction=desc"
            else:
                querylink+=f"&order={sortby}&direction={direction}"
            for item in additionalConditions:
                querylink+=f"&{item}={additionalConditions[item]}"
                logging.warning(querylink)
            logging.warning(querylink)
            querylink+="&nodes[0]=48&nodes[1]=169&nodes[2]=40&nodes[3]=115"
            
            
            
            soup=await self.get_soup(querylink)
            try:
                resultTable=soup.find("div",{"class":"structItemContainer"})
                bookTable=resultTable.find("div",{"class":"js-threadList"})
                bookRows=bookTable.find_all("div", {"class":"structItem"})
                #logging.warning(bookRows)
                firstResult=bookRows[0].find("div", {"class":"structItem-title"})
                logging.warning("=================")
                logging.warning(firstResult.get_text())
                
                if (firstResult):
                    links=firstResult.find_all("a")
                    if (links):
                        logging.warning(links)
                        for link in links:
                            if link.get_text(strip=True) == "Jump to New":
                                continue
                            # If we find a link that is not "Jump to New", we take it
                            firstResultLink=link['href']
                            break
                        #formatting
                        resultLink=f"https://forums.spacebattles.com/{firstResultLink}"
                        return resultLink
                return "No Results Found"
            except Exception as e:
                errorText=f"Search failed. Most likely reason: There wasn't any search results. Function query_spacebattles_filter_version Error: {e}"
                write_to_logs(errorText)
                return "No Results Found"
        except Exception as e:
            errorText=f"Improper query attempt. Function query_spacebattles_filter_version Error: {e} How did you even do this?"
            write_to_logs(errorText)
            return "Invalid Option"
        #These need to be added at the end to specify the forums.
        #THEY MUST BE at the end of the query.

    
    #TODO: Working on creating a new function to generate an epub with the selected chapters without actually storing them into the repository.
    async def process_new_chapter_non_saved(self, soup, book_title,chapter_id,image_count, exclude_images):
        try:
            soup = soup
            chapter_title = await self.fetch_chapter_title(soup)
            chapter_content= soup.find("div", {"class": "message-userContent"})
            if not chapter_content:
                errorText=f"Failed to find chapter content. Function process_new_chapter_non_saved Error: No content found for page {chapter_id} in book {book_title}."
                write_to_logs(errorText)
                return None, image_count, None
            chapter_content = await self.spacebattles_remove_garbage_from_chapter(chapter_content)
            chapter_content = await self.remove_junk_links_from_soup(chapter_content)
            if not chapter_content:
                errorText=f"Failed to clean chapter content. Function process_new_chapter_non_saved Error: No valid content found for page {chapter_id} in book {book_title}."
                write_to_logs(errorText)
                return None, image_count, None
            
            currentImageCount=image_count
            # Process images
            if exclude_images:
                for img in chapter_content.find_all('img'):
                    img.decompose()
            else:
                images=[]
                seen = set()
                for image in chapter_content.find_all('img'):
                    # Prefer a valid http(s) URL from data-src or src
                    img_url = None
                    for attr in ['data-src', 'src']:
                        candidate = image.get(attr)
                        if candidate and re.match(r'^https?://', candidate):
                            img_url = candidate
                            break
                        if img_url and img_url not in seen:
                            images.append(img_url)
                            seen.add(img_url)
                image_dir = f"./books/raw/temporary/images/"
                #Do not save these images permanent. Always overwrite.
                if images:
                    start_idx = image_counter  # Save the starting index
                    image_counter = await self.save_images_in_chapter(images, image_dir, image_counter)
                    # Replace all img srcs with local file path
                    for idx, img in enumerate(chapter_content.find_all('img')):
                        if idx < len(images):
                            img['src'] = f"images/image_{start_idx + idx}.png"
            
            file_chapter_title = f"{book_title} - {chapter_id} - {remove_invalid_characters(chapter_title)}"
            
            return file_chapter_title, currentImageCount, chapter_content
        except Exception as e:
            errorText=f"Failed to process new chapter. Function spacebattles_process_new_chapter_non_saved Error: {e}"
            write_to_logs(errorText)