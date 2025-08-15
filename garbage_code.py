
import os
from PIL import Image, ImageChops
import aiohttp
import asyncio
import logging
import re

from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
load_dotenv(env_path, override=True)
logLocation=os.getenv("logs")

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from seleniumwire import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
logging.getLogger('seleniumwire').setLevel(logging.WARNING)
import bs4
firefox_options = FirefoxOptions()

# Path to .xpi extension file
path_to_extension = os.getenv("LOCAL_ADBLOCK_EXTENSION")

basicHeaders={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "cookie": "cf_clearance=jmBzhtY.V13RoM4LZ9yjMeu..PVR2JJL4uULCtTpHu0-1753819000-1.2.1.1-OwVqAu5q0mfU3dvvHEaLaCuWZGrWWDsx1m32nOQc4szC6pp5WaY1WAs1Y1gDOHEkS5uynZ2RlJChHNeE4gW7PV4aCBnG1zjHQc5SS72ILgnrKVOdlD9s9_dXwfo7fC.hqTUmK9fqRgI2.XZ5SSXvYjdXT9L_E0DT6tvM8ZKnnVKZ41VaoscTz4zD31xGLuoce62eht1krkOwsEQqV.OxrnFYxxFzSLDjUNaNoblGuYk;_csrf=1oo4rZymlY8P6PkfYrnnsI3q"
}

def interception (request):
    global cookie
    del request.headers['User-Agent']
    del request.headers['Accept']
    del request.headers['Accept-Language']
    del request.headers['Accept-Encoding']
    del request.headers['Cookie']
    
    request.headers['User-Agent']=basicHeaders["User-Agent"]
    request.headers['Accept']=basicHeaders["Accept"]
    request.headers['Accept-Language']=basicHeaders["Accept-Language"]
    request.headers['Accept-Encoding']=basicHeaders["Accept-Encoding"]
    #request.headers['Cookie']=basicHeaders["cookie"]

async def open_link(url):
    try:
        driver = webdriver.Firefox(options=firefox_options)
        
        path_to_extension = os.getenv("LOCAL_ADBLOCK_EXTENSION")
        if not path_to_extension:
            logging.warning("LOCAL_ADBLOCK_EXTENSION environment variable is not set.")
        else:
            # Now safe to use path_to_extension
            driver.install_addon(path_to_extension, temporary=True)
        
        driver.install_addon(path_to_extension, temporary=True)
        driver.request_interceptor=interception
        driver.get(url)

        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        soup = bs4.BeautifulSoup(driver.execute_script("return document.body.innerHTML;"), 'html.parser')
        logging.warning(soup)
        driver.close()
        logging.warning(f"Opened link: {url}")
    except Exception as e:
        logging.warning(f"Error opening link {url}: {e}")
        soup = None

asyncio.run(open_link("https://novelbin.com/b/alantina-online-the-greatest-sword-mage-reborn-as-a-weak-npc/chapter-78-rare-drops-part-1"))

async def open_link(url):
    try:
        async with aiohttp.ClientSession(headers=basicHeaders) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logging.warning(f"Failed to open link: {url}, Status: {response.status}")
    except Exception as e:
        logging.warning(f"Error opening link {url}: {e}")

asyncio.run(open_link("https://novelbin.com/b/alantina-online-the-greatest-sword-mage-reborn-as-a-weak-npc/chapter-78-rare-drops-part-1"))




















# async def extract_chapter_from_book(dirLocation):
    
#     fileName=dirLocation.split("/")[-1]
#     if not fileName.endswith('.epub'):
#         errorText=f"Function extract_chapter_from_book Error: {fileName} is not an epub file."
#         write_to_logs(errorText)
#         return
    
    
#     volume_number = extract_volume_or_book_number(fileName)
#     chapterID=0
#     if volume_number:
#         chapterID = volume_number * 10000
    
#     chapter_metadata = []
#     book = epub.read_epub(dirLocation)
#     bookTitle=await process_book_title(book)
#     def get_existing_order_of_contents(book_title):
#         # Default implementation
#         dir_location = f"./books/imported/{book_title}/order_of_chapters.txt"
#         if os.path.exists(dir_location):
#             with open(dir_location, "r") as f:
#                 return f.readlines()
#         return []
    
