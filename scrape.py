import bs4
import requests
import re
from pathlib import Path
from pymongo import MongoClient
import os, errno
import datetime
import logging
import asyncio
import io
from ebooklib import epub 
from PIL import Image
import aiohttp

from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
load_dotenv(env_path, override=True)

MONGODB_URL=os.getenv('MONGODB_URI')
myclient=MongoClient(MONGODB_URL)
mydb=myclient["Webnovels"]
savedBooks=mydb["Books"]

from scrapers.common import (
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

cookie=""

def write_to_logs(log):
    logLocation=os.getenv("LOGS",
        #os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
    )
    #Debugging purposes.
    # logging.warning(f"Log location: {logLocation}")
    
    # print("CWD:", os.getcwd())
    # print("LOGS env:", os.getenv("LOGS"))
    # print("logLocation:", logLocation)
    
    
    
    todayDate=datetime.datetime.today().strftime('%Y-%m-%d')
    log = datetime.datetime.now().strftime('%c') +" "+log+"\n"
    fileLocation=f"{logLocation}/{todayDate}.txt"
    logging.warning(f"Writing to log file: {fileLocation}")
    if (check_directory_exists(fileLocation)):
        f=open(fileLocation,"a")
    else:
        f=open(fileLocation,'w')
    f.write(log)
    f.close()
options={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
        "Accept-Encoding": "gzip, deflate, br",
        "Cookie": cookie
    }

def interception (request):
        del request.headers['User-Agent']
        del request.headers['Accept']
        del request.headers['Accept-Language']
        del request.headers['Accept-Encoding']
        #del request.headers['Referer']
        del request.headers['Cookie']
        
        request.headers['User-Agent']=options["User-Agent"]
        request.headers['Accept']=options["Accept"]
        request.headers['Accept-Language']=options["Accept-Language"]
        request.headers['Accept-Encoding']=options["Accept-Encoding"]
        #request.headers['Referer']=options["Referer"]
        request.headers['Cookie']=options["Cookie"]








def update_existing_order_of_contents(bookTitle,chapterList):
    bookDirLocation=f"./books/raw/{bookTitle}"
    if not (check_directory_exists(bookDirLocation)):
        make_directory(bookDirLocation)
    fileLocation=f"./books/raw/{bookTitle}/order_of_chapters.txt"
    if (os.path.exists(fileLocation)):
        f=open(fileLocation,"w")
    else:
        f=open(fileLocation,"x")
    for line in chapterList:
        f.write(str(line)) #FORMATTING IS FUCKED
    f.close()
    
    

#Cut out and insert function
#Take [range1:range2] from the chapterList and insert into position [insertRange1] of existingChapterList
def insert_into_Chapter_List(cutOutRange,insertRange,chapterList,existingChapterList):
    
    if (cutOutRange[0]<= cutOutRange[1]):
        logging.warning("Invalid range")
        return False
    if (cutOutRange[0] >=len(existingChapterList or cutOutRange[1]>=len(existingChapterList))):
        logging.warning("Out of bounds error")
        return False
    if (insertRange>=len(existingChapterList) or insertRange<0):
        logging.warning("Insert range out of bounds")
        return False
    if (existingChapterList):
        logging.warning("Existing chapter list is empty")
        return False
    
    #Get the desired chapters to cut out from "chapterList" of the new file to be inserted into the saved existingChapterList.
    cutOutChapters=chapterList[cutOutRange[0]:cutOutRange[1]]
    
    #Split the existing chapterList in half to insert
    firstHalfChapters=existingChapterList[0:insertRange]
    secondHalfChapters=existingChapterList[insertRange:]
    
    #Create new chapterlist, insert the cutout in
    newChapterList=list()
    newChapterList=firstHalfChapters+cutOutChapters+secondHalfChapters
    return newChapterList



        
def delete_from_Chapter_List(deleteRange,existingChapterList):
    if (deleteRange[0]<= deleteRange[1]):
        logging.warning("Invalid range")
        return False
    if (deleteRange[0] >=len(existingChapterList or deleteRange[1]>=len(existingChapterList))):
        logging.warning("Out of bounds error")
        return False
    
    cutOutChapters=existingChapterList[deleteRange[0]:deleteRange[1]]
    for item in cutOutChapters:
        existingChapterList.remove(item)
    newChapterList=existingChapterList
    return newChapterList
    





async def novelcool_get_chapter_list(novelURL):
    async with aiohttp.ClientSession(headers = basicHeaders
    ) as session:
        async with session.get(novelURL) as response:
            if response.status == 200:
                html = await response.text()
                soup = bs4.BeautifulSoup(html, 'html.parser')
                chapterTable = soup.find("div", {"class": "chapter-item-list"})
                rows= chapterTable.find_all("div", {"class":"chp-item"})
                chapterListURL=list()
                for row in rows[0:len(rows)]:
                    processChapterURL=row.find("a")["href"]
                    chapterURL=processChapterURL
                    chapterListURL.append(chapterURL)
                logging.warning(chapterListURL)      
                return chapterListURL
link="https://www.novelcool.com/novel/If-You-Could-Hear-My-Heart.html"



