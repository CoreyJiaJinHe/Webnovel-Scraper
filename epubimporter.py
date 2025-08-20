

import bs4
import re
import os, errno
import datetime
import logging
import asyncio
import io
from ebooklib import epub 
from PIL import Image, ImageChops
import aiohttp
from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
load_dotenv(env_path, override=True)
logLocation=os.getenv("logs")


# Add these missing imports:
from backend.common import (
    write_to_logs, 
    check_directory_exists, 
    make_directory, 
    remove_tags_from_title, 
    store_chapter, 
    retrieve_cover_from_storage, 
    storeEpub,
    get_first_last_chapter,
    remove_invalid_characters,
    create_epub_directory_url,
    sanitize_title,
    generate_new_ID
)


from mongodb import(
    check_existing_book,
    check_existing_book_Title,
    check_latest_chapter,
    check_recently_scraped,
    create_Entry, 
    create_latest,
    get_all_book_titles,
    get_Entry_Via_Title,
    create_imported_book_record,
    update_imported_book_record,
    check_existing_imported_book_via_title,
    check_existing_imported_book_via_ID
)



from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from seleniumwire import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile

firefox_options = FirefoxOptions()

# Path to .xpi extension file
path_to_extension = os.getenv("LOCAL_ADBLOCK_EXTENSION")


def extract_volume_or_book_number(fileName):
        """
        Extracts the volume or book number from a fileName string.
        Looks for patterns like 'vol5', 'vol_5', 'vol-5', 'book5', 'book_5', 'book-5', case-insensitive.
        Returns the number as an integer if found, otherwise None.
        """
        match = re.search(r'(?:vol|book)[\s\-_]*([0-9]+)', fileName, re.IGNORECASE)
        if match:
            return int(match.group(1))
        return None

def fuzzy_similarity(newBookTitle, existingBookTitles):
    """
    Returns the string from existingBookTitles with the highest similarity to newBookTitle,
    based on the longest common subsequence ratio.
    """
    def normalize_string(s):
        return re.sub(r'[\W_]+', '', s).lower()  # removes all non-alphanumeric chars and lowercases

    # Dynamic programming approach for LCS
    def levenshtein_distance(s1, s2):
        m, n = len(s1), len(s2)
        # Initialize distance matrix
        dp = [[0] * (n + 1) for _ in range(m + 1)]
        for i in range(m + 1):
            dp[i][0] = i
        for j in range(n + 1):
            dp[0][j] = j
        # Compute distances
        for i in range(1, m + 1):
            for j in range(1, n + 1):
                cost = 0 if s1[i - 1] == s2[j - 1] else 1
                dp[i][j] = min(
                    dp[i - 1][j] + 1,      # Deletion
                    dp[i][j - 1] + 1,      # Insertion
                    dp[i - 1][j - 1] + cost  # Substitution
                )
        return dp[m][n]

    best_match = None
    best_score = 0.0
    newBookTitle = normalize_string(newBookTitle)
    for book in existingBookTitles:
        if not newBookTitle or not book:
            continue
        book= normalize_string(book)
        #logging.warning(f"Comparing '{newBookTitle}' with '{book}'")
        lev_dist = levenshtein_distance(newBookTitle, book)
        max_len = max(len(newBookTitle), len(book))
        score = 1 - (lev_dist / max_len) if max_len > 0 else 0.0
        if score > best_score:
            best_score = score
            best_match = book
    #logging.warning(f"Best match for '{newBookTitle}' is '{best_match}' with score {best_score:.2f}")
    return best_match, best_score



def store_chapter_version_two(chapterContent,bookTitle,fileTitle):
    bookDirLocation = "./books/imported/" + bookTitle+"/"
    if not check_directory_exists(bookDirLocation):
        make_directory(bookDirLocation)

    # Check if the chapter already exists
    dirLocation = f"./books/imported/{bookTitle}/{fileTitle}.html"
    if check_directory_exists(dirLocation):
        return

    # Write the chapter content to the file with UTF-8 encoding
    chapterDirLocation = "./books/imported/" + bookTitle + "/"
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


import ebooklib
import xml.etree.ElementTree as ET