#     existingChapters = get_existing_order_of_contents(bookTitle)
#     existingChapters = [line.strip().split(";") for line in existingChapters if line.strip()]
    
    
#     image_dir = f"./books/imported/{bookTitle}/images/"
#     cover_dir=f"./books/imported/{bookTitle}/"
#     try:
#         numberofImages=os.listdir(image_dir)
#         currentImageCounter=len(numberofImages)-1 if numberofImages else 0
#     except Exception as e:
#         errorText=f"Failed to get number of images in {image_dir}. Function extract_chapter_from_book Error: {e}"
#         logging.error(errorText)
#         write_to_logs(errorText)
#         currentImageCounter=0
#         numberofImages=[]
                
    
#     #Cover Image Only
#     images = book.get_items_of_type(ebooklib.ITEM_IMAGE)
#     if images:
#         for image in images:
#             if ("cover" in image.file_name):
#                 image_path = f"{cover_dir}cover_image.png"
#                 if not os.path.exists(cover_dir):
#                     os.makedirs(cover_dir)
#                 if not os.path.exists(image_path):
#                     with open(image_path, "wb") as f:
#                         f.write(image.get_content())
#                 else:
#                     image_bytes = image.get_content()
#                     if not is_image_duplicate(image_bytes,image_dir):
#                         existingImages=get_all_files_in_directory(cover_dir)
#                         cover_image_count = sum(1 for f in existingImages if "cover_image" in f)
#                         image_path = f"{cover_dir}cover_image_{cover_image_count}.png"
#                         try:
#                             with open(image_path, "wb") as f:
#                                 f.write(image.get_content())
#                         except Exception as e:
#                             errorText=f"Failed to write cover image bytes to file. Function extract_chapter_from_book Error: {e}, file:{bookTitle}"
#                             write_to_logs(errorText)
#                             continue
#                     else:
#                         logging.warning(f"Cover Image already exists in {image_dir}. Skipping.")
    
#     #reset counter
#     currentImageCounter=len(numberofImages)-1 if numberofImages else 0
#     for item in book.get_items():
#         if item.get_type() == ebooklib.ITEM_DOCUMENT:
#             print('==================================')
#             print('NAME : ', item.get_name())
#             print('----------------------------------')
#             #print(item.get_content())
#             #print('==================================')
            
#             soup= bs4.BeautifulSoup(item.get_content(), 'html.parser')
            
#             title =soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
#             if title=="":
#                 title=soup.find('h2').get_text(strip=True) if soup.find('h2') else ""
#             if title=="":
#                 title=soup.find('h3').get_text(strip=True) if soup.find('h3') else ""
#             if title=="":
#                 continue
            
#             chapterContent = soup
#             img_tags = chapterContent.find_all('img')
#             image_dir = f"./books/imported/{bookTitle}/images/"
#             if not os.path.exists(image_dir):
#                 os.makedirs(image_dir)
#             images = [img['src'] for img in img_tags if img.has_attr('src')]
#             if (images):
#                 logging.warning(images)

#             # Get all image items in the book for matching
#             image_items = {img_item.file_name: img_item for img_item in book.get_items_of_type(ebooklib.ITEM_IMAGE)}

#             for img in img_tags:
#                 img_src = img['src']
#                 # Try to find the corresponding image item in the epub
#                 matched_item = None
#                 for file_name, img_item in image_items.items():
#                     if img_src in file_name or file_name in img_src:
#                         matched_item = img_item
#                         break
#                 if not matched_item:
#                     continue  # Skip if not found in epub

#                 image_bytes = matched_item.get_content()
#                 image_path = f"{image_dir}image_{currentImageCounter}.png"

#                 # Check for duplicate in directory
#                 if not is_image_duplicate(image_bytes, image_dir):
#                     # Save new image and update src
#                     with open(image_path, "wb") as f:
#                         logging.warning(f"Saving image {currentImageCounter} to {image_path}")
#                         try:
#                             f.write(image_bytes)
#                             img['src'] = f"images/image_{currentImageCounter}.png"
#                             currentImageCounter += 1

