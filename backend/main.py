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

from backend.epubproducers.RoyalRoadEpubProducer import RoyalRoadEpubProducer
from backend.epubproducers.FoxaholicEpubProducer import FoxaholicEpubProducer
from backend.epubproducers.NovelBinEpubProducer import NovelBinEpubProducer
from backend.epubproducers.SpaceBattlesEpubProducer import SpaceBattlesEpubProducer
from backend.scrapers.ScraperFactory import ScraperFactory


# Add these missing imports:
from backend.common import (
    get_first_last_chapter,
    remove_invalid_characters,
    create_epub_directory_url,
    write_to_logs,
)
from mongodb import create_Entry, create_latest, update_entry, check_existing_book, check_existing_book_Title, check_recently_scraped, check_latest_chapter


async def main_interface(url, cookie):
    try:
        scraper= ScraperFactory.create_scraper(url)
        if (scraper is None):
            errorText="Function main_interface. Error: Scraper is None. Please check the URL and try again."
            logging.warning(errorText)
            write_to_logs(errorText)
            return None
        
        if (cookie):
            scraper.setCookie(cookie)
        epub_producer = None
        if "royalroad.com" in url:
            epub_producer = RoyalRoadEpubProducer()
            prefix="rr"
        elif "spacebattles.com" in url:
            epub_producer=SpaceBattlesEpubProducer()
            prefix="sb"
            normalized_url = url if url.endswith('/') else url + '/'
            if re.search(r'/reader/page-\d+/$',normalized_url):
                url = re.sub(r'/reader/page-\d+/?$', '/reader/', url)
            elif not url.rstrip('/').endswith('/reader'):
                if url.endswith('/'):
                    url += 'reader/'
                else:
                    url += '/reader/'
        elif "foxaholic.com" in url:
            epub_producer = FoxaholicEpubProducer()
            prefix="fx"
            if (cookie is None):
                errorText="Function main_interface. Error: Cookie is required for Foxaholic. Please provide a cookie."
                logging.warning(errorText)
                write_to_logs(errorText)
                return None
        elif "novelbin.com" or "novelbin.me" in url:
            epub_producer = NovelBinEpubProducer()
            prefix="nb"
            if (cookie is None):
                errorText="Function main_interface. Error: Cookie is required for NovelBin. Please provide a cookie."
                logging.warning(errorText)
                write_to_logs(errorText)
                return None
        else:
            raise ValueError("Unsupported website")
        logging.warning(url)
        logging.warning('Fetching novel data')
        
        bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle, latestChapterID= await scraper.fetch_novel_data(url)
        
        style=open("style.css","r").read()
        default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)
        async def instantiate_new_epub(bookID,bookTitle,bookAuthor,default_css):
            try:
                new_epub=epub.EpubBook()
                new_epub.set_identifier(bookID)
                new_epub.set_title(bookTitle)
                new_epub.set_language('en')
                new_epub.add_author(bookAuthor)
                new_epub.add_item(default_css)
                return new_epub
            except Exception as e:
                errorText=f"Failed to create new_epub object. Error: {e}"
                write_to_logs(errorText)
                return
        bookID=remove_invalid_characters(bookID)
        new_epub=await instantiate_new_epub(bookID,bookTitle,bookAuthor,default_css)
        
        
        
        def ensure_bookid_prefix(bookID, prefix):
            """
            Ensures the bookID starts with one of the valid prefixes ('rr', 'sb', 'fx').
            If not, prepends the given prefix.
            """
            valid_prefixes = ("rr", "sb", "fx","nb")
            if any(bookID.startswith(p) for p in valid_prefixes):
                return bookID
            return f"{prefix}{bookID}"
        
        bookID=ensure_bookid_prefix(bookID, prefix)
        
        override = True
        #TODO: DONE If the book already exists, we should check if the latest chapter is the same as the one in the database.
        #To do this, I need to change the way latest chapters are stored in the database. I need to store the latest chapter's name and ID
        #and make the name be the one that is displayed on the front end, while using the ID to compare latest chapters
        if (override):
            await scraper.process_new_book(url, bookTitle)
            
        else:
            if (check_existing_book(bookID) or check_existing_book_Title(bookTitle)):
                logging.warning(f"Book {bookTitle} already exists in the database with ID {bookID}. Checking for new chapters.")
                if not (check_recently_scraped(bookID)):
                    logging.warning(f"Book {bookTitle} has not been scraped recently. Checking to see if latest is already stored.")
                    if not (check_latest_chapter(bookID,bookTitle,latestChapterTitle)):
                        logging.warning(f"Latest chapter {latestChapterTitle} is not the same as the one in the database. Processing new book.")
                        await scraper.process_new_book(url, bookTitle)
                    else:
                        logging.warning(f"Book {bookTitle} already exists in the database with the latest chapter {latestChapterTitle}. No new chapters to scrape.")
        
        #TODO: DONE I also need to modify SpacebattlesEpubProducer. Currently, the latest chapter is considered the last page of spacebattles reader mode.
        #Due to how spacebattles works, it does not check for new chapters added to the page. Meaning, I can store 5 threadmarks on last page, and the sixth won't be detected.
        #TODO: DONE I also need to modify all the EpubProducers to handle broken images so that it won't break the epub generation.
        
        await epub_producer.produce_epub(bookTitle,default_css,new_epub)
        rooturl=""
        
        match = re.search(r"https://(?:www\.)?([A-Za-z0-9.-]+)", url)
        if match:
            rooturl=match.group(1)
        first,last,total=get_first_last_chapter(bookTitle)
        
        directory = create_epub_directory_url(bookTitle)
        create_Entry(
            bookID=bookID,
            bookName=bookTitle,
            bookAuthor=bookAuthor,
            bookDescription=description,
            websiteHost=rooturl,
            firstChapter=first,
            lastChapterID=last,
            lastChapterTitle=latestChapterTitle,
            lastScraped=lastScraped,
            totalChapters=total,
            directory=directory,
            imported=False,
            edited=False
        )
        
        create_latest(
            bookID="-1",
            bookName=bookTitle,
            bookAuthor=bookAuthor,
            bookDescription=description,
            websiteHost=rooturl,
            firstChapter=first,
            lastChapterID=last,
            lastChapterTitle=latestChapterTitle,
            lastScraped=lastScraped,
            totalChapters=total,
            directory=directory,
            imported=False,
            edited=False
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





async def search_page(input: str, selectedSite: str, searchConditions:dict, cookie):
    try:
        scraper= ScraperFactory.create_scraper(selectedSite)
    except ValueError as e:
        errorText="Unsupported website. Please check the URL and try again."
        logging.warning(errorText)
        write_to_logs(errorText)
        return None
    
    if "foxaholic" in selectedSite:
        if (cookie is None):
            errorText="Function search_page. Error: Cookie is required for Foxaholic. Please provide a cookie."
            logging.warning(errorText)
            write_to_logs(errorText)
            return None
    elif "novelbin" in selectedSite:
        if (cookie is None):
            errorText="Function search_page. Error: Cookie is required for NovelBin. Please provide a cookie."
            logging.warning(errorText)
            write_to_logs(errorText)
            return None
    if (cookie):
        scraper.setCookie(cookie)
    
    url_pattern = re.compile(r'^(https?://|www\.)', re.IGNORECASE)
    if url_pattern.match(input.strip()):
        url=input
        if "spacebattles" in selectedSite:
            normalized_url = url if url.endswith('/') else url + '/'
            if re.search(r'/reader/page-\d+/$',normalized_url):
                url = re.sub(r'/reader/page-\d+/?$', '/reader/', url)
            elif not url.rstrip('/').endswith('/reader'):
                if url.endswith('/'):
                    url += 'reader/'
                else:
                    url += '/reader/'

    else:
        def adapt_search_conditions(search_conditions):
            """
            Converts search_conditions dict to the adapted format for SpaceBattles/RoyalRoad queries.
            Only includes keys that are present and valid.
            """
            adapted_conditions = {}
            if not isinstance(search_conditions, dict) or not search_conditions:
                return adapted_conditions  # Return empty dict if no conditions

            # Handle threadmark_status as indexed keys if it's a list
            threadmark_status = search_conditions.get("threadmark_status", [])
            if isinstance(threadmark_status, list):
                for idx, status in enumerate(threadmark_status):
                    adapted_conditions[f"threadmark_index_statuses[{idx}]"] = status

            search_scope = search_conditions.get("search_scope", "title")
            if isinstance(search_scope, dict):
                for k, v in search_scope.items():
                    adapted_conditions[k] = v

            # Directly copy over other relevant keys if present
            for key in ["min_word_count", "max_word_count", "sort_by", "direction", "true_search"]:
                if key in search_conditions:
                    # For "sort_by", convert to "order" as required by some endpoints
                    if key == "sort_by":
                        adapted_conditions["order"] = search_conditions[key]
                    else:
                        adapted_conditions[key] = search_conditions[key]
                
            return adapted_conditions
        searchConditions=adapt_search_conditions(searchConditions)
        
        #If input is not a URL, treat it as a search query
        #I need to standardize the query_site function 
        url=await scraper.query_site(input.strip(), searchConditions,cookie)
        logging.warning(f"Search URL: {url}")
    
    if not url_pattern.match(url.strip()):
        errorText=f"Function search_page. Error: There was no result. Please check the input or the search conditions."
        logging.warning(errorText)
        write_to_logs(errorText)
        return None
    bookID,bookTitle,bookAuthor,description,lastScraped,latestChapterTitle,latestChapterID= await scraper.fetch_novel_data(url)
    bookID=remove_invalid_characters(bookID)
    listofChapterTitles=await scraper.fetch_chapter_title_list(url)
    listofChapters = await scraper.fetch_chapter_list(url)
    logging.warning(listofChapters)
    return {
        "bookID": bookID,
        "bookTitle": bookTitle,
        "bookAuthor": bookAuthor,
        "bookDescription": description,
        "latestChapterTitle": latestChapterTitle,
        "chapterTitles": listofChapterTitles,
        "chapterUrls": listofChapters,
        "mainURL": url,
    }


class MissingBookDataException(Exception):
    def __init__(self, missing_keys):
        message = f"Missing required keys in book dict: {', '.join(missing_keys)}"
        super().__init__(message)
        self.missing_keys = missing_keys


async def search_page_scrape_interface(book: dict, cookie: str, additionalConditions: dict):
    try:
        bookID=book["bookID"]
        bookTitle=book["bookTitle"]
        bookAuthor=book["bookAuthor"]
        websiteHost=book["websiteHost"]
        book_chapter_urls=book["book_chapter_urls"]
        mainBookURL=book["mainBookURL"]
    except KeyError as e:
        missing = [str(e)]
        raise MissingBookDataException(missing)


    if websiteHost=="royalroad":
        epub_producer=RoyalRoadEpubProducer()
    elif websiteHost=="forums.spacebattles":
        epub_producer=SpaceBattlesEpubProducer()
    elif websiteHost=="foxaholic":
        epub_producer=FoxaholicEpubProducer()
        if (cookie is None):
            errorText="Function search_page_scrape_interface. Error: Cookie is required for Foxaholic. Please provide a cookie."
            logging.warning(errorText)
            write_to_logs(errorText)
            return None
    elif websiteHost=="novelbin":
        epub_producer=NovelBinEpubProducer()
        if (cookie is None):
            errorText="Function search_page_scrape_interface. Error: Cookie is required for NovelBin. Please provide a cookie."
            logging.warning(errorText)
            write_to_logs(errorText)
            return None
    else:
        raise ValueError("Unsupported website")
    
    epub_producer.setCookie(cookie)
    
    style=open("style.css","r").read()
    default_css=epub.EpubItem(uid="style_nav",file_name="style/nav.css",media_type="text/css",content=style)
    
    async def instantiate_new_epub(bookID,bookTitle,bookAuthor):
        try:
            new_epub=epub.EpubBook()
            new_epub.set_identifier(bookID)
            new_epub.set_title(bookTitle)
            new_epub.set_language('en')
            new_epub.add_author(bookAuthor)
            new_epub.add_item(default_css)
            return new_epub
        except Exception as e:
            errorText=f"Failed to create new_epub object. Error: {e}"
            write_to_logs(errorText)
            return
    
    bookID=remove_invalid_characters(bookID)
    new_epub=await instantiate_new_epub(bookID,bookTitle,bookAuthor)
    

    dirLocation= await epub_producer.produce_custom_epub_interface(
        new_epub,bookTitle,default_css,book_chapter_urls, mainBookURL, additionalConditions,cookie)
    logging.error(dirLocation)    
    return dirLocation
#NOTE TO SELF. TEST THE NEW FETCH_CHAPTER_TITLE_LIST FUNCTIONS FOR EACH SITE

async def update_book(book: dict):
    try:
        bookID=book["bookID"]
        bookTitle=book["bookTitle"]
        orderOfContents=book["orderOfContents"]
    except KeyError as e:
        missing = [str(e)]
        raise MissingBookDataException(missing)
    
    if ((check_existing_book_Title(bookTitle) or check_existing_book(bookID)) and orderOfContents):
        logging.warning(f"Book {bookTitle} already exists in the database. Updating the book.")
        def write_order_of_contents(book_title, chapter_metadata):
            file_location = f"./books/raw/{book_title}/order_of_chapters.txt"
            logging.warning(chapter_metadata)
            with open(file_location, "w") as f:
                for data in chapter_metadata:
                    if isinstance(data, str):
                        data = data.strip().split(";")
                    logging.warning(data)
                    f.write(";".join(map(str, data))+ "\n")
        
        write_order_of_contents(bookTitle, orderOfContents)
        
        try:
            latestChapterTitle=orderOfContents[-1].split(";")[2].strip() if orderOfContents else "N/A"
            def strip_latest_chapter_title(latestChapterTitle: str) -> str:
                """
                For a string like:
                "Beneath the Dragoneye Moons/Beneath the Dragoneye Moons - 2230094 - Chapter 622 - Overthrowing the Tyrants XV.html"
                returns: "Chapter 622 - Overthrowing the Tyrants XV"
                """
                # Get the last part after the last '/'
                last_part = latestChapterTitle.split("/")[-1]
                # Split on ' - ' and get everything after the second dash
                parts = last_part.split(" - ")
                # Find the index of the part that starts with 'Chapter'
                chapter_idx = next((i for i, p in enumerate(parts) if p.strip().startswith("Chapter")), None)
                if chapter_idx is not None:
                    # Join 'Chapter ###' and everything after
                    chapter_title = " - ".join(parts[chapter_idx:])
                    # Remove .html if present
                    if chapter_title.endswith(".html"):
                        chapter_title = chapter_title[:-5]
                    return chapter_title.strip()
                # Fallback: just remove .html and return last part
                return last_part.replace(".html", "").strip()
            latestChapterTitle=strip_latest_chapter_title(latestChapterTitle)
        except Exception as e:
            errorText=f"Failed to retrieve latest chapter title from order of contents. Error: {e}"
            logging.warning(errorText)
            write_to_logs(errorText)
            latestChapterTitle="N/A"
        
        first,last,total=get_first_last_chapter(bookTitle)
        
        updated_book={
            "bookID": bookID,
            "bookTitle": bookTitle,
            "firstChapter": first,
            "lastChapterID": last,
            "totalChapters": total,
            "lastChapterTitle": latestChapterTitle,
        }
        update_entry(updated_book)
        return True
    else:
        errorText=f"Book {bookTitle} does not exist in the database. Please provide a valid book ID or title."
        logging.warning(errorText)
        write_to_logs(errorText)
        return None
        
        