def extract_series_from_epub(book):
    try:
        # 1. Try to find 'series' in book.metadata (all namespaces)
        for ns, meta_dict in book.metadata.items():
            for key, values in meta_dict.items():
                if 'series' in key.lower():
                    for value, attrs in values:
                        # Try 'content' in attrs first
                        if isinstance(attrs, dict) and 'content' in attrs and attrs['content']:
                            return attrs['content']
                        # Try value itself if it's a string and not None
                        if value:
                            return value
        # 2. Try to find in OPF XML <meta> tags
        opf_item = None
        for item in book.get_items():
            if item.file_name.endswith('.opf'):
                opf_item = item
                break
        if opf_item:
            opf_xml = opf_item.get_content()
            root = ET.fromstring(opf_xml)
            # Find <metadata> element (namespace-agnostic)
            metadata_elem = None
            for elem in root.iter():
                if elem.tag.lower().endswith('metadata'):
                    metadata_elem = elem
                    break
            if metadata_elem is not None:
                for meta in metadata_elem.iter():
                    if meta.tag.lower().endswith('meta'):
                        # Check both 'name' and 'property' attributes for 'series'
                        for attr in ['name', 'property']:
                            if attr in meta.attrib and 'series' in meta.attrib[attr].lower():
                                if 'content' in meta.attrib:
                                    return meta.attrib['content']
                                elif meta.text:
                                    return meta.text
    except Exception as e:
        errorText=f"Failed to extract series from epub. Function extract_series_from_epub Error: {e}, book:{book.get_metadata('DC', 'title')}"
        #logging.error(errorText)
        write_to_logs(errorText)
        
    # Not found
    return ""

# Usage in your import_from_epub:
#fileName="DRR 3 - Fragments of Time - Silver Linings.epub"
#dirLocation= f"./books/imported/{fileName}"

def remove_tags_from_inside_brackets(text):
    """
    Removes all text inside brackets, including the brackets themselves.
    """
    return re.sub(r'[\[\(].*?[\]\)]', '', text)

async def process_book_title(book):
    series = extract_series_from_epub(book)
    series = remove_invalid_characters(series)
    if series and series !="":
        bookTitle = series
    else:
        # Fallback to dc:title
        bookTitle = book.get_metadata('DC', 'title') 
        if bookTitle and isinstance(bookTitle, list) and len(bookTitle) > 0:
            bookTitle = bookTitle[0][0]
            bookTitle= remove_tags_from_inside_brackets(bookTitle)
            bookTitle=remove_invalid_characters(bookTitle)
        else:
            bookTitle = ""
    return bookTitle


def detect_epub_source(book):
    """
    Attempts to detect the source website of an epub by searching for known domains
    in the OPF file, stylesheets, and chapter HTML content.
    Returns the source as a string, or 'Unknown' if not found.
    """

    # List of known sources and their identifying keywords/domains
    known_sources = {
        "royalroad.com": ["royalroad.com"],
        "scribblehub.com": ["scribblehub.com"],
        "forums.spacebattles.com": ["spacebattles.com"],
        "novelbin.me": ["novelbin.me", "novelbin.com"],
        "foxaholic.com": ["foxaholic.com"],
        # Add more as needed
    }

    # Helper to check for keywords in a string
    def find_source_in_text(text):
        for source, keywords in known_sources.items():
            for keyword in keywords:
                if keyword in text:
                    return source
        return None

    # 1. Check OPF file (metadata)
    opf_item = None
    for item in book.get_items():
        if item.file_name.endswith('.opf'):
            opf_item = item
            break
    if opf_item:
        opf_content = opf_item.get_content().decode(errors="ignore")
        found = find_source_in_text(opf_content)
        if found:
            return found

    # 2. Check all stylesheets
    for item in book.get_items_of_type(ebooklib.ITEM_STYLE):
        style_content = item.get_content().decode(errors="ignore")
        found = find_source_in_text(style_content)
        if found:
            return found

    # 3. Check all HTML chapters
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        html_content = item.get_content().decode(errors="ignore")
        found = find_source_in_text(html_content)
        if found:
            return found

    # 4. Check all images (sometimes watermarks or URLs)
    for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
        if hasattr(item, 'file_name') and find_source_in_text(item.file_name):
            return find_source_in_text(item.file_name)

    # 5. Fallback
    return "Unknown"


