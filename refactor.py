

#TODO: Create a epub function that generates from links, and existing file retrievals if link isn't available

#https://github.com/aerkalov/ebooklib/issues/194
#Do this to embed images into the epub.
#Will need to have a counter as the html files are being stored.
#So that image_01 -> image_02 -> image_03
#DONE #Will also need to replace the src="link here" to src="images/image_01.png" while chapters are being stored.
#DONE #Will need to store the images into the raw epub folder.
#DONE #Will need to add_item(image_01) into the epub each time.

#DONE Will need to write a css sheet for tables.
#DONE Set base text to black
#DONE Set table text to white







#: DONE Fuzzy search for if input is not link. If input is Title, send query, get results.
#API:https://www.royalroad.com/fictions/search?globalFilters=false&title=test&orderBy=popularity
#https://www.royalroad.com/fictions/search?globalFilters=false&title=test
#Two versions. Popularity, and Relevance.
#Relevance to get best possible match.
#Popularity for when results have similar names.


#div class="fiction-list"
#div class= "row fiction-list-item"
#h2 class="fiction-title"
#a href format="/fiction/#####/title"





import bs4
import re
import os, errno
import datetime
import logging
import asyncio
import io
from word2number import w2n

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
    update_entry
)



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

# When creating the driver:
#driver = webdriver.Firefox(options=firefox_options)
#driver.install_addon(path_to_extension, temporary=True)





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
    










#available additionalConditions for search-filter
#&t=post&c[child_nodes]=1&c[nodes][0]=18 is for forum: Creative Writing
#&c[title_only]=1 is for title only search
#https://forums.spacebattles.com/forums/creative-writing.18/?tags[0]=trails+series&nodes[0]=48&nodes[1]=169&nodes[2]=115
#tag searching: ?tags[0]=trails+series
#forums: &nodes[0]=48&nodes[1]=169&nodes[2]=40&nodes[3]=115
#48 is original writing, 169 is unlisted original fiction, 40 is creative writing archives, and 115 is worm.
#word count filters: &min_word_count=1000&max_word_count=1000000
#sort by options:
#order=title, reply_count,view_count, last_threadmark, watchers
#&direction=desc/asc
#threadmark status
#&threadmark_index_statuses[0]=incomplete
#&threadmark_index_statuses[1]=complete
#&threadmark_index_statuses[2]=hiatus

#available additionalConditions for search-search
#https://forums.spacebattles.com/search/104096825/?q=Trails+Of&t=post&c[child_nodes]=1&c[nodes][0]=18&c[title_only]=1&o=date
#&c[container_only]=1
#&c[gifts_only]=1 (0/1 False/True)
#&c[tags]=word1+word2
#&c[threadmark_only]=1
#&c[title_only]=1
#&c[users]=String_Name

#asyncio.run(test("https://forums.spacebattles.com/threads/quahinium-industries-shipworks-kancolle-si.1103320/reader/"))



# result=asyncio.run(spacebattles_search_interface("Trails Of", "date", {
#     "c[container_only]": 0,
#     "c[gifts_only]": 0,
#     "c[tags]": "",
#     "c[threadmark_only]": 0,
#     "c[title_only]": 1,
#     "c[users]": ""
# }))

# result = asyncio.run(spacebattles_search_interface("Trails series", "", "" ,{
#     "min_word_count": 5000,
#     "threadmark_index_statuses[0]":"incomplete",
#     "threadmark_index_statuses[1]":"complete"}))

# logging.warning(result)


















