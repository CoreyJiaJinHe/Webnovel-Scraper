

import aiohttp
import asyncio
import logging

async def download_file(url, filename):
    async with aiohttp.ClientSession(headers = {
            'User-agent': 'Image Bot'}) as session:
        async with session.get(url) as response:
            logging.warning(response.status)
            if response.status !=200:
                logging.warning("Failed to connect")
            logging.warning(response.content)
            with open(filename, "wb") as f: 
                chunk_size = 4096
                async for data in response.content.iter_chunked(chunk_size):
                    f.write(data)

asyncio.run(download_file("https://i.imgur.com/Kd5ERk2.jpg", "image.jpg"))




def generate_Epub_Based_On_Stored_Order(new_epub, bookTitle):
    already_saved_chapters=get_existing_order_of_contents(bookTitle)
    
    tocList=list()
    for url in already_saved_chapters:
        url=url.split(";")
        chapterID=url[0]
        fileChapterTitle=extract_chapter_title(url[len(url)-1])
        dirLocation=url[len(url)-1]
        chapterContent=get_chapter_contents_from_saved(dirLocation).encode("utf-8")
        
        strippedTitle=fileChapterTitle.split('-')
        strippedTitle=strippedTitle[len(strippedTitle)-1].strip()
        
        chapter=epub.EpubHtml(title=strippedTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
        chapter.set_content(chapterContent)
        
        
        tocList.append(chapter)
        
        new_epub.add_item(chapter)
    
    new_epub.toc=tocList
    storeEpub(bookTitle,new_epub)
    
        
def generate_Epub_Based_On_Online_Order(new_epub,novelURL,bookTitle):
    tocList=list()
    for url in RoyalRoad_Fetch_Chapter_List(novelURL):
        chapterID=extract_chapter_ID(url)
        chapterTitle=fetch_Chapter_Title(url)
        fileChapterTitle = f"{bookTitle} - {chapterID} - {remove_invalid_characters(chapterTitle)}"
        chapterContent=RoyalRoad_Fetch_Chapter(url)
        
        
        chapter=epub.EpubHtml(title=chapterTitle,file_name=fileChapterTitle+'.xhtml',lang='en')
        chapter.set_content(chapterContent)
        
        tocList.append(chapter)
        
        new_epub.add_item(chapter)
        
        time.sleep(0.5)
    new_epub.toc=tocList
    storeEpub(bookTitle,new_epub)

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