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
from scrapers.FoxaholicScraper import FoxaholicScraper
from common import(
    store_chapter,
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


class FoxaholicEpubProducer(EpubProducer):
    #This grabs the first digit in the URL to treat as the ChapterID
    def extract_chapter_ID(self, chapter_url):
        chapterID=chapter_url.split("/")
        chapterID=chapterID[len(chapterID)-2]
        chapterID=re.search(r'\d+',chapterID).group()
        return chapterID

    async def produce_custom_epub(self, new_epub, book_title, css, book_chapter_urls, mainBookURL, additionalConditions):
        pass
