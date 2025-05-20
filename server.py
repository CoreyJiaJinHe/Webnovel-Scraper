#TO START
# fastapi dev server.py
# npm run dev for react frontend
#ngrok http --url=delicate-generally-gelding.ngrok-free.app 5173 for ngrok open domain


from typing import Union
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi import Request
from fastapi import FastAPI, File, UploadFile
import logging

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel
#import scrape
import mongodb

#from pymongo import MongoClient
import os

# MONGODB_URL=os.getenv('MONGODB_URI')
# myclient=MongoClient(MONGODB_URL)
# mydb=myclient["Webnovels"]
# savedBooks=mydb["Books"]
port = os.getenv("PORT") or 8080
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES=os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")


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
    latestBook=mongodb.getLatest()
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
    book=mongodb.getEpub(id)

    fileLocation=book["directory"]
    fileName=book["bookName"]
    
    
    #Consider improving fileName to include Ch1- Latest chapter
    #logging.warning(fileName)
    
    headers={"content-disposition": f"{fileName}"}
    
    #This now works
    return FileResponse(path=fileLocation,filename=fileName,headers=headers)

@app.get("/api/allBooks/")
def getAllBooks():
    allBooks=mongodb.get_organized_books()
    #logging.warning(allBooks)
    return JSONResponse(content=allBooks)

#THE ERROR WITH MAPPING STARTS HERE^. ITS NOT A DICTIONARY
#FIXED BY DOING IT ON THE FRONT END




#TODO: Write hashing function for passwords
#Create user login function
#Create user registration function
#Create user profile function
#Create user book list return function
#Create user book list add function
#Create user book list remove function


#Learn how to use JWT Tokens/Cookies

import scrape
from passlib.context import CryptContext
#https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#install-passlib




class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    email: str | None = None
    full_name: str | None = None
    disabled: bool | None = None


class UserInDB(User):
    hashed_password: str

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password,hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def authenticate_user(password:str,hashed_password:str):
    if not verify_password(password, hashed_password):
        return False
    return True


@app.post("/api/login/")
async def login(request: Request):
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return JSONResponse(content={"error": "Missing username or password"}, status_code=400)
        
        scrape.write_to_logs(username + " " + password)
        hashed_password=mongodb.get_hashed_password(username)
        if (hashed_password):
            if (authenticate_user(password,hashed_password)):
                return {"message": "Login success"}
        else:
            return {"message": "Invalid Credentials"}
    except Exception as e:
        logging.error(f"Login error: {e}")
        return JSONResponse(content={"error": "Invalid request"}, status_code=400)


@app.post("/api/register/")
async def register (request: Request):
    try:
        data = await request.json()
        username = data.get("username")
        password = data.get("password")
        if not username or not password:
            return JSONResponse(content={"error": "Missing username or password"}, status_code=400)
        
        password=get_password_hash(password)
        scrape.write_to_logs(username + " " + password)
        
        if (mongodb.create_new_user(username,password)):
            return {True}
        else:
            return {False}
    except Exception as e:
        logging.error(f"Login error: {e}")
        return JSONResponse(content={"error": "Invalid request"}, status_code=400)
    

#TEST THE ABOVE



    
@app.get("/", tags=["root"])
async def read_root() -> dict:
    return {"message": "Welcome to FAST API."}

#logging.warning(getFiles())