async def fetch_novel_data_from_epub(dirLocation) -> dict:
    
    try:
        #logging.warning(f"Importing from epub: {dirLocation}")
        book = epub.read_epub(dirLocation)
        #logging.warning(book)
        bookTitle=await process_book_title(book)
        
        bookAuthor = book.get_metadata('DC', 'creator')
        if bookAuthor and isinstance(bookAuthor, list) and len(bookAuthor) > 0:
            bookAuthor = bookAuthor[0][0]
        else:
            bookAuthor = ""

            
        bookDescription = book.get_metadata('DC', 'description') if book.get_metadata('DC', 'description') else ""
        bookDescription= bookDescription[0][0] if isinstance(bookDescription, list) and len(bookDescription) > 0 else bookDescription
        if ("\n" in bookDescription):
            bookDescription=bookDescription.replace("\n"," ")
        if ("  " in bookDescription):
            bookDescription=bookDescription.replace("  "," ")
                    
        origin=detect_epub_source(book)
        
        bookID=str(generate_new_ID(bookTitle,origin))
        lastScraped = datetime.datetime.now()
        latestChapterTitle = ""
        try:
            chapters = list(book.get_items())
            # Find the last non-cover.xhtml document with a valid title
            idx = len(chapters) - 1
            latestChapterTitle = ""
            while idx >= 0:
                last_chapter = chapters[idx]
                # Skip if it's a cover.xhtml file
                if last_chapter.get_name().lower().endswith("cover.xhtml"):
                    idx -= 1
                    continue
                soup = bs4.BeautifulSoup(last_chapter.get_content(), 'html.parser')
                # Try to find the latest chapter title from headings
                title = ""
                for tag in ['h1', 'h2', 'h3']:
                    heading = soup.find(tag)
                    if heading and heading.get_text(strip=True):
                        title = heading.get_text(strip=True)
                        break
                if title:
                    latestChapterTitle = remove_invalid_characters(title)
                    break  # Found a valid title, exit loop
                idx -= 1
            if not latestChapterTitle:
                latestChapterTitle = "N/A"
                
        
        
        except Exception as e:
            errorText=f"Failed to extract latest chapter title from epub. Function fetch_novel_data_from_epub Error: {e}, file: {dirLocation}"
            logging.error(errorText)
            write_to_logs(errorText)
            # Fallback if not found
            latestChapterTitle="N/A"

        
        
        latestChapterID="N/A"
        book ={
            "bookID":bookID,
            "bookTitle":bookTitle,
            "bookAuthor":bookAuthor,
            "bookDescription":bookDescription,
            "origin":origin,
            "lastScraped":lastScraped,
            "latestChapterTitle":latestChapterTitle,
            "latestChapterID":latestChapterID
        }
        logging.warning(f"[fetch_novel_data_from_epub] Returning: {book} (type: {type(book)})")
        return book



    except Exception as e:
        errorText=f"Function fetch_novel_data_from_epub. Failed to import from epub: {e}"
        logging.error(errorText)
        write_to_logs(errorText)
        return None



def get_epubs_to_import():
    dirLocation= "./books/imported/epubs"
    dir_list=os.listdir(dirLocation)
    #print(f"Files in {dirLocation}:")
    # print(dir_list)
    # write_to_logs(f"Files in {dirLocation}: {dir_list}")
    override=False
    if (override):
        filtered_list = [f for f in dir_list if "DIE RESPAWN REPEAT" in f]
        return filtered_list
        
        #return sorted(dir_list)[:10]
    return dir_list

#dir_list=get_epubs_to_import()

def get_all_files_in_directory(directory):
    dir_list=os.listdir(directory)
    print(f"Files in {directory}:")
    print(dir_list)
    return dir_list

def compare_files_in_directory(directory):
    dir_list=get_all_files_in_directory(directory)
    with open("{directory}/order_of_chapters.txt", "r") as f:
        order_of_contents_chapters= f.readlines()
    file_names = []
    for line in order_of_contents_chapters:
        parts = line.strip().split(";")
        if len(parts) >= 3:
            file_path = parts[2]
            file_name = os.path.basename(file_path)
            file_names.append(file_name)
    extra_files = [f for f in dir_list if f not in file_names]

    print("Files in directory not listed in order_of_chapters.txt:")
    for f in extra_files:
        print(f)
    
    
    
def get_existing_order_of_contents(book_title):
        # Default implementation
        dir_location = f"./books/imported/{book_title}/order_of_chapters.txt"
        if os.path.exists(dir_location):
            with open(dir_location, "r") as f:
                return f.readlines()
        return []

async def compare_existing_with_import(dirLocation)-> list:
    existingBookTitles=get_all_book_titles()
    book =await fetch_novel_data_from_epub(dirLocation)

    bookMatch,bookScore=fuzzy_similarity(book["bookTitle"], existingBookTitles)

    if (bookScore>=0.8):
        return True, book["bookTitle"]
    else:
        return False, None

async def compare_all_epubs_in_dir_with_existing(dir_list,condition):
    existingBookTitles=get_all_book_titles()
    matchingBooks = set()  # Use a set for uniqueness
    
    for item in dir_list:
        if item.endswith('.epub'):
            #logging.warning(f"Extracting from file: {item}")
            dirLocation= f"./books/imported/epubs/{item}"
            bookID, bookTitle, bookAuthor, bookDescription, origin, lastScraped, latestChapterTitle = await fetch_novel_data_from_epub(dirLocation)
            if bookTitle:
                #logging.warning(f"Read: {bookTitle} by {bookAuthor}")
                bookMatch,bookScore=fuzzy_similarity(bookTitle, existingBookTitles)
                if (condition):
                    if (bookScore>=0.8):
                        #logging.warning(f"Book {bookTitle} is similar to existing book {bookMatch} with score {bookScore}. Skipping.")
                        
                        matchingBooks.add(bookTitle)  # Add to set
                else:
                    if (bookScore<0.8):
                        #logging.warning(f"Book {bookTitle} is not similar to existing book {bookMatch} with score {bookScore}. Adding to matching books.")
                        matchingBooks.add(bookTitle)
                
            else:
                errorText=f"Failed to import from {item}"
                write_to_logs(errorText)
                logging.warning(errorText)
            
    return matchingBooks
