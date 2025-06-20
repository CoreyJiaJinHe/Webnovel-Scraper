from pymongo import MongoClient
import os
import logging
import bs4
from dotenv import load_dotenv, find_dotenv
import re

env_path = find_dotenv()
load_dotenv(env_path, override=True)


MONGODB_URL=os.getenv('MONGODB_URI')
myclient=MongoClient(MONGODB_URL)
mydb=myclient["BotServers"]
botServers=mydb["Servers"]
from utils import write_to_logs

class Database:
    _instance = None

    @staticmethod
    def get_instance():
        if Database._instance is None:
            MONGODB_URL = os.getenv('MONGODB_URI')
            Database._instance = MongoClient(MONGODB_URL)["Webnovels"]
        return Database._instance


def get_existing_order_of_contents(book_title):
            # Default implementation
            dir_location = f"./books/raw/{book_title}/order_of_chapters.txt"
            if os.path.exists(dir_location):
                with open(dir_location, "r") as f:
                    return f.readlines()
            return []
def get_chapter_contents_from_saved(dir_location):
            #logging.warning(f"Retrieving chapter from {dir_location}")
            with open(dir_location, "r") as f:
                return f.read()
        
def get_chapter_from_saved(chapter_id, saved_chapters):
            for chapter in saved_chapters:
                chapter = chapter.split(";")
                if str(chapter_id) == str(chapter[0]):
                    return chapter[0], chapter[2].strip()
            return None, None
        

def get_chapter_list(bookID):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID": bookID})
    order_of_contents = []
    bookTitle=results["bookName"]
    if results:
        already_saved_chapters=get_existing_order_of_contents(bookTitle)
        for chapter in already_saved_chapters:
            chapterData=chapter.split(";")
            chapterID=chapterData[0]
            dirLocation=chapterData[2].strip()
            
            file_name = dirLocation.split('/')[-1]

            name = file_name.replace('.html', '').strip()
            idx = name.lower().find("chapter")
            if idx != -1:
                name= name[idx:].strip()
            #logging.warning(name)
            
            # If "Extra" is present, extract from "Extra" onward and prepend "Chapter "
            extra_idx = name.lower().find("extra")
            if extra_idx != -1:
                name = "Chapter " + name[extra_idx:].strip()
            else:
                # Existing logic for "Chapter"
                idx = name.lower().find("chapter")
                if idx != -1:
                    name = name[idx:].strip()

            # (Optional: Remove duplicate "Chapter" if present)
            if name.lower().startswith("chapter chapter"):
                name = name[8:].strip()
            
            chapterTitle=name
            
            order_of_contents.append(f"{chapterID};{dirLocation};{chapterTitle}")
        
        
        
        return order_of_contents
    else:
        logging.warning(f"Book with ID {bookID} not found in the database.")
        return None

def get_chapter_list_spacebattles(bookID):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID": bookID})
    bookTitle=results["bookName"]
    logging.warning(f"Book title: {bookTitle}")
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    logging.warning(f"Already saved chapters: {len(already_saved_chapters)}")
    logging.warning(already_saved_chapters)
    if already_saved_chapters:
        order_of_contents=[]
        for pageNum in range(1,len(already_saved_chapters)+1):
            chapter_id,dirLocation=get_chapter_from_saved(pageNum,already_saved_chapters)
            
            page_content=get_chapter_contents_from_saved(dirLocation)
            
            page_soup=bs4.BeautifulSoup(page_content,'html.parser')
            all_chapters=page_soup.find_all('div',{'id':'chapter-start'})
            for chapter in all_chapters:
                chapter_title=chapter.find('title').text.strip()
                if chapter_title:
                    order_of_contents.append(f"{chapter_id};{dirLocation};{chapter_title}")
        return order_of_contents
    else:
        logging.warning(f"Book with ID {bookID} not found in the database.")
        return None

def get_stored_chapter(bookID,chapterID):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID": bookID})
    bookTitle=results["bookName"]
    
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    
    chapter_id,dirLocation=get_chapter_from_saved(chapterID,already_saved_chapters)

    page_content = get_chapter_contents_from_saved(dirLocation)
    soup = bs4.BeautifulSoup(page_content, 'html.parser')
    for img in soup.find_all('img'):
        src = img.get('src', '')
        if not src.lower().startswith('http'):
            if not ('/' in src or '\\' in src):
                img['src'] = f"/react/static/{bookTitle}/{src}"
            else:
                # If src is already a relative path, just prepend /static/
                # Remove leading './' or '/' from src
                clean_src = src.lstrip('./').lstrip('/')
                img['src'] = f"/react/static/{bookTitle}/{clean_src}"
    
    return str(soup)
    


#TODO: For image links, modify the src that is currently "images/image_XX.png" to "imageDirectory/images/image_XX.png"

def get_stored_chapter_spacebattles(bookID,pageID, chapterTitle):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID": bookID})
    bookTitle=results["bookName"]
    
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    
    chapter_id,dirLocation=get_chapter_from_saved(pageID,already_saved_chapters)

    page_content=get_chapter_contents_from_saved(dirLocation)
    
    page_soup=bs4.BeautifulSoup(page_content,'html.parser')
    for img in page_soup.find_all('img'):
        src = img.get('src', '')
        if not src.lower().startswith('http'):
            if not ('/' in src or '\\' in src):
                img['src'] = f"/react/static/{bookTitle}/{src}"
            else:
                # If src is already a relative path, just prepend /static/
                # Remove leading './' or '/' from src
                clean_src = src.lstrip('./').lstrip('/')
                img['src'] = f"/react/static/{bookTitle}/{clean_src}"
    
    all_chapters=page_soup.find_all('div',{'id':'chapter-start'})
    
    #logging.warning(type(all_chapters))
    # for chapterTitle in all_chapters:
    #     logging.warning(chapterTitle.text)
    matching_chapter = None
    for chapter in all_chapters:
        if chapterTitle.strip() in chapter.text.strip():
            matching_chapter = chapter
            break

    if matching_chapter:
        text = matching_chapter
    else:
        text = "Chapter not found"
    return text

# x=get_chapter_list_spacebattles(bookID="sb1076757")
# logging.warning(x)
# write_to_logs(str(x))
#get_stored_chapter_spacebattles(bookID="sb1076757", pageID="1", chapterTitle="The New Normal - 1-2")