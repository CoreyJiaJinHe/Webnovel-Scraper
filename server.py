#TO START
# fastapi dev server.py
# 
from typing import Union
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
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
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    #expose_headers={'Content-Disposition'}
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
async def getFiles():
    latestBook=scrape.getLatest()
    #logging.warning(latestBook)
    #logging.warning(latestBook["directory"])
    fileLocation=latestBook["directory"]
    fileName=latestBook["bookName"]
    
    
    #Consider improving fileName to include Ch1- Latest chapter
    logging.warning(fileName)
    
    #This now works
    return FileResponse(path=fileLocation,filename=fileName)

@app.get("/", tags=["root"])
async def read_root() -> dict:
    return {"message": "Welcome to FAST API."}

logging.warning(getFiles())