#logging.warning(asyncio.run(compare_existing_with_import(dir_list)))
# logging.warning(asyncio.run(import_from_epub("Legendary Shadow Blacksmith Ch1-102.epub")))


async def extract_from_epub(dirLocation, bookTitle)-> None:
    try:
        fileName=dirLocation.split("/")[-1]
        if not fileName.endswith('.epub'):
            errorText=f"Function extract_from_epub Error: {fileName} is not an epub file."
            write_to_logs(errorText)
            return
        override=False
        if override:
            bookTitle = fileName[:-5] if fileName.lower().endswith('.epub') else fileName
    except Exception as e:
        errorText=f"Function extract_from_epub Error: {e}, file:{fileName}"
        write_to_logs(errorText)
        logging.warning(errorText)
        return 

    volume_number = extract_volume_or_book_number(fileName)
    chapterID=0
    if volume_number:
        chapterID = volume_number * 10000
    chapter_metadata = []
    book = epub.read_epub(dirLocation)
    
    def get_existing_order_of_contents(book_title):
        # Default implementation
        dirLocation=f"./books/raw/{book_title}/order_of_chapters.txt"
        if os.path.exists(dirLocation):
            with open(dirLocation, "r") as f:
                return f.readlines()
        return []
    
    existingChapters = get_existing_order_of_contents(bookTitle)
    existingChapters = [line.strip().split(";") for line in existingChapters if line.strip()]
    
    cover_dir=f"./books/raw/{bookTitle}/"
    #Cover Image Only
    images = book.get_items_of_type(ebooklib.ITEM_IMAGE)
    if images:
        for image in images:
            if ("cover" in image.file_name):
                image_path = f"{cover_dir}cover_image.png"
                if not os.path.exists(cover_dir):
                    os.makedirs(cover_dir)
                if not os.path.exists(image_path):
                    with open(image_path, "wb") as f:
                        f.write(image.get_content())
                else:
                    image_bytes = image.get_content()
                    if not is_image_duplicate(image_bytes,image_dir):
                        existingImages=get_all_files_in_directory(cover_dir)
                        cover_image_count = sum(1 for f in existingImages if "cover_image" in f)
                        image_path = f"{cover_dir}cover_image_{cover_image_count}.png"
                        try:
                            with open(image_path, "wb") as f:
                                f.write(image.get_content())
                        except Exception as e:
                            errorText=f"Failed to write cover image bytes to file. Function extract_chapter_from_book Error: {e}, file:{bookTitle}"
                            write_to_logs(errorText)
                            continue
                    else:
                        logging.warning(f"Cover Image already exists in {image_dir}. Skipping.")

    image_dir = f"./books/raw/{bookTitle}/images/"    
    try:
        numberofImages = [f for f in os.listdir(image_dir) if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]
        currentImageCounter = len(numberofImages)
    except Exception as e:
        errorText=f"Failed to get number of images in {image_dir}. Function extract_chapter_from_book Error: {e}"
        logging.error(errorText)
        write_to_logs(errorText)
        currentImageCounter=0
        numberofImages=[]
    
    # Get all image items in the book for matching
    image_items = {img_item.file_name: img_item for img_item in book.get_items_of_type(ebooklib.ITEM_IMAGE)}
    #Grab Chapters and any images in each chapter
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            print('==================================')
            print('NAME : ', item.get_name())
            print('----------------------------------')
            #print(item.get_content())
            #print('==================================')
            
            soup= bs4.BeautifulSoup(item.get_content(), 'html.parser')
            
            item_name = item.get_name().lower()
            # Check for cover.xhtml and if cover image hasn't been saved yet
            if "cover.xhtml" in item_name:
                cover_dir = f"./books/raw/{bookTitle}/"
                image_dir = f"{cover_dir}images/"
                cover_image_path = f"{cover_dir}cover_image.png"
                if not os.path.exists(cover_dir):
                    os.makedirs(cover_dir)
                if not os.path.exists(cover_image_path):
                    soup = bs4.BeautifulSoup(item.get_content(), 'html.parser')
                    # Try to find the first <img> or <image> tag
                    cover_img_tag = soup.find('img')
                    if not cover_img_tag:
                        cover_img_tag = soup.find('image')
                    if cover_img_tag:
                        # Get the image source
                        img_src = cover_img_tag.get('src') or cover_img_tag.get('xlink:href')
                        if img_src:
                            # Find the corresponding image item in the epub
                            matched_item = None
                            for file_name, img_item in image_items.items():
                                if img_src in file_name or file_name in img_src:
                                    matched_item = img_item
                                    break
                            if matched_item:
                                image_bytes = matched_item.get_content()
                                # Duplicate check before saving
                                if not is_image_duplicate(image_bytes, cover_dir):
                                    try:
                                        with open(cover_image_path, "wb") as f:
                                            f.write(image_bytes)
                                        logging.warning(f"Saved cover image from {item_name} to {cover_image_path}")
                                    except Exception as e:
                                        errorText = f"Failed to write cover image from {item_name}. Error: {e}"
                                        write_to_logs(errorText)
                                else:
                                    logging.warning(f"Duplicate cover image detected in {cover_dir}. Skipping save.")
                continue
            
            title =soup.find('h1').get_text(strip=True) if soup.find('h1') else ""
            if title=="":
                title=soup.find('h2').get_text(strip=True) if soup.find('h2') else ""
            if title=="":
                title=soup.find('h3').get_text(strip=True) if soup.find('h3') else ""
            if title=="":
                continue
            if title.lower().startswith(bookTitle.lower()):
                # Remove bookTitle and any following separators (space, dash, colon, etc.)
                title = title[len(bookTitle):].lstrip(" -:–—")
                
            if not title.lower().startswith("chapter"):
                title = f"Chapter {title}"   
            
            chapterContent = soup
            #Convert <image> tags to <img> tags
            for svg_tag in chapterContent.find_all('svg'):
                svg_tag.unwrap()
            
            for image_tag in chapterContent.find_all('image'):
                # Create a new <img> tag
                img_tag = chapterContent.new_tag('img')
                # Copy relevant attributes (commonly xlink:href, width, height)
                if image_tag.has_attr('xlink:href'):
                    img_tag['src'] = image_tag['xlink:href']
                if image_tag.has_attr('width'):
                    img_tag['width'] = image_tag['width']
                if image_tag.has_attr('height'):
                    img_tag['height'] = image_tag['height']
                # Copy any other attributes you want as needed

                # Replace <image> with <img>
                image_tag.replace_with(img_tag)
            
            
            
            #Discover if images exist in current chapter
            img_tags = chapterContent.find_all('img')
            image_dir = f"./books/raw/{bookTitle}/images/"
            if not os.path.exists(image_dir):
                os.makedirs(image_dir)
            images = [img['src'] for img in img_tags if img.has_attr('src')]
            if (images):
                logging.warning(images)

            for img in img_tags:
                img_src = img['src']
                # Try to find the corresponding image item in the epub
                #We do this because while we have all the images, we need to match them with the ones in the epub
                #So that we can replace the epub's [src] tags with the new image paths.
                #I'm not actually sure if I need to do this part.
                matched_item = None
                for file_name, img_item in image_items.items():
                    if img_src in file_name or file_name in img_src:
                        matched_item = img_item
                        break
                if not matched_item:
                    continue  # Skip if not found in epub

                image_bytes = matched_item.get_content()
                logging.warning(f"Image bytes length for {matched_item.file_name}: {len(image_bytes) if image_bytes else 'None'}")
                image_path = f"{image_dir}image_{currentImageCounter}.png"
                
                
                
                if image_bytes:
                # Check for duplicate in directory
                    if not is_image_duplicate(image_bytes, image_dir):
                        # Save new image and update src
                        try:
                            with open(image_path, "wb") as f:
                                logging.warning(f"Saving image {currentImageCounter} to {image_path}")
                                f.write(image_bytes)
                                img['src'] = f"images/image_{currentImageCounter}.png"
                                currentImageCounter += 1
                                logging.warning(f"Image {currentImageCounter} saved successfully.")
                        except Exception as e:
                            errorText=f"Failed to write image bytes to file. Function extract_chapter_from_book Error: {e}"
                            write_to_logs(errorText)
                            continue
                    else:
                        # If duplicate, find the existing image index to point to
                        # Loop through files to find the match and set src accordingly
                        for idx, file in enumerate(sorted(os.listdir(image_dir))):
                            file_path = os.path.join(image_dir, file)
                            epub_img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                            existing_img = Image.open(file_path).convert("RGB")
                            try:
                                if epub_img.size == existing_img.size:
                                    diff = ImageChops.difference(epub_img, existing_img)
                                    logging.warning(f"Comparing {file} with epub image.")
                                    if not diff.getbbox():
                                        logging.warning(f"Duplicate image found: {file}. Updating src.")
                                        img['src'] = f"images/{file}"
                                        break
                            except Exception:
                                continue
                else:
                    # If image_bytes is invalid, remove the image from the chapter content
                    logging.warning(f"Invalid image bytes for {matched_item.file_name}. Removing image from chapter content.")
                    img.decompose()
                    continue
            
            #logging.warning(f"Chapter Title: {title}")


            logging.warning(f"Chapter Title: {title}")
            fileTitle= f"{bookTitle} - {chapterID} - {sanitize_title(title)}"
            logging.warning(f"File Title: {fileTitle}")
            
            #Temporary method. Do not keep.
            def store_chapter(content, bookTitle, chapterTitle, chapterID):
                try:
                    # Check if the folder for the book exists
                    bookDirLocation = "./books/raw/" + bookTitle
                    if not check_directory_exists(bookDirLocation):
                        make_directory(bookDirLocation)

                    # Check if the chapter already exists
                    title = f"{bookTitle} - {chapterID} - {chapterTitle}"
                    dirLocation = f"./books/raw/{bookTitle}/{title}.html"
                    #logging.warning(dirLocation)

                    if check_directory_exists(dirLocation):
                        return

                    # Write the chapter content to the file with UTF-8 encoding
                    chapterDirLocation = "./books/raw/" + bookTitle + "/"
                    completeName = os.path.join(chapterDirLocation, f"{title}.html")
                    with open(completeName, "w", encoding="utf-8") as f:
                        if not isinstance(content, str):
                            content = content.decode("utf-8")  # Decode bytes to string if necessary
                        f.write(content)
                except Exception as e:
                    errorText=f"Storing chapter failed. Function store_chapter Error: {e}"
                    write_to_logs(errorText)
            
            
            store_chapter(str(chapterContent), bookTitle, sanitize_title(title), chapterID)
            chapter_metadata.append([chapterID, f"imported from epub, {sanitize_title(title)}",f"./books/raw/{bookTitle}/{fileTitle}.html"])
            chapterID+=1
    
    # if len(chapter_metadata) > 20:
    #     logging.warning(
    #         f"Merged chapters (showing first 5 and last 5 of {len(chapter_metadata)}):\n"
    #         f"{chapter_metadata[:5]} ... {chapter_metadata[-5:]}"
    #     )
    # else:
    #     logging.warning(chapter_metadata)          
    
    
    def merge_chapter_lists_preserve_order(list1, list2):
        """
        Merge two lists of chapters, preserving order and removing duplicates.
        Duplicates are detected by chapter title (case-insensitive, stripped).
        Returns a merged list with unique chapters, order: all from list1, then unique from list2.
        """
        def chapter_key(chapter):
            # chapter_metadata is saved as [ID, Title, FilePath]
            # We assume the title is always at index 1, and it can be a list
            if isinstance(chapter, list):
                return chapter[2].strip().lower()
            return chapter.strip().lower()

        seen = set()
        merged = []
        chapterID=0
        # Add all chapters from list1, marking them as seen
        for chapter in list1:
            key = chapter_key(chapter)
            if key not in seen:
                merged.append(chapter)
                seen.add(key)
                chapterID+=1

        # Add only new chapters from list2
        for chapter in list2:
            key = chapter_key(chapter)
            if key not in seen:
                # If chapter is a list, preserve its structure, but update the ID
                if isinstance(chapter, list) and len(chapter) == 3:
                    merged.append([chapterID, chapter[1], chapter[2]])
                else:
                    merged.append(chapter)
                seen.add(key)
                chapterID += 1
        logging.warning(merged)
        return merged
    
    merged_chapter_metadata=merge_chapter_lists_preserve_order(existingChapters, chapter_metadata)
    #logging.warning(merged_chapter_metadata)
    def write_order_of_contents(chapter_metadata, file_location):
        #logging.warning(chapter_metadata)
        mode = "w"
        with open(file_location, mode, encoding="utf-8") as f:
            for data in chapter_metadata:
                if isinstance(data, str):
                    data = data.strip().split(";")
                f.write(";".join(map(str, data)) + "\n")
    
    if len(merged_chapter_metadata) > 20:
        logging.warning(
            f"Merged chapters (showing first 5 and last 5 of {len(merged_chapter_metadata)}):\n"
            f"{merged_chapter_metadata[:5]} ... {merged_chapter_metadata[-5:]}"
        )
    else:
        logging.warning(merged_chapter_metadata)
    write_order_of_contents(merged_chapter_metadata,f"./books/raw/{bookTitle}/order_of_chapters.txt")
    
    #Create directory for the book
    #make_directory(f"./books/imported/{bookTitle}")



