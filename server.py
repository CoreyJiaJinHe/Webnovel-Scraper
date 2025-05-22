#TO START
# fastapi dev server.py
# npm run dev for react frontend
#ngrok http --url=delicate-generally-gelding.ngrok-free.app 5173 for ngrok open domain


from typing import Union
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi import Request
from fastapi import FastAPI, File, UploadFile
import logging

import scrape

from passlib.context import CryptContext

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


#For logging in terminal
#https://medium.com/@emanueleorecchio/print-log-messages-in-the-terminal-using-python-fastapi-and-uvicorn-f32dd4f77a03

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




#DONE: Write hashing function for passwords
#DONE:Create user login function
#DONE:Create user registration function
#Create user profile function
#Create user book list return function
#Create user book list add function
#Create user book list remove function
#Create Cookies to store user login information and session data

#Learn how to use JWT Tokens/Cookies
#https://www.telerik.com/blogs/react-basics-how-to-use-cookies
#https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/#install-passlib




class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str | None = None
    userID:str |None=None


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

def create_access_token(data:dict, expires_delta: timedelta | None=None):
    to_encode=data.copy()
    if expires_delta:
        expire=datetime.now(timezone.utc)+expires_delta
    else:
        expire=datetime.now(timezone.utc)+timedelta(days=1)
    to_encode.update({"exp":expire})
    encoded_jwt=jwt.encode(to_encode,SECRET_KEY,algorithm=ALGORITHM)
    return encoded_jwt

credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
async def authenticate_token(token):
    try:
        payload=jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        
        logging.error(f"Payload: {payload}")
        userID=payload.get("userid")
        username=payload.get("username")
        if (userID is None or username is None):
            raise credentials_exception
        verifiedStatus=mongodb.is_verified_user(userID,username)
        if (verifiedStatus):
            access_token_expires = timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
            new_access_token = create_access_token(
                data={"userid": str(userID), "username": username},
                expires_delta=access_token_expires
            )
            return new_access_token, username, verifiedStatus
        return False
    except jwt.ExpiredSignatureError:
        raise credentials_exception        
    except InvalidTokenError:
        raise credentials_exception

@app.post("/api/token/")
async def login (request: Request, response: Response):
    received_access_token=request.cookies.get("access_token")
    logging.error(f"New Access Token: {received_access_token}")
    if (received_access_token):
        new_access_token,username,verifiedStatus=await authenticate_token(received_access_token)
        logging.error(f"New Access Token: {new_access_token}")
        if (new_access_token):
            response=JSONResponse(content={"username":username,"verifiedStatus":verifiedStatus}, status_code=200)
            response.set_cookie(
                key="access_token",
                value=new_access_token,
                httponly=True,
                samesite="lax",
                secure=False,
                max_age=60 * 60 * 24,  # 1 day in seconds
                expires=60 * 60 * 24   # 1 day in seconds (for compatibility)
            )
            return response
    else:
        raise credentials_exception

    
    
@app.post("/api/login/")
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], response: Response):
    try:
        username = form_data.username
        password = form_data.password
        if not username or not password:
            raise credentials_exception
            #return JSONResponse(content={"error": "Missing username or password"}, status_code=400)
        #scrape.write_to_logs(username + " " + password)
        hashed_password=mongodb.get_hashed_password(username)
        if (hashed_password):
            scrape.write_to_logs(hashed_password + " " + password)
            if (authenticate_user(password,hashed_password)):
                scrape.write_to_logs("User authenticated")
                userID=mongodb.get_userID(username)
                access_token_expires=timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
                access_token=create_access_token(data={"userid": userID, "username":username},expires_delta=access_token_expires)
                scrape.write_to_logs("Access Token: "+access_token)
                response=JSONResponse(content={"message":"Login successful"},status_code=200)
                response.set_cookie(
                    key="access_token",
                    value=access_token,
                    httponly=True,
                    samesite="lax",
                    secure=False,
                    max_age=60 * 60 * 24,  # 1 day in seconds
                    expires=60 * 60 * 24   # 1 day in seconds (for compatibility)
                )
                return response
        else:
            return {"message": "Invalid Credentials"}
    except Exception as e:
        scrape.write_to_logs("FastApi Login Error: "+str(e))
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
        #scrape.write_to_logs(username + " " + password)
        
        if (mongodb.create_new_user(username,password)):
            return {True}
        else:
            return {False}
    except Exception as e:
        logging.error(f"Login error: {e}")
        return JSONResponse(content={"error": "Invalid request"}, status_code=400)
    
@app.post("/api/changepassword/")
async def changePassword(request: Request):
    try:
        data = await request.json()
        username=data.get("username")
        password=data.get("password")
        newPassword=data.get("newPassword")
        
        hashed_password=mongodb.get_hashed_password(username)
        if (authenticate_user(password,hashed_password)):
            userID=mongodb.get_userID(username)
            newPassword=get_password_hash(newPassword)
            
            try:
                if (mongodb.update_password(username,newPassword)):
                    access_token_expires=timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))
                    access_token=create_access_token(data={"userid": userID, "username":username},expires_delta=access_token_expires)
                    scrape.write_to_logs("Access Token: "+access_token)
                    response=JSONResponse(content={"message":"Login successful"},status_code=200)
                    response.set_cookie(
                        key="access_token",
                        value=access_token,
                        httponly=True,
                        samesite="lax",
                        secure=False,
                        max_age=60 * 60 * 24,  # 1 day in seconds
                        expires=60 * 60 * 24   # 1 day in seconds (for compatibility)
                    )
                    return response
                else:
                    scrape.write_to_logs("How the fuck did you get here. This should not be possible. We check username multiple times before this")
            except Exception as e:
                scrape.write_to_logs("FastAPI Change Password Error: "+str(e))
        else:
            return {"message": "Invalid Credentials"}
    except Exception as e:
        scrape.write_to_logs("FastApi Change Password Error: "+str(e))
        return JSONResponse(content={"error": "FastApi Change Password Error"}, status_code=400)
    
@app.get("/", tags=["root"])
async def read_root() -> dict:
    return {"message": "Welcome to FAST API."}

#logging.warning(getFiles())
