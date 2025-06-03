import re
import os, errno
import datetime
from novel_template import NovelTemplate
import logging
from ebooklib import epub 
from PIL import Image

from mongodb import (
    check_existing_book_Title,
    get_Entry_Via_Title,
    get_Total_Books,
)



basicHeaders={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
}

cloudflare_cookie=''




def setCookie(newCookie):
    global cookie
    cookie=newCookie

def interception (request):
    del request.headers['User-Agent']
    del request.headers['Accept']
    del request.headers['Accept-Language']
    del request.headers['Accept-Encoding']
    del request.headers['Cookie']
    
    request.headers['User-Agent']=basicHeaders["User-Agent"]
    request.headers['Accept']=basicHeaders["Accept"]
    request.headers['Accept-Language']=basicHeaders["Accept-Language"]
    request.headers['Accept-Encoding']=basicHeaders["Accept-Encoding"]
    request.headers['Cookie']=cloudflare_cookie["Cookie"]



logLocation=os.getenv("logs")
def write_to_logs(log):
    todayDate=datetime.datetime.today().strftime('%Y-%m-%d')
    log = datetime.datetime.now().strftime('%c') +" "+log+"\n"
    fileLocation=f"{logLocation}/{todayDate}"
    if (check_directory_exists(fileLocation)):
        f=open(fileLocation,"a")
        f.write(log)
    else:
        f=open(fileLocation,'w')
        f.write(log)



def check_directory_exists(path):
    if os.path.exists(path):
        return True
    return False
        
def make_directory(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno!=errno.EEXIST:
            errorText=f"Failed to make directory. Function make_directory. Error: {e}"
            write_to_logs(errorText)
            return



def remove_non_english_characters(text):
    invalid_chars='【】'
    for char in invalid_chars:
        text=text.replace(char,'')
    text = re.sub(r'\s+', ' ', text)
    result = re.search(r'([A-Za-z0-9,!\'\-]+( [A-Za-z0-9,!\'\-]+)+)', text)
    #logging.warning(result)
    if not result:
        return text
    return result.group() 

def remove_invalid_characters(inputString):
    invalid_chars = '.-<>:;"/\\|?*()'
    for char in invalid_chars:
        inputString=inputString.replace(char,' ')
#    inputString=re.sub(r"[\(\[].*?[\)\]]", "", inputString)
    inputString=remove_non_english_characters(inputString)
    return inputString.strip()

def remove_tags_from_title(inputString):
    invalid_chars = '.-<>:;"/\\|?*'
    for char in invalid_chars:
        inputString=inputString.replace(char,' ')
    inputString=re.sub(r"[\(\[].*?[\)\]]", "", inputString)
    inputString=remove_non_english_characters(inputString)
    return inputString.strip()

def check_if_chapter_exists(chapterID,savedChapters):
    if (savedChapters is False):
        return False
    for chapter in savedChapters:
        if chapterID in chapter:
            return True
    return False


def retrieve_stored_image(imageDir):
    try:
        if os.path.exists(imageDir):
            return Image.open(imageDir)
        else:
            #logging.warning(f"Image file not found: {imageDir}")
            errorText=f"Image file not found: {imageDir}"
            write_to_logs(errorText)
    except Exception as e:
        errorText=f"Failed to retrieve image. Function retrieve_stored_image. Error: {e}"
        write_to_logs(errorText)
    return None


def retrieve_cover_from_storage(bookTitle):
    dirLocation=f"./books/raw/{bookTitle}/cover_image.png"
    if os.path.exists(dirLocation):
        try:
            return Image.open(dirLocation)
        except Exception as e:
            errorText=f"Failed to retrieve cover image. Function retrieve_cover_from_storage. Error: {e}"
            write_to_logs(errorText)
            return None
    errorText=f"Cover image does not exist. Function retrieve_cover_from_storage."
    write_to_logs(errorText)
    return None

def storeEpub(bookTitle,new_epub):
    try:
        dirLocation="./books/epubs/"+bookTitle
        if not check_directory_exists(dirLocation):
            make_directory(dirLocation)
        
        dirLocation="./books/epubs/"+bookTitle+"/"+bookTitle+".epub"
        if (check_directory_exists(dirLocation)):
            os.remove(dirLocation)
        epub.write_epub(dirLocation,new_epub)
    except Exception as e:
        errorText=f"Error with storing epub. Function store_epub. Error: {e}"
        write_to_logs(errorText)
    

def store_chapter(content, bookTitle, chapterTitle, chapterID):
    try:
        # Remove invalid characters from file name
        bookTitle = remove_invalid_characters(bookTitle)
        chapterTitle = remove_invalid_characters(chapterTitle)
        #logging.warning(content)
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



def update_existing_order_of_contents(bookTitle,chapterList):
    try:
        bookDirLocation=f"./books/raw/{bookTitle}"
        if not (check_directory_exists(bookDirLocation)):
            make_directory(bookDirLocation)
        fileLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
        if (os.path.exists(fileLocation)):
            f=open(fileLocation,"w")
        else:
            f=open(fileLocation,"x")
            
        try:
            for line in chapterList:
                f.write(str(line)) #FORMATTING IS FUCKED
        except Exception as e:
            errorText=f"Updating order of contents failed. Function update_existing_order_of_contents Error: {e}"
            write_to_logs(errorText)
        finally:
            f.close()
    except Exception as e:
        errorText=f"Updating order of contents failed. Function update_existing_order_of_contents Error: {e}"
        write_to_logs(errorText)
        
    
def append_order_of_contents(bookTitle,chapterData):
    logging.warning(chapterData)
    fileLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
    if (os.path.exists(fileLocation)):
        f=open(fileLocation,"a")
        f.write('\n')
        for dataLine in chapterData:
            chapterID=dataLine[0]
            chapterLink=dataLine[1]
            chapterTitle=dataLine[2]
            f.write(chapterID+";"+chapterLink+";"+chapterTitle+"\n")
    f.close()
    
def generate_new_ID(bookTitle):
    try:
        if (check_existing_book_Title(bookTitle)):
            bookData=get_Entry_Via_Title(bookTitle)
            if bookData:
                return bookData["bookID"]
        return get_Total_Books()+1
    except Exception as e:
        errorText=f"Generate new id failed. Function generate_new_ID Error: {e}"
        write_to_logs(errorText)








def create_epub_directory_url(bookTitle):
    dirLocation="./books/epubs/"+bookTitle+"/"+bookTitle+".epub"
    return dirLocation

def is_empty(chapterList):
    if not chapterList:
        return True
    return False

def get_first_last_chapter(bookTitle):
    dirLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
    if (check_directory_exists(dirLocation)):
        f= open(dirLocation,"r")
        lines=f.readlines()
        f.close()
    else:
        return -1,-1,-1
    if is_empty(lines):
        return -1,-1,-1
    firstChapterID=lines[0].split(";")[0]
    lastChapterID=lines[len(lines)-1].split(";")[0]
    
    return firstChapterID,lastChapterID,len(lines)