def is_image_duplicate(epub_image_bytes, directory):
    """
    Compare the given image bytes with all images in the directory.
    Returns True if a duplicate is found, False otherwise.
    """
    try:
        epub_img = Image.open(io.BytesIO(epub_image_bytes)).convert("RGB")
    except Exception as e:
        # If the image can't be opened, treat as new
        return False
    try:
        for file in os.listdir(directory):
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                file_path = os.path.join(directory, file)
                try:
                    dir_img = Image.open(file_path).convert("RGB")
                    # Compare size first for speed
                    if epub_img.size != dir_img.size:
                        continue
                    diff = ImageChops.difference(epub_img, dir_img)
                    if not diff.getbbox():
                        return True  # Duplicate found
                except Exception:
                    continue
        return False
    except Exception as e:
        errorText=f"Failed to compare images in directory {directory}. Function is_image_duplicate Error: {e}"
        logging.error(errorText)
        write_to_logs(errorText)
        return False # No duplicate found


def get_prefix_from_origin(origin):
    """
    Returns the correct prefix for a given origin.
    """
    origin_prefix_map = {
        "royalroad.com": "rr",
        "scribblehub.com": "sb",
        "forums.spacebattles.com": "sb",
        "novelbin.me": "nb",
        "foxaholic.com": "fx",
        "Unknown": "un"
    }
    # Normalize origin to lower-case for matching
    return origin_prefix_map.get(str(origin).lower(), "un")


        
