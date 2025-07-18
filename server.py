#TO START
# fastapi dev server.py
# npm run dev for react frontend
#ngrok http --url=delicate-generally-gelding.ngrok-free.app 5173 for ngrok open domain


from typing import Union
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi import Request
from fastapi import FastAPI, File, UploadFile
from fastapi.staticfiles import StaticFiles

import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
#logging.getLogger("uvicorn").setLevel(logging.DEBUG)
#logging.getLogger("uvicorn.error").setLevel(logging.DEBUG)
#logging.getLogger("uvicorn.access").setLevel(logging.DEBUG)


from scrapers.common import (write_to_logs)
import refactor
import OnlineReader

from passlib.context import CryptContext

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from pydantic import BaseModel

import mongodb

#from pymongo import MongoClient
import os

# MONGODB_URL=os.getenv('MONGODB_URI')
# myclient=MongoClient(MONGODB_URL)
# mydb=myclient["Webnovels"]
# savedBooks=mydb["Books"]
port = os.getenv("PORT") or 8000 #8080
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES=os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES")


#For logging in terminal
#https://medium.com/@emanueleorecchio/print-log-messages-in-the-terminal-using-python-fastapi-and-uvicorn-f32dd4f77a03

app=FastAPI()

app.mount("/react/static", StaticFiles(directory="books/raw"), name="static")

