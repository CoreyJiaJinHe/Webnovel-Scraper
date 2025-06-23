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

from . import ScraperFactory, Scraper, RoyalroadEpubProducer, FoxaholicEpubProducer, NovelBinEpubProducer, SpaceBattlesEpubProducer

# Add these missing imports:
from .common import (
    setCookie,
    check_existing_book_Title,
    get_first_last_chapter,
    remove_invalid_characters,
    create_epub_directory_url
)
from mongodb import create_Entry, create_latest

async def main_interface(url, cookie):
    try:
        if (cookie):
            setCookie(cookie)
        epub_producer = None
        if "royalroad.com" in url:
            epub_producer = RoyalroadEpubProducer()
        elif "foxaholic.com" in url:
            epub_producer = FoxaholicEpubProducer()
        elif "novelbin.com" in url or "novelbin.me" in url:
            epub_producer= NovelBinEpubProducer()
        elif "spacebattles.com" in url:
            epub_producer=SpaceBattlesEpubProducer()
            normalized_url = url if url.endswith('/') else url + '/'
            if re.search(r'/reader/page-\d+/$',normalized_url):
                url = re.sub(r'/reader/page-\d+/?$', '/reader/', url)
            elif not url.rstrip('/').endswith('/reader'):
                if url.endswith('/'):
                    url += 'reader/'
                else:
                    url += '/reader/'
        else:
            raise ValueError("Unsupported website")
        logging.warning(url)
        logging.warning('Creating scraper')
        scraper=ScraperFactory.get_scraper(url)
        logging.warning('Fetching novel data')
        bookID,bookTitle,bookAuthor,description,lastScraped,latestChapter= await scraper.fetch_novel_data(url)
        
        
        
        new_epub=epub.EpubBook()
        new_epub.set_identifier(bookID)
        new_epub.set_title(bookTitle)
        new_epub.set_language('en')
        new_epub.add_author(bookAuthor)
        style=open("style.css","r").read()
        default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)
        new_epub.add_item(default_css)
        
        
        #if (check_existing_book(bookID) or check_existing_book_Title(bookTitle)):
            #if not (check_latest_chapter(bookID,bookTitle,latestChapter)):
                #pass
        logging.warning('Producing epub')
        logging.warning(url)
        await epub_producer.produce_epub(url, bookTitle,default_css,new_epub)
        rooturl=""
        match = re.search(r"https://(?:www\.)?([A-Za-z0-9.-]+)", url)
        if match:
            rooturl=match.group(1)
        first,last,total=get_first_last_chapter(bookTitle)
        
        bookID=int(remove_invalid_characters(bookID))
        directory = create_epub_directory_url(bookTitle)
        create_Entry(
            bookID=bookID,
            bookName=bookTitle,
            bookAuthor=bookAuthor,
            bookDescription=description,
            websiteHost=rooturl,
            firstChapter=first,
            lastChapter=last,
            totalChapters=total,
            directory=directory
        )
        
        create_latest(
            bookID=int(bookID),
            bookName=bookTitle,
            bookAuthor=bookAuthor,
            bookDescription=description,
            websiteHost=rooturl,
            firstChapter=first,
            lastChapter=last,
            totalChapters=total,
            directory=directory
        )
        
        return directory
    
    
    except ValueError as e:
        logging.error(f"Error: {e}")
        
        
#royalroad cookie: .AspNetCore.Identity.Application


specialHeaders={
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-CA,en-US;q=0.7,en;q=0.3",
    "Accept-Encoding": "gzip, deflate, br",
    "cookie":rrcookie
}

async def specialSoup(url, specialHeaders):
    async with aiohttp.ClientSession(headers = specialHeaders) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = bs4.BeautifulSoup(html, 'html.parser')
                    return soup

async def retrieve_from_royalroad_follow_list():
    soup=await specialSoup("https://www.royalroad.com/my/follows", specialHeaders)
    bookTitles=soup.find_all("h2",{"class":"fiction-title"})
    bookLinks=[]
    for title in bookTitles:
        a_tag = title.find("a")
        if a_tag and "href" in a_tag.attrs:
            bookLinks.append(f"https://www.royalroad.com{a_tag["href"]}")
    logging.warning(bookLinks)
    for link in bookLinks:
        logging.warning(await main_interface(link))
    