def ensure_bookid_prefix(bookID, prefix):
    """
    Ensures the bookID starts with one of the valid prefixes ('rr', 'sb', 'fx').
    If not, prepends the given prefix.
    """
    valid_prefixes = ("rr", "sb", "fx","nb","un")
    if any(bookID.startswith(p) for p in valid_prefixes):
        return bookID
    return f"{prefix}{bookID}"

def merge_book_entries(existing, new):
            """
            Merge two book records (dicts), preferring valid data from 'existing'.
            If 'existing' has an empty string, None, "N/A", or "Unknown", use the value from 'new'.
            """
            merged = {}
            invalid_values = ("", None, "N/A", "Unknown")
            for key in set(existing.keys()).union(new.keys()):
                old_val = existing.get(key, "")
                new_val = new.get(key, "")
                # Special handling for bookID
                if key == "bookID":
                # If old is 'un...' and new is not, use new
                    if str(old_val).startswith("un") and not str(new_val).startswith("un") and new_val:
                        merged[key] = new_val
                    else:
                        merged[key] = old_val if old_val not in invalid_values else new_val
                else:
                    merged[key] = old_val if old_val not in invalid_values else new_val
                # Use old value if it's not in invalid_values, otherwise use new value
                merged[key] = old_val if old_val not in invalid_values else new_val
            return merged