#                         except Exception as e:
#                             errorText=f"Failed to write image bytes to file. Function extract_chapter_from_book Error: {e}"
#                             write_to_logs(errorText)
#                             continue
#                 else:
#                     # If duplicate, find the existing image index to point to
#                     # Loop through files to find the match and set src accordingly
#                     for idx, file in enumerate(sorted(os.listdir(image_dir))):
#                         file_path = os.path.join(image_dir, file)
#                         epub_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
#                         existing_img = Image.open(file_path).convert("RGB")
#                         try:
#                             if epub_img.size == existing_img.size:
#                                 diff = ImageChops.difference(epub_img, existing_img)
#                                 if not diff.getbbox():
#                                     img['src'] = f"images/{file}"
#                                     break
#                         except Exception:
#                             continue
            
            
#             #logging.warning(f"Chapter Title: {title}")
#             fileTitle= f"{bookTitle} - {remove_invalid_characters(title)}"
#             logging.warning(f"File Title: {fileTitle}")
#             store_chapter_version_two(chapterContent, bookTitle, fileTitle)
#             chapter_metadata.append([chapterID,title,f"./books/imported/{bookTitle}/{fileTitle}.html"])
#             chapterID+=1
            
    
    
#     def merge_chapter_lists_preserve_order(list1, list2):
#         """
#         Merge two lists of chapters, preserving order and removing duplicates.
#         Duplicates are detected by chapter title (case-insensitive, stripped).
#         Returns a merged list with unique chapters, order: all from list1, then unique from list2.
#         """
#         def chapter_key(chapter):
#             # chapter_metadata is saved as [ID, Title, FilePath]
#             # We assume the title is always at index 1, and it can be a list
#             if isinstance(chapter, list):
#                 return chapter[1].strip().lower()
#             return chapter.strip().lower()

#         seen = set()
#         merged = []
#         chapterID=0
#         # Add all chapters from list1, marking them as seen
#         for chapter in list1:
#             key = chapter_key(chapter)
#             if key not in seen:
#                 merged.append(chapter)
#                 seen.add(key)
#                 chapterID+=1

#         # Add only new chapters from list2
#         for chapter in list2:
#             key = chapter_key(chapter)
#             if key not in seen:
#                 chapter=[chapterID,chapter[1],chapter[2]]
#                 merged.append(chapter)
#                 seen.add(key)
#                 chapterID+=1
#         logging.warning(merged)
#         return merged
    
#     merged_chapter_metadata=merge_chapter_lists_preserve_order(existingChapters, chapter_metadata)
#     #logging.warning(merged_chapter_metadata)
#     def write_order_of_contents(book_title, chapter_metadata):
#         file_location = f"./books/imported/{book_title}/order_of_chapters.txt"
#         #logging.warning(chapter_metadata)
#         with open(file_location, "w") as f:
#             for data in chapter_metadata:
#                 if isinstance(data, str):
#                     data = data.strip().split(";")
#                 #logging.warning(data)
#                 f.write(";".join(map(str, data))+ "\n")
#     write_order_of_contents(bookTitle, merged_chapter_metadata)
    
#     #Create directory for the book
#     #make_directory(f"./books/imported/{bookTitle}")


# def test_compare_images():
#     img1_path = os.path.join('books', 'imported', 'DIE RESPAWN REPEAT', 'images', 'cover_image.png')
#     img2_path = os.path.join('books', 'imported', 'DIE RESPAWN REPEAT', 'images', 'cover_image - Copy.png')

#     if not os.path.exists(img1_path):
#         print(f"File not found: {img1_path}")
#         return
#     if not os.path.exists(img2_path):
#         print(f"File not found: {img2_path}")
#         return

#     try:
#         img1 = Image.open(img1_path)
#         img2 = Image.open(img2_path)
#         diff = ImageChops.difference(img1, img2)
#         if not diff.getbbox():
#             #logging.warning("Images are the same.")
#             return True
#         else:
#             #logging.warning("Images are different.")
#             return False
#     except Exception as e:
#         #logging.warning(f"Images are different (exception occurred: {e})")
#         return False

