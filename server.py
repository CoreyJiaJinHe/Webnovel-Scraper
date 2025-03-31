#TO START
# fastapi dev server.py
# 
from typing import Union
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse


import scrape

from pymongo import MongoClient
import os

MONGODB_URL=os.getenv('MONGODB_URI')
myclient=MongoClient(MONGODB_URL)
mydb=myclient["Webnovels"]
savedBooks=mydb["Books"]


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


@app.get("/")
async def root():
    
    return {"message":"Hello World"}

async def getFiles():
    latestBook=scrape.getLatestBook()
    return latestBook.directory
    
    #latestBook=scrape.getLatest()
    #return FileResponse(latestBook.directory)