async def import_main_interface(fileName):
    try:
        logging.warning(f"Processing file: {fileName}")
        dirLocation=f"./books/imported/epubs/{fileName}"

        match=await compare_existing_with_import(dirLocation)
        bookTitle=None
        if match[0]:
            logging.warning("Found matching entry:")
            logging.warning(match[1])
            bookTitle=match[1]
        else:
            bookTitle=fileName
        logging.warning(f"Calling fetch_novel_data_from_epub with: {fileName}")
        book=await fetch_novel_data_from_epub(f"./books/imported/epubs/{fileName}")
        logging.warning(f"fetch_novel_data_from_epub returned: {book} (type: {type(book)})")
        
        #logging.warning(await fetch_novel_data_from_epub(f"./books/imported/epubs/{fileName}"))
        bookID=book["bookID"]
        if not bookTitle:
            bookTitle=book["bookTitle"]
        bookAuthor=book["bookAuthor"]
        bookDescription=book["bookDescription"]
        origin=book["origin"]
        lastScraped=book["lastScraped"]
        latestChapterTitle=book["latestChapterTitle"]
        try:
            await extract_from_epub(f"./books/imported/epubs/{fileName}", bookTitle)
        except Exception as e:
            errorText=f"Failed to extract from epub. Function import_main_interface Error: {e}, file:{fileName}"
            logging.error(errorText)
            write_to_logs(errorText)
            return    
        
        first,last,total=get_first_last_chapter(bookTitle)
            
        directory = create_epub_directory_url(bookTitle)
        
        prefix=get_prefix_from_origin(origin)
        
        bookID=ensure_bookid_prefix(bookID, prefix)
        
        

        existing_entry= get_Entry_Via_Title(match[1])
        bestmatch,bookScore=fuzzy_similarity(bookTitle, match[1])
        if bookScore < 0.9:
            aliases = [bookTitle]
        else:
            aliases = []
        if existing_entry and "aliases" in existing_entry and isinstance(existing_entry["aliases"], list):
            # Only add if not already present
            if bookScore < 0.9 and bookTitle not in existing_entry["aliases"]:
                aliases = existing_entry["aliases"] + [bookTitle]
            else:
                aliases = existing_entry["aliases"]
        
        new_entry = {
            "bookID": bookID,
            "bookName": match[1],
            "bookAuthor": bookAuthor,
            "bookDescription": bookDescription,
            "websiteHost": origin,
            "firstChapter": first,
            "lastChapterID": last,
            "lastChapterTitle": latestChapterTitle,
            "lastScraped": lastScraped,
            "totalChapters": total,
            "directory": directory,
            "imported": True,
            "edited": False,
            "aliases": aliases
        }        
        if existing_entry:
            merged_entry = merge_book_entries(existing_entry, new_entry)
        else:
            merged_entry = new_entry
            
        create_Entry(
            bookID=merged_entry["bookID"],
            bookName=merged_entry["bookName"],
            bookAuthor=merged_entry["bookAuthor"],
            bookDescription=merged_entry["bookDescription"],
            websiteHost=merged_entry["websiteHost"],
            firstChapter=merged_entry["firstChapter"],
            lastChapterID=merged_entry["lastChapterID"],
            lastChapterTitle=merged_entry["lastChapterTitle"],
            lastScraped=merged_entry["lastScraped"],
            totalChapters=merged_entry["totalChapters"],
            directory=merged_entry["directory"],
            imported = True,
            edited = False,
            aliases=merged_entry["aliases"]
        )
        
        
        check1=check_existing_imported_book_via_title(merged_entry["bookName"])
        check2= check_existing_imported_book_via_ID(merged_entry["bookID"])

        if check1 or check2:
            update_imported_book_record({
                "bookID": merged_entry["bookID"],
                "bookName": merged_entry["bookName"],
                "bookAuthor": merged_entry["bookAuthor"],
                "fileName": fileName
            })
        else:
            create_imported_book_record({
                "bookID": merged_entry["bookID"],
                "bookName": merged_entry["bookName"],
                "bookAuthor": merged_entry["bookAuthor"],
                "fileName": fileName
            })
        
    except Exception as e:
        errorText=f"Function import_main_interface Error: {e}, file:{fileName}"
        logging.error(errorText)
        write_to_logs(errorText)