# async def download_file(url, filename):
#     async with aiohttp.ClientSession(headers = {
#             'User-agent': 'Image Bot'}) as session:
#         async with session.get(url) as response:
#             logging.warning(response.status)
#             if response.status !=200:
#                 logging.warning("Failed to connect")
#             logging.warning(response.content)
#             with open(filename, "wb") as f: 
#                 chunk_size = 4096
#                 async for data in response.content.iter_chunked(chunk_size):
#                     f.write(data)

# #asyncio.run(download_file("https://i.imgur.com/Kd5ERk2.jpg", "image.jpg"))


# def test():
#     urls=["https://www.royalroad.com/fiction/82591/magic-murder-cube-marine",
#     "https://novelbin.me/novel-book/raising-orphans-not-assassins",
#     "https://www.foxaholic.com/novel/hikikomori-vtuber-wants-to-tell-you-something/",
#     "https://forums.spacebattles.com/threads/quahinium-industries-shipworks-kancolle-si.1103320/",
#     "https://novelbin.com/b/"
#     ]
#     root_domains=[]
#     for url in urls:
#         match = re.search(r"https://(?:www\.)?([A-Za-z0-9.-]+)", url)
#         if match:
#             root_domains.append(match.group(1))
#     logging.warning(root_domains)
# test()



# async def updateEpub(novelURL,bookTitle):
#     already_saved_chapters=get_existing_order_of_contents(bookTitle)
#     chapterMetaData=list()
#     imageCount=0
#     logging.warning("Finding chapters not stored")
#     logging.warning(await RoyalRoad_Fetch_Chapter_List(novelURL))
#     for url in await RoyalRoad_Fetch_Chapter_List(novelURL):
#         chapterID=extract_chapter_ID(url)
#         if not (check_if_chapter_exists(chapterID,already_saved_chapters)):
#             soup=await getSoup(url)
#             chapterTitle=await fetch_Chapter_Title(soup)
#             logging.warning(url)
#             fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
#             chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{fileChapterTitle}.html"])
#             chapterContent=await RoyalRoad_Fetch_Chapter(soup)
#             if chapterContent:
#                 images=chapterContent.find_all('img')
#                 images=[image['src'] for image in images]
#                 imageDir=f"./books/raw/{bookTitle}/images/"
#                 currentImageCount=imageCount
#                 #logging.warning(images)
#                 if (images):
#                     imageCount=await save_images_in_chapter(images,imageDir,imageCount)
#                     for img,image in zip(chapterContent.find_all('img'),images):
#                         img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")
#                 else:
#                     logging.warning("Chapter has no images")
#             else:
#                 logging.warning("chapterContent is None")
            
            

#             chapterContent=chapterContent.encode('ascii')
#             store_chapter(chapterContent,bookTitle,chapterTitle,chapterID)
#             await asyncio.sleep(0.5)
#     append_order_of_contents(bookTitle, chapterMetaData)


# def generate_Epub_Based_On_Stored_Order(new_epub, bookTitle):
#     already_saved_chapters=get_existing_order_of_contents(bookTitle)
    
#     tocList=list()
#     for url in already_saved_chapters:
#         url=url.split(";")
#         chapterID=url[0]
#         fileChapterTitle=extract_chapter_title(url[len(url)-1])
#         dirLocation=url[len(url)-1]
#         chapterContent=get_chapter_contents_from_saved(dirLocation).encode("utf-8")
        
#         strippedTitle=fileChapterTitle.split('-')
#         strippedTitle=strippedTitle[len(strippedTitle)-1].strip()
        
#         chapter=epub.EpubHtml(title=strippedTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
#         chapter.set_content(chapterContent)
        
        
#         tocList.append(chapter)
        
#         new_epub.add_item(chapter)
    
#     new_epub.toc=tocList
#     storeEpub(bookTitle,new_epub)
    
        
# def generate_Epub_Based_On_Online_Order(new_epub,novelURL,bookTitle):
#     tocList=list()
#     for url in RoyalRoad_Fetch_Chapter_List(novelURL):
#         chapterID=extract_chapter_ID(url)
#         chapterTitle=fetch_Chapter_Title(url)
#         fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
#         chapterContent=RoyalRoad_Fetch_Chapter(url)
        
        
#         chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
#         chapter.set_content(chapterContent)
        
