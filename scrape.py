import bs4
import requests



from typing import Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


app=FastAPI()
origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://127.0.0.1",
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
url="https://www.royalroad.com/fiction/55927/the-newt-and-demon-book-1-2-on-amazon-cozy-alchemy"




def fetchChapterList(novelURL):
    soup = bs4.BeautifulSoup(requests.get(novelURL).text, 'html.parser')
    chapterTable=soup.find("table",{"id":"chapters"})
    rows=chapterTable.find_all("tr")
    chapterList=list()
    
    f=open("chapters.txt","w")
    for row in rows[1:len(rows)-1]:
        #print(row)
        #print(type(row))
        #print(row.find('a').contents[0])
        #print("\n")
        chapterData={}
        chapterData["name"]=row.find("a").contents[0].strip()
        chapterData["url"]=row.find("a")["href"]
        chapterList.append(chapterData)
        f.write(str(chapterData)+"\n")
        
    f.close()
    

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/chapters")
def fetchChapterList(novelURL):
    
    return {"Current working"}
    
    soup = bs4.BeautifulSoup(requests.get(novelURL).text, 'html.parser')
    chapterTable=soup.find("table",{"id":"chapters"})
    rows=chapterTable.find_all("tr")
    chapterList=list()
    for row in rows[1:len(rows)-1]:
        #print(row)
        #print(type(row))
        #print(row.find('a').contents[0])
        #print("\n")
        chapterData={}
        chapterData["name"]=row.find("a").contents[0].strip()
        chapterData["url"]=row.find("a")["href"]
        chapterList.append(chapterData)
    return chapterList