#TO START
# fastapi dev server.py
# npm run dev for react frontend
#ngrok http --url=delicate-generally-gelding.ngrok-free.app 5173 for ngrok open domain


from typing import Union
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi import FastAPI, File, UploadFile
import logging

import scrape

from pymongo import MongoClient
import os

MONGODB_URL=os.getenv('MONGODB_URI')
myclient=MongoClient(MONGODB_URL)
mydb=myclient["Webnovels"]
savedBooks=mydb["Books"]
port = os.getenv("PORT") or 8080

app=FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:5173",
    "http://127.0.0.1",
    "http://127.0.0.1:5173",
    "https://delicate-generally-gelding.ngrok-free.app"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=['Content-Disposition'],
    #expose_headers=["CustomName", "content-disposition"],  # Expose custom headers
)


#@app.get("/")
#async def root():
    
#    return {"message":"Hello World"}
#https://fastapi.tiangolo.com/advanced/custom-response/?h=fileresponse#fileresponse
#https://stackoverflow.com/questions/60716529/download-file-using-fastapi
#https://stackoverflow.com/questions/63048825/how-to-upload-file-using-fastapi

#https://fastapi.tiangolo.com/tutorial/first-steps/
#https://stackoverflow.com/questions/71191662/how-do-i-download-a-file-from-fastapi-backend-using-javascript-fetch-api-in-the
#https://stackoverflow.com/questions/73234675/how-to-download-a-file-after-posting-data-using-fastapi/73240097#73240097
#https://stackoverflow.com/questions/73410132/how-to-download-a-file-using-reactjs-with-axios-in-the-frontend-and-fastapi-in-t

@app.get("/api/getFiles/")
def getFiles():
    latestBook=scrape.getLatest()
    #logging.warning(latestBook)
    #logging.warning(latestBook["directory"])
    fileLocation=latestBook["directory"]
    fileName=latestBook["bookName"]
    
    
    #Consider improving fileName to include Ch1- Latest chapter
    #logging.warning(fileName)
    
    headers={"content-disposition": f"{fileName}"}
    
    #This now works
    return FileResponse(path=fileLocation,filename=fileName,headers=headers)

@app.get("/api/getBook/")
async def getBook(id):
    book=scrape.get_Entry(id)

    fileLocation=book["directory"]
    fileName=book["bookName"]
    
    
    #Consider improving fileName to include Ch1- Latest chapter
    #logging.warning(fileName)
    
    headers={"content-disposition": f"{fileName}"}
    
    #This now works
    return FileResponse(path=fileLocation,filename=fileName,headers=headers)

@app.get("/api/allBooks/")
def getAllBooks():
    allBooks=scrape.get_all_books()
    #logging.warning(allBooks)
    return JSONResponse(content=allBooks)

#THE ERROR WITH MAPPING STARTS HERE^. ITS NOT A DICTIONARY
#FIXED BY DOING IT ON THE FRONT END
    
@app.get("/", tags=["root"])
async def read_root() -> dict:
    return {"message": "Welcome to FAST API."}

#logging.warning(getFiles())