async def import_all_main_interface():
    dir_list=get_epubs_to_import()
    logging.warning(f"Files to import: {dir_list}")
    matches=await compare_all_epubs_in_dir_with_existing(dir_list, True)
    #Second parameter dictates whether we receive a list of matching books
    #or a list of non-matching books, with matching being with existing books in the database.
    for fileName in dir_list:
        logging.warning(f"Processing file: {fileName}")
        #logging.warning(await fetch_novel_data_from_epub(f"./books/imported/epubs/{fileName}"))
        book = await fetch_novel_data_from_epub(f"./books/imported/epubs/{fileName}")
        bookID = book["bookID"]
        bookTitle = book["bookTitle"]
        bookAuthor = book["bookAuthor"]
        bookDescription = book["bookDescription"]
        origin = book["origin"]
        lastScraped = book["lastScraped"]
        latestChapterTitle = book["latestChapterTitle"]
        
        await extract_from_epub(f"./books/imported/epubs/{fileName}")
        
        first,last,total=get_first_last_chapter(bookTitle)
        
        directory = create_epub_directory_url(bookTitle)
        
        
        prefix=get_prefix_from_origin(origin)
        
        bookID=ensure_bookid_prefix(bookID, prefix)
        
        existing_entry= get_Entry_Via_Title(bookTitle)
        
        new_entry = {
            "bookID": bookID,
            "bookName": bookTitle,
            "bookAuthor": bookAuthor,
            "bookDescription": bookDescription,
            "websiteHost": origin,
            "firstChapter": first,
            "lastChapterID": last,
            "lastChapterTitle": latestChapterTitle,
            "lastScraped": lastScraped,
            "totalChapters": total,
            "directory": directory,
            "imported": True,
            "edited": False
        }        
        if existing_entry:
            merged_entry = merge_book_entries(existing_entry, new_entry)
        else:
            merged_entry = new_entry
        create_Entry(
            bookID=merged_entry["bookID"],
            bookName=merged_entry["bookName"],
            bookAuthor=merged_entry["bookAuthor"],
            bookDescription=merged_entry["bookDescription"],
            websiteHost=merged_entry["websiteHost"],
            firstChapter=merged_entry["firstChapter"],
            lastChapterID=merged_entry["lastChapterID"],
            lastChapterTitle=merged_entry["lastChapterTitle"],
            lastScraped=merged_entry["lastScraped"],
            totalChapters=merged_entry["totalChapters"],
            directory=merged_entry["directory"],
            imported = True,
            edited = False
        )

        check1=check_existing_imported_book_via_title(merged_entry["bookName"])
        check2= check_existing_imported_book_via_ID(merged_entry["bookID"])

        if check1 or check2:
            update_imported_book_record({
                "bookID": merged_entry["bookID"],
                "bookName": merged_entry["bookName"],
                "bookAuthor": merged_entry["bookAuthor"],
                "fileName": fileName
            })
        else:
            create_imported_book_record({
                "bookID": merged_entry["bookID"],
                "bookName": merged_entry["bookName"],
                "bookAuthor": merged_entry["bookAuthor"],
                "fileName": fileName
            })
        # if fileName.endswith('.epub'):
        #     dirLocation= f"./books/imported/epubs/{fileName}"
        #     logging.warning(f"Extracting from file: {fileName}")
        #     await extract_chapter_from_book(dirLocation)
        # else:
        #     logging.warning(f"Skipping non-epub file: {fileName}")

#asyncio.run(importing_main_interface())
#compare_images()
#asyncio.run(extract_chapter_from_book("./books/imported/epubs/DRR 4 - Paradoxical Ties - Silver Linings.epub"))


#TODO: Create a function to import all epubs within a folder, and merge the results into existing directories
#TODO: This means I need to check if the title corresponds to a book that exists inside the database.
#TODO: I will probably have to add another record to the database like 'aliases' or 'alternative_titles'
#TODO: The merging will need to consider if an existing chapter title matches the extracted chapter title.
#TODO: If it does, then to save space, we should not let it be imported.


# async def check_for_already_imported(bookName):
    