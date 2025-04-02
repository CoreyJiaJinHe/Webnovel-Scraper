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
)


#@app.get("/")
#async def root():
    
#    return {"message":"Hello World"}
#https://fastapi.tiangolo.com/advanced/custom-response/?h=fileresponse#fileresponse
#https://stackoverflow.com/questions/60716529/download-file-using-fastapi
#https://stackoverflow.com/questions/63048825/how-to-upload-file-using-fastapi

#https://fastapi.tiangolo.com/tutorial/first-steps/

@app.get("/api/getFiles/")
async def getFiles():
    latestBook=scrape.getLatest()
    logging.warning(latestBook)
#    return latestBook["directory"]
    return FileResponse(file_location=latestBook["directory"], filename=latestBook["bookName"],media_type="application/epub+zip")    
    #latestBook=scrape.getLatest()
    #return FileResponse(latestBook.directory)

@app.get("/", tags=["root"])
async def read_root() -> dict:
    return {"message": "Welcome to FAST API."}