#         tocList.append(chapter)
        
#         new_epub.add_item(chapter)
        
#         time.sleep(0.5)
#     new_epub.toc=tocList
#     storeEpub(bookTitle,new_epub)

# response=requests.get(image,stream=True, headers = {'User-agent': 'Image Bot'})
# time.sleep(0.5)
# imageCount+=1
# if response.ok:
#     response=response.content
#     with open (imageDir,'wb') as f:
#         f.write(response)
#     f.close()


# async with aiohttp.ClientSession(headers = {
#     "Host": "www.foxaholic.com",
#     "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
#     "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
#     "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
#     "Accept-Encoding": "gzip, deflate, br, zstd",
#     "Referer": "https://www.foxaholic.com/novel/ankoku-kishi-monogatari-yuusha-wo-taosu-tameni-maou-ni-shoukansaremashita/",
#     #Foxaholic requires cookie. Will need to get new cookie each time.
#     "Cookie": "cf_clearance=SNaHcNrSUkA8AP0tbL7.PL6H_27QedJXi62Taf3wZ9Q-1744213439-1.2.1.1-U4L692Wcb9hCY2168bRBt_YfzYcA9AhUKjFxmeoCjm3uwKuLdD0VN29Wl6x7Gq5RcHrupkWvawaSFuoDbhOH_eQD2_vd012lS9vr6bBBNw4xUMwBzkp71hX70lrjnH0uRWuKztMC47_qSDay5RdklFss0G9zP3YJ3lhFgzjD7dUkbX0T4xJJ.wdFcVayxqDgBQPwSBTE5GTf_yCF4ZVxFT.Dk.LH3FfbYsE9EMYlcaDGGGCexTpVcFxvYGad81idSRMdzv9H0XibWmybhASDXnY17YYsy5INxG3.qrBqKXqykl4x6rLxeyUL.9SZq2LEhCfskht0F2IPoiMVaazgeKiHM17B1G0eo40DRIzzNcW3_6yGrjGLmM7MhXvu8D8p",
#     }) as session:
#     async with session.get(url) as response:
#         #logging.warning(response.status)
#         if response.status == 200:
#             logging.warning(response)
#             html = await response.text()
#             soup = bs4.BeautifulSoup(html, 'html.parser')
#             chapterTable = soup.find("ul", {"class": "main version-chap"})
#             rows= chapterTable.find_all("li", {"class":"free-chap"})
#             chapterListURL=list()
#             for row in rows[1:len(rows)]:
#                 chapterData={}
#                 chapterData["name"]=row.find("a").contents[0].strip()
#                 processChapterURL=row.find("a")["href"]
                
#                 chapterURL=processChapterURL
#                 chapterListURL.append(chapterURL)
#             logging.warning(chapterListURL)      
#             return chapterListURL







#There needs to be a file to keep track of the order of the chapters within the books/raw/bookTitle folder.
#This is because authors tend to go between Ch then Vol Ch, and then back to Ch

# def check_order_of_contents(bookTitle,novelURL):
#     dirLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
#     if (check_directory_exists(dirLocation)):
#         f= open(dirLocation,"r")
#         f.read()
#     else:
#         f=[]
    
#     chapterList=extract_chapter_ID(fetch_Chapter_List(novelURL))
#     newChapterList=update_order_of_contents(chapterList,f)
    
#     write_order_of_contents(newChapterList,bookTitle)
    
#     if (isinstance(f,io.IOBase)):
#         f.close()

    
# def update_order_of_contents(chapterList, existingChapterList):
#     seen = set()
#     combined_list = []

#     for chapter in existingChapterList:
#         if chapter not in seen:
#             seen.add(chapter)
#             combined_list.append(chapter)

#     for chapter in chapterList:
#         if chapter not in seen:
#             seen.add(chapter)
#             combined_list.append(chapter)

#     return combined_list

# def test_delete():
#     newChapterList=delete_from_Chapter_List([2,4],get_existing_order_of_contents("FINAL CORE"))
#     if (newChapterList==False):
#         logging.warning("Delete failed")
#     else:
#         test_update_existing_order_of_contents("FINAL CORE",newChapterList)