origins = [
    "http://localhost",
    "http://localhost:8000",
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


@app.get("/api/get_website_hosts/")
def get_website_hosts():
    """
    Returns a list of website hosts that are supported.
    """
    try:
        website_hosts = mongodb.get_website_hosts()
        return JSONResponse(content=website_hosts)
    except Exception as e:
        logging.error(f"Error retrieving website hosts: {e}")
        return JSONResponse(content={"error": "Failed to retrieve website hosts"}, status_code=500)

@app.get("/api/getFiles/")
async def getFiles():
    try:
        latestBook=mongodb.getLatest()
        print("Before logging")
        logging.error(latestBook)
        print("After logging")
        #logging.warning(latestBook["directory"])
        fileLocation=latestBook["directory"]
        fileName=latestBook["bookName"]
            
        #Consider improving fileName to include Ch1- Latest chapter
        #logging.warning(fileName)
        
        headers={"content-disposition": f"{fileName}"}
        
        #This now works
        return FileResponse(path=fileLocation,filename=fileName,headers=headers, status_code=200)
    except Exception as e:
        logging.error(f"Error retrieving files: {e}")
        return JSONResponse(content={"error": "Failed to retrieve files"}, status_code=500)

@app.get("/api/getBook/")
async def getBook(id):
    try:
        logging.error(id)
        book=mongodb.getEpub(id)
        
        print("Before logging")
        logging.error(book)
        print("After logging")
        fileLocation=book["directory"]
        fileName=book["bookName"]
        #Consider improving fileName to include Ch1- Latest chapter
        #logging.warning(fileName)
        
        headers={"content-disposition": f"{fileName}"}
        
        #This now works
        return FileResponse(path=fileLocation,filename=fileName,headers=headers)
    except Exception as e:
            logging.error(f"Error retrieving book: {e}")
            return JSONResponse(content={"error": "Failed to retrieve book"}, status_code=500)




@app.get("/api/allBooks/")
def getAllBooks():
    allBooks=mongodb.get_organized_books()
    #logging.warning(allBooks)
    return JSONResponse(content=allBooks)

@app.get("/api/followedBooks/")
async def getFollowedBooks(request: Request,response: Response):
    received_access_token=request.cookies.get("access_token")
    logging.error(f"Current Access Token: {received_access_token}")
    if not received_access_token:
        raise credentials_exception  # 401 Unauthorized
    try:
        new_access_token,username,userID,verifiedStatus=await authenticate_token(received_access_token)
        logging.error(f"New Access Token: {new_access_token}")
        if (new_access_token):
            try:
                followedBooks = mongodb.get_Followed_Books(str(username))
            except Exception as e:
                logging.error(f"Error retrieving followed books: {e}")
                return JSONResponse(content={"error": "Failed to retrieve followed books"}, status_code=500)
            logging.error(followedBooks)
            response=JSONResponse(content={"username":username,"verifiedStatus":verifiedStatus, "allbooks":followedBooks}, status_code=200)
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
        
    except Exception as e:
        logging.error(f"Token authentication failed: {e}")
        raise credentials_exception  # 401 Unauthorized

@app.post("/api/followBook/")
async def followBook(request: Request):
    received_access_token=request.cookies.get("access_token")
    logging.error(f"New Access Token: {received_access_token}")
    if not received_access_token:
        raise credentials_exception  # 401 Unauthorized
    try:
        new_access_token,username,userID,verifiedStatus=await authenticate_token(received_access_token)
        data = await request.json()
        bookID = data.get("bookID")
        if (new_access_token):
            if(mongodb.add_to_user_reading_list(userID,bookID)):
                response=JSONResponse(content={"message": "Book followed successfully"}, status_code=200)
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
                logging.error("Failed to follow book")
                return JSONResponse(content={"error": "Failed to follow book"}, status_code=400)
    except Exception as e:
        logging.error(f"Token authentication failed: {e}")
        raise credentials_exception  # 401 Unauthorized


@app.post("/api/unfollowBook/")
async def unfollowBook(request: Request):
    received_access_token=request.cookies.get("access_token")
    logging.error(f"New Access Token: {received_access_token}")
    if not received_access_token:
        raise credentials_exception  # 401 Unauthorized
    try:
        new_access_token,username,userID,verifiedStatus=await authenticate_token(received_access_token)
        data = await request.json()
        bookID = data.get("bookID")
        if (new_access_token):
            if(mongodb.remove_from_user_reading_list(userID,bookID)):
                response=JSONResponse(content={"message": "Book removed successfully"}, status_code=200)
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
                logging.error("Failed to remove book")
                return JSONResponse(content={"error": "Failed to remove book"}, status_code=400)
    except Exception as e:
        logging.error(f"Token authentication failed: {e}")
        raise credentials_exception  # 401 Unauthorized

@app.get("/api/dev_get_unverified/")
async def getUnverifiedUsers():
    users=mongodb.get_unverified_users()
    return JSONResponse(content=users)
    
@app.post("/api/dev_verify_users/")
async def verifyUser(request: Request):
    try:
        data=await request.json()
        userid=data.get("userid")
        if(mongodb.verify_user(userid)):
            return JSONResponse(content={"message": "User verified successfully"}, status_code=200)
        else:
            return JSONResponse(content={"error": "User verification failed"}, status_code=400)
    except Exception as e:
        logging.error(f"Error verifying user: {e}")
        return JSONResponse(content={"error": "Invalid request"}, status_code=400)



@app.get("/api/retrieve_book")
async def retrieveBook(request: Request, bookTitle: str):
    received_access_token=request.cookies.get("access_token")
    if not received_access_token:
        raise credentials_exception  # 401 Unauthorized
    try:
        new_access_token,username,userID,verifiedStatus=await authenticate_token(received_access_token)
        if (new_access_token):
            book= mongodb.get_Entry_Via_Title(bookTitle)
            if (book):
                book_copy = dict(book)
                book = {
                    "bookID": book_copy.get("bookID"),
                    "bookName": book_copy.get("bookName"),
                    "bookAuthor": book_copy.get("bookAuthor"),
                    "bookDescription": book_copy.get("bookDescription"),
                    "websiteHost": book_copy.get("websiteHost"),
                    "lastChapterTitle": book_copy.get("lastChapterTitle"),
                    "totalChapters": book_copy.get("totalChapters"),
                }
                
                order_of_contents=mongodb.get_existing_order_of_contents(str(book["bookName"]))
                logging.error(f"Retrieved book: {book}")
                logging.error(f"Retrieved order of contents: {order_of_contents}")
                return JSONResponse(content=[book, order_of_contents], status_code=200)
            else:
                return JSONResponse (content={"error": "Book not found"}, status_code=404)
        else:
            raise credentials_exception  # 401 Unauthorized
    except Exception as e:
        errorText=f"Error retrieving book: {e}"
        write_to_logs(errorText)
        return JSONResponse(content={"error": errorText}, status_code=400)


@app.get("/api/query_book/")
async def queryBook(searchConditions: list, searchTerm: str, siteHost:str):
    #TODO Figure out a way to limit the amount of attempts per user
    try:
        def adapt_search_conditions(conditions):
            adapted_conditions = []
            if not conditions:
                return conditions #Remain empty. There are default conditions built into the existing search.



            return adapted_conditions
        
        
        logging.error(f"queryBook input: {searchTerm}")
        # Pass searchTerm and siteHost to your search_page function
        data = await refactor.search_page(searchTerm, siteHost, None)
        logging.error(data)
        response = JSONResponse(content=data, status_code=200)
        
        return response

    except Exception as e:
        logging.error(f"Weird error occurred: {e}")
        
        return JSONResponse(content={"error": "Weird error"}, status_code=400)


@app.post("/api/scrape_book/")
async def scrapeBook(request: Request):
    try:
        data = await request.json()
        logging.error(data)
        bookID= data.get("bookID")
        bookTitle = data.get("bookTitle")
        bookAuthor=data.get("bookAuthor")
        selectedSite = data.get("selectedSite")
        cookie = data.get("cookie",[])
        book_chapter_urls = data.get("book_chapter_urls", [])

        if (not bookTitle or not selectedSite or not book_chapter_urls):
            return JSONResponse(content={"error": "Missing bookTitle, siteHost or selectedSite"}, status_code=400)
        if not any(selectedSite in str(url) for url in book_chapter_urls):
            logging.error(f"Selected site {selectedSite} not in book_chapter_urls: {book_chapter_urls}")
            return JSONResponse(content={"error": "Selected site not in book chapter URLs"}, status_code=400)
        logging.error(f"Scraping book: {bookTitle} from {selectedSite}")
        #return JSONResponse(content={"message": "Scraping started"}, status_code=200)
        dirLocation = await refactor.search_page_scrape_interface(bookID, bookTitle, bookAuthor, selectedSite, cookie, book_chapter_urls)
        
        
        fileName=bookTitle
        #Consider improving fileName to include Ch1- Latest chapter
        #logging.warning(fileName)
        
        headers={"content-disposition":  f"attachment; filename={bookTitle}.epub"}
        #There is a potentially bad error where you get sent a file that's double its actual size?
        #CONFIRMED: TODO: FIXED FIX THIS ERROR. It breaks the epub file.
        return FileResponse(path=dirLocation, filename=fileName, headers=headers, status_code=200)
    except Exception as e:
        logging.error(f"Error in scrape_Book: {e}")
        return JSONResponse(content={"error": "Invalid request"}, status_code=400)
    

#DONE: Write hashing function for passwords
#DONE:Create user login function
#DONE:Create user registration function
#Create user profile function
#DONE: Create user book list return function
#DONE: Create user book list add function
#DONE: Create user book list remove function
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
    logging.warning(f"Creating access token with data: {data}")
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
            return new_access_token, username, userID, verifiedStatus
        return False
    except jwt.ExpiredSignatureError:
        raise credentials_exception        
    except InvalidTokenError:
        raise credentials_exception


    

@app.post("/api/token/")
async def login (request: Request, response: Response):
    received_access_token=request.cookies.get("access_token")
    logging.error(f"Current Access Token: {received_access_token}")
    if (received_access_token):
        new_access_token,username,userID,verifiedStatus=await authenticate_token(received_access_token)
        logging.error(f"New Access Token: {new_access_token}")
        if (new_access_token):
            isDeveloper=False
            if(mongodb.check_developer(username)):
                isDeveloper=True
            response=JSONResponse(content={"username":username,"verifiedStatus":verifiedStatus, "isDeveloper":isDeveloper}, status_code=200)
            response.set_cookie(
                key="access_token",
                value=new_access_token,
                httponly=True,
                samesite="lax",
                secure=False,
                max_age=60 * 60 * 24,  # 1 day in seconds
                expires=60 * 60 * 24   # 1 day in seconds (for compatibility)
            )
            logging.warning("Returning response with access token cookie")
            logging.error(response)
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
        #write_to_logs(username + " " + password)
        hashed_password=mongodb.get_hashed_password(username)
        logging.error(f"Hashed Password: {hashed_password}")
        if (hashed_password):
            write_to_logs(hashed_password + " " + password)
            logging.error(f"Verifying password for user: {username}")

            if (authenticate_user(password,hashed_password)):
                logging.error(f"User {username} authenticated successfully")
                write_to_logs("User authenticated")
                userID=mongodb.get_userID(username)
                access_token_expires=timedelta(minutes=int(ACCESS_TOKEN_EXPIRE_MINUTES))                    
                isDeveloper=False
                if(mongodb.check_developer(username)):
                    isDeveloper=True
                access_token=create_access_token(data={"userid": userID, "username":username},expires_delta=access_token_expires)
                write_to_logs("Access Token: "+access_token)
                verifiedStatus=mongodb.is_verified_user(userID,username)
                response=JSONResponse(content={"username":username, "verifiedStatus":verifiedStatus, "isDeveloper":isDeveloper},status_code=200)
                response.set_cookie(
                    key="access_token",
                    value=access_token,
                    httponly=True,
                    samesite="lax",
                    secure=False,
                    max_age=60 * 60 * 24,  # 1 day in seconds
                    expires=60 * 60 * 24   # 1 day in seconds (for compatibility)
                )
                logging.warning("Returning response with access token cookie")
                logging.error(response)
                return response
            else:
                logging.error(f"Invalid credentials for user: {username}")
                return JSONResponse(content={"message": "Invalid Credentials"}, status_code=401)
        else:
            logging.error(f"Invalid credentials for user: {username}")
            return JSONResponse(content={"message": "Invalid Credentials"}, status_code=401)
    except Exception as e:
        write_to_logs("FastApi Login Error: "+str(e))
        return JSONResponse(content={"error": "Invalid request"}, status_code=400)

@app.post("/api/logout/")
async def logout(response: Response):
    try:
        response=JSONResponse(content={"message": "Logout successful"}, status_code=200)
        response.delete_cookie("access_token")
        logging.warning("User logged out successfully")
        return response
    except Exception as e:
        logging.error(f"Logout error: {e}")
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
        #write_to_logs(username + " " + password)
        
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
                    write_to_logs("Access Token: "+access_token)
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
                    write_to_logs("How the fuck did you get here. This should not be possible. We check username multiple times before this")
            except Exception as e:
                write_to_logs("FastAPI Change Password Error: "+str(e))
        else:
            return {"message": "Invalid Credentials"}
    except Exception as e:
        write_to_logs("FastApi Change Password Error: "+str(e))
        return JSONResponse(content={"error": "FastApi Change Password Error"}, status_code=400)
    
    
    
    
    
    
    
    










@app.post("/api/verifydeveloper/")
async def developerLogin(request: Request, response: Response):
    logging.error("Checking to see if you are a developer")
    received_access_token=request.cookies.get("access_token")
    if (received_access_token):
        new_access_token,username,userID,verifiedStatus=await authenticate_token(received_access_token)
        if(mongodb.check_developer(username)):
            return True
    else:
        
        raise credentials_exception

@app.post("/api/dev/rrfollows/")
async def dev_get_reading_list(request: Request, response: Response):
    received_access_token=request.cookies.get("access_token")
    if (received_access_token):
        new_access_token,username,userID,verifiedStatus=await authenticate_token(received_access_token)
        if(mongodb.check_developer(username)):
            try:
                bookLinks=await refactor.retrieve_from_royalroad_follow_list()
                return JSONResponse(content={"message":"Successfully retrieved Royalroad follow list"}, status_code=200)
            except Exception as e:
                logging.error(f"Error retrieving Royal Road follow list: {e}")
                return JSONResponse(content={"error": "Failed to retrieve Royal Road follow list"}, status_code=500)
    else:
        raise credentials_exception


@app.get("/api/getBookChapterList/{book_id}")
async def getBookChapterList(book_id: str):
    try:
        if ("sb" in book_id):
            chapters = OnlineReader.get_chapter_list_spacebattles(book_id)
        else:
            chapters = OnlineReader.get_chapter_list(book_id)
        if chapters:
            return JSONResponse(content=chapters, status_code=200)
        else:
            return JSONResponse(content={"error": "No chapters found"}, status_code=404)
    except Exception as e:
        logging.error(f"Error retrieving chapter list: {e}")
        return JSONResponse(content={"error": "Failed to retrieve chapter list"}, status_code=500)



@app.get("/api/getBookChapterContent")
async def getBookChapters(bookID: str, chapterID: str, chapterTitle: str):
    #logging.error(f"Getting chapter content for bookID: {bookID}, chapterID: {chapterID}, chapterTitle: {chapterTitle}")

    try:
        if "sb" in bookID:
            chapter_content = OnlineReader.get_stored_chapter_spacebattles(bookID, chapterID, chapterTitle)
        else:
            chapter_content = OnlineReader.get_stored_chapter(bookID, chapterID)
        # Ensure the content is a string with HTML tags included
        if hasattr(chapter_content, 'prettify'):
            chapter_content = str(chapter_content)
        elif not isinstance(chapter_content, str):
            chapter_content = str(chapter_content)
        return JSONResponse(content={"chapterContent": chapter_content, "chapterTitle": chapterTitle}, status_code=200)
    except Exception as e:
        logging.error(f"Error retrieving chapter content: {e}")
        return JSONResponse(content={"error": "Failed to retrieve chapter content"}, status_code=500)

















@app.get("/", tags=["root"])
async def read_root() -> dict:
    return {"message": "Welcome to FAST API."}

#logging.warning(getFiles())
