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
from scrapers.SpacebattlesScraper import SpaceBattlesScraper

from common import(
    write_to_logs,
    check_directory_exists,
    make_directory,
    check_if_chapter_exists,
    retrieve_stored_image,
    remove_tags_from_title,
    retrieve_cover_from_storage,
    storeEpub
)


class SpaceBattlesEpubProducer(EpubProducer):
    async def spacebattles_fetch_chapter_list(self,url):
        scraper=SpaceBattlesScraper()
        return await scraper.fetch_chapter_list(url)
    
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

    async def spacebattles_save_page_content(self,chapterContent,bookTitle,fileTitle):
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

    #Overrides existing produce_epub
    async def produce_epub(self,novelURL,bookTitle,css,new_epub):
        logging.warning('Starting produce_epub in overwritten method')
        already_saved_chapters = self.get_existing_order_of_contents(bookTitle)
        chapterMetaData=list()
        tocList=list()
        imageCount=0
        scraper=SpaceBattlesScraper()
        for pageNum in range(1, await self.spacebattles_fetch_chapter_list(novelURL)+1):
            await asyncio.sleep(1)
            page_url = f"{novelURL}page-{pageNum}/"
            
            logging.warning (page_url)
            #Retrieval does not work at the moment
            if check_if_chapter_exists(page_url, already_saved_chapters):
                chapter_id, dir_location = self.get_chapter_from_saved(pageNum, already_saved_chapters)
                page_content = self.get_chapter_contents_from_saved(dir_location)
                page_soup=bs4.BeautifulSoup(page_content,'html.parser')
                all_chapters=page_soup.find_all('div',{'id':'chapter-start'})
                for chapter_soup in all_chapters:
                    chapter_title=chapter_soup.find('title')
                    chapter_title=chapter_title.get_text()
                    images=chapter_soup.find_all('img')
                    images=[image['src'] for image in images]
                    currentImageCount=imageCount
                    if images:
                        for image in images:
                            try:
                                imageDir=f"./books/raw/{bookTitle}/images/image_{currentImageCount}.png"
                                epubImage=retrieve_stored_image(imageDir)
                                b=io.BytesIO()
                                epubImage.save(b,'png')
                                b_image1=b.getvalue()
                                
                                image_item=epub.EpubItem(uid=f'image_{currentImageCount}',file_name=f'images/image_{currentImageCount}.png', media_type='image/png', content=b_image1)
                                new_epub.add_item(image_item)
                                currentImageCount+=1
                            except Exception as e:
                                errorText=f"Failed to add image to epub. Image does not exist, was never saved. Function spacebattles_produce_epub Error: {e}"
                                write_to_logs(errorText)
                                continue
                    imageCount=currentImageCount
                    chapter=epub.EpubHtml(title=chapter_title, file_name=f"{bookTitle} - {pageNum} - {chapter_title}.xhtml", lang='en')
                    chapter_content=chapter_soup.encode('ascii')
                    chapter.set_content(chapter_content)
                    chapter.add_item(css)
                    tocList.append(chapter)
                    new_epub.add_item(chapter)
                
                fileTitle=bookTitle+" - "+str(pageNum)
                chapterMetaData.append([pageNum,page_url,f"./books/raw/{bookTitle}/{fileTitle}.html"])
            else:
                soup=await scraper.get_soup(page_url)
                articles=soup.find_all("article",{"class":"message"})
                pageContent=""
                if (articles):
                    for article in articles:
                        threadmarkTitle=article.find("span",{"class":"threadmarkLabel"})
                        title=threadmarkTitle.get_text()
                        title=remove_tags_from_title(title)
                        logging.warning(title)
                        
                        chapterContent=article.find("div",{"class":"message-userContent"})
                        chapterContent=await self.spacebattles_remove_garbage_from_chapter(chapterContent)
                        
                        
                        hyperlinks=chapterContent.find_all('a',{'class':'link'})
                        
                        #Convert hyperlinked text into normal text with image appended after.
                        for link in hyperlinks:
                            if 'imgur' in link['href']:
                                p_text=link.get_text()
                                imgur_url=link['href']
                                if not imgur_url.startswith('https://i.imgur.com/'):
                                    match = re.search(r'(https?://)?(www\.)?imgur\.com/([a-zA-Z0-9]+)', imgur_url)
                                    if match:
                                        imgur_id = match.group(3)  # Extract the unique Imgur ID
                                        imgur_url = f"https://i.imgur.com/{imgur_id}.png"  # Convert to i.imgur.com format
                                p_tag=bs4.BeautifulSoup(f"<p>{p_text}</p><div><img class=\"image\" src={imgur_url}></div>", 'html.parser')
                                link.replace_with(p_tag)
                                chapterContent=bs4.BeautifulSoup(str(chapterContent),'html.parser')
                                
                        #images=chapterContent.find_all('img')
                        #logging.warning(images)
                        images=[]
                        seen = set()
                        for image in chapterContent.find_all('img'):
                            # Get the image URL from 'src' or fallback to 'data-src'
                            img_url = image['src'] if re.match(r'^https?://', image.get('src', '')) else image.get('data-src', '')
                            # Add the URL to the list if it's valid and not already seen
                            if img_url and img_url not in seen:
                                images.append(img_url)
                                seen.add(img_url)
                        
                        imageDir=f"./books/raw/{bookTitle}/images/"
                        currentImageCount=imageCount
                        if (images):
                            imageCount=await self.save_images_in_chapter(images,imageDir,imageCount,new_epub)
                            for img,image in zip(chapterContent.find_all('img'),images):
                                # Ensure the 'src' attribute exists before replacing
                                if img.has_attr('src') and image:
                                    # Replace the 'src' attribute with the local path
                                    img['src'] = f"images/image_{currentImageCount}.png"
                                    currentImageCount += 1
                                # img['src']=img['src'].replace(image,f"images/image_{currentImageCount}.png")       
                                # currentImageCount+=1
                        
                        chapter=epub.EpubHtml(title=title, file_name=f"{bookTitle} - {pageNum} - {title}.xhtml", lang='en')
                        stringChapterContent=str(chapterContent)
                        pageContent+=f"<div id='chapter-start'><title>{title}</title>{stringChapterContent}</div>"
                        
                        chapterContent=chapterContent.encode('ascii')
                        chapter.set_content(chapterContent)
                        chapter.add_item(css)
                        tocList.append(chapter)
                        new_epub.add_item(chapter)
                        
                        
                        
                fileTitle=bookTitle+" - "+str(pageNum)
                pageContent=bs4.BeautifulSoup(pageContent,'html.parser')
                
                await self.spacebattles_save_page_content(pageContent,bookTitle,fileTitle)
                chapterMetaData.append([str(pageNum),page_url,f"./books/raw/{bookTitle}/{fileTitle}.html"])
        
        # logging.warning("We reached retrieve_cover_from_storage")
        img1=retrieve_cover_from_storage(bookTitle)
        if img1:    
            b=io.BytesIO()
            try:
                img1.save(b,'png')
                b_image1=b.getvalue()
                image1_item=epub.EpubItem(uid='cover_image',file_name='images/cover_image.png', media_type='image/png', content=b_image1)
                new_epub.add_item(image1_item)
            except Exception as e:
                logging.warning(f"There is no cover image:{e}")
        
        new_epub.toc=tocList
        new_epub.spine=tocList
        new_epub.add_item(epub.EpubNcx())
        new_epub.add_item(epub.EpubNav())
        
        self.write_order_of_contents(bookTitle, chapterMetaData)
        
        # logging.warning("Attempting to store epub")
        storeEpub(bookTitle, new_epub)