# def test_insert():
#     f=open ("chapters.txt","r")
#     chapterList=f.readlines() #Use readlines to get list object
#     f.close()
#     newChapterList=insert_into_Chapter_List([2,5],1,chapterList,get_existing_order_of_contents("FINAL CORE"))
#     test_update_existing_order_of_contents("FINAL CORE",newChapterList)


# def test_update_existing_order_of_contents(bookTitle,chapterList):
#     bookDirLocation=f"./books/raw/{bookTitle}"
#     if not (check_directory_exists(bookDirLocation)):
#         make_directory(bookDirLocation)
#     fileLocation=f"./books/raw/{bookTitle}/test.txt"
#     if (os.path.exists(fileLocation)):
#         f=open(fileLocation,"w")
#     else:
#         f=open(fileLocation,"x")
#     for line in chapterList:
#         f.write(str(line)) #FORMATTING IS FUCKED
#     f.close()




# def test_get_existing_order_of_contents(bookTitle):
#     dirLocation=f"./books/raw/{bookTitle}/test.txt"
#     if (check_directory_exists(dirLocation)):
#         f=open(dirLocation,"r")
#         chapters=f.readlines()
#         return chapters
#     else:
#         return False







# #Obsolete. Foxaholic does not have a working search api.
# def foxaholic_query(title,cookie):
#     if (title.isspace() or title==""):
#         return "Invalid Title"
    
#     querylink = f"https://www.foxaholic.com/?s={title}"

#     soup=foxaholic_driver_selenium(querylink,cookie)
    
#     resultTable=soup.find("div",{"class":"tab-content-wrap"})
#     bookTable=resultTable.find("h4",{"class":"heading"})
#     bookRows=bookTable.find("a")
#     firstResult=bookRows['href']

#     #formatting
#     resultLink=f"https://www.royalroad.com{firstResult}"
    
#     return resultLink



# async def produceEpub(new_epub,novelURL,bookTitle,css):
#     already_saved_chapters=get_existing_order_of_contents(bookTitle)
#     chapterMetaData=list()
    
#     tocList=list()
    
#     imageCount=0
#     for url in await RoyalRoad_Fetch_Chapter_List(novelURL):
#         logging.warning(url)
#         chapterID=extract_chapter_ID(url)
#         if (check_if_chapter_exists(chapterID,already_saved_chapters)):
#             chapterID,dirLocation=get_chapter_from_saved(chapterID,already_saved_chapters)
#             chapterContent=get_chapter_contents_from_saved(dirLocation)
#             fileChapterTitle=extract_chapter_title(dirLocation)
            
#             chapterTitle=fileChapterTitle.split('-')
#             chapterTitle=chapterTitle[len(chapterTitle)-1]
            
#             images=re.findall(r'<img\s+[^>]*src="([^"]+)"[^>]*>',chapterContent)
#             currentImageCount=imageCount
#             for image in images:
#                 imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
#                 epubImage=retrieve_stored_image(imageDir)
#                 b=io.BytesIO()
#                 epubImage.save(b,'png')
#                 b_image1=b.getvalue()
                
#                 image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
#                 new_epub.add_item(image_item)
#                 currentImageCount+=1
#             chapterContent=chapterContent.encode("utf-8")
#         else:
#             await asyncio.sleep(0.5)
#             soup=await getSoup(url)
#             chapterTitle=await fetch_Chapter_Title(soup)
#             fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
#             #logging.warning(fileChapterTitle)
#             chapterMetaData.append([chapterID,url,f"./books/raw/{bookTitle}/{fileChapterTitle}.html"])
#             chapterContent=await RoyalRoad_Fetch_Chapter(soup)
            
#             if chapterContent:
#                 images=chapterContent.find_all('img')
#                 images=[image['src'] for image in images]
#                 imageDir=f"./books/raw/{bookTitle}/images/"
#                 currentImageCount=imageCount
#                 #logging.warning(images)
#                 if (images):
#                     imageCount=await save_images_in_chapter(images,imageDir,imageCount)
#                     for img,image in zip(chapterContent.find_all('img'),images):
#                         img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")
                        
#                         imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
#                         epubImage=retrieve_stored_image(imageDir)
#                         b=io.BytesIO()
#                         epubImage.save(b,'png')
#                         b_image1=b.getvalue()
                        
#                         image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
#                         new_epub.add_item(image_item)
#                         currentImageCount+=1
#                 else:
#                     logging.warning("There are no images in this chapter")
#             else:
#                 logging.warning("chapterContent is None")

#             chapterContent=chapterContent.encode('ascii')
#             store_chapter(chapterContent,bookTitle,chapterTitle,chapterID)

#         chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
#         chapter.set_content(chapterContent)
#         chapter.add_item(css)
#         tocList.append(chapter)
#         new_epub.add_item(chapter)
    
#     logging.warning("We reached retrieve_cover_from_storage")
#     img1=retrieve_cover_from_storage(bookTitle)
#     if img1:    
#         b=io.BytesIO()
#         try:
#             img1.save(b,'png')
#             b_image1=b.getvalue()
#             image1_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image1)
#             new_epub.add_item(image1_item)
#         except Exception as e:
#             logging.warning(f"Failed to save image:{e}")
    
#     new_epub.toc=tocList
#     new_epub.spine=tocList
#     new_epub.add_item(epub.EpubNcx())
#     new_epub.add_item(epub.EpubNav())
    
#     write_order_of_contents(bookTitle, chapterMetaData)
    
#     logging.warning("Attempting to store epub")
#     storeEpub(bookTitle, new_epub)



#Discord Bot code


        ##THIS DOES and DOES NOT WORK.
        #This times out heartbeat but somehow manages to send the epub???
        #task1=asyncio.create_task(scrape.mainInterface(novelURL))
        #thread = threading.Thread(target=scrape.mainInterface(novelURL))
        #thread.start()
        #thread.join()
        
        
        #task = asyncio.create_task(await scrape.mainInterface(novelURL))
        #book=await task



 # if not (bookQueue.empty() and asyncio.get_event_loop() is None):
    #     logging.warning(f"Book Queue: {bookQueue.qsize()}")
    #     url,channelID=bookQueue.get()
    #     #asyncio.gather(asyncio.to_thread(grabNovel(url,channelID)))
        
    #     asyncio.gather(asyncio.to_thread(grabNovel(url,channelID)))
        
        #asyncio.to_thread(await grabNovel(url,channelID))
        #threading.Thread(target=asyncio.gather(await grabNovel(url,channelID))).start()
#        threading.Thread(target=grabNovel, args=(url,channelID)).start()
                        #t1=threading.Thread(target=grabNovel, args=(bookQueue[0][1],bookQueue[0][1]))
                        #t1.start()
#https://docs.python.org/3/library/asyncio-eventloop.html#
#https://docs.python.org/3/library/asyncio-task.html#coroutine

#asyncio.create_task(scrape.mainInterface(novelURL))


# try:
                    #     async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",}) as session:
                    #                     if not isinstance(img_url,str):
                    #                         img_url=img_url["src"]
                    #                     async with session.get(img_url) as response:
                    #                         if response.status == 200:
                    #                             response=await response.content.read()
                    #                             with open(image_path, "wb") as f:
                    #                                 f.write(response)
                    
                    
                    
                    # async def save_images_in_chapter(self, img_urls, save_directory, image_count):
                    #     if not os.path.exists(save_directory):
                    #         os.makedirs(save_directory)
                    #     #logging.warning(img_urls)
                    #     try:
                    #         for img_url in img_urls:
                    #             image_path = f"{save_directory}image_{image_count}.png"
                    #             if not os.path.exists(image_path):
                    #                 async with aiohttp.ClientSession(headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",}) as session:
                    #                     if not isinstance(img_url,str):
                    #                         img_url=img_url["src"]
                    #                     async with session.get(img_url) as response:
                    #                         if response.status == 200:
                    #                             response=await response.content.read()
                    #                             with open(image_path, "wb") as f:
                    #                                 f.write(response)
                    #                     image_count += 1
                    #             await asyncio.sleep(0.5)
                    #         return image_count
                    #     except Exception as e:
                    #         errorText=f"Failed to get save image. Function save_images_in_chapter Error: {e}"
                    #         write_to_logs(errorText)
                    
                    