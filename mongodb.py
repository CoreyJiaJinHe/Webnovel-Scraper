from pymongo import MongoClient
import os
import datetime
import logging

from dotenv import load_dotenv
load_dotenv()


MONGODB_URL=os.getenv('MONGODB_URI')
myclient=MongoClient(MONGODB_URL)
mydb=myclient["BotServers"]
botServers=mydb["Servers"]
from scrape import write_to_logs 

class Database:
    _instance = None

    @staticmethod
    def get_instance():
        if Database._instance is None:
            MONGODB_URL = os.getenv('MONGODB_URI')
            Database._instance = MongoClient(MONGODB_URL)["Webnovels"]
        return Database._instance

#savedBooks=Database.get_instance()


#Retrieve book data from MongoDB
def get_Entry_Via_ID(bookID):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID":bookID})
    return results
#Retrieve latest book data from MongoDB
def getLatest():
    db=Database.get_instance()
    savedBooks=db["Books"]
    result=savedBooks.find_one({"bookID":-1})
    logging.warning(result)
    return result

def get_Total_Books():
    db=Database.get_instance()
    savedBooks=db["Books"]
    result=savedBooks.count_documents({})
    return result-2

def get_all_books():
    db=Database.get_instance()
    savedBooks=db["Books"]
    result = savedBooks.find({"bookID": {"$nin": [-1, 0]}}).to_list(length=None).sort('bookName',1)
    result=[[result["bookID"],result["bookName"],(result["lastScraped"]).strftime('%m/%d/%Y'),result["lastChapter"]] for result in result]
    return result

def get_organized_books():
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.distinct("websiteHost")
    #logging.warning(results)
    all_books=[]
    for result in results:
        books=savedBooks.find({"bookID":{"$nin":[-1,0]}, "websiteHost":result}).sort('bookName',1).to_list(length=None)
        books=[[book["bookID"],book["bookName"],(book["lastScraped"]).strftime('%m/%d/%Y'),book["lastChapter"]] for book in books]
        if (books):
            all_books.append([result, books])
    return all_books
#logging.warning(get_organized_books())

def remove_excess_spaces():
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find({"bookID":{"$ne":-1}})
    for result in results:
        bookDescription=result["bookDescription"]
        if ("\n" in bookDescription):
            bookDescription=bookDescription.replace("\n","")
        while ("  " in bookDescription):
            bookDescription=bookDescription.replace("  "," ")
        bookDescription=bookDescription.strip()
        bookAuthor=result["bookAuthor"]
        #logging.warning(bookAuthor)
        if ("\n" in bookAuthor):
            bookAuthor=bookAuthor.replace("\n","")
        while ("  " in bookAuthor):
            bookAuthor=bookAuthor.replace("  "," ")
        if ("Author:" in bookAuthor):
            bookAuthor=bookAuthor.replace("Author:","")
        bookAuthor=bookAuthor.strip()
        savedBooks.update_one({"bookID":result["bookID"]},{"$set":{'bookDescription':bookDescription, 'bookAuthor':bookAuthor}})
#remove_excess_spaces()



import re
def fix_websiteHost_links():
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find({"bookID":{"$ne":0}})
    for result in results:
        websiteHost=result["websiteHost"]
        if re.match(r"^[A-Za-z0-9.-]+$", websiteHost):
            logging.warning(f"WebsiteHost already in correct format: {websiteHost}")
            continue  # Skip processing if it's already a root domain
        match = re.search(r"https://(?:www\.)?([A-Za-z0-9.-]+)", websiteHost)

        if match:
            newURL=match.group(1)
            savedBooks.update_one({"bookID":result["bookID"]},{"$set":{'websiteHost':newURL}})
            logging.warning(f"Updated websiteHost: {newURL}")
        else:
            logging.warning(f"Failed to process websiteHost: {websiteHost}")
#fix_websiteHost_links()


def check_existing_book(bookID):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID":bookID})
    if (results==None):
        return False
    else:
        return True
def check_existing_book_Title(bookTitle):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookName":bookTitle})
    if (results==None):
        return False
    return True


#Return existing epub directory if the latest chapter is already stored.
def getEpub(bookID):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID":bookID})
    directory=results["directory"]
    return directory

def get_Entry_Via_Title(bookTitle):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results = savedBooks.find_one({"bookID": {"$ne": -1}, "bookName": bookTitle})
    if not results:
        return None
    return results

def check_latest_chapter(bookID,bookTitle,latestChapter):
    bookData=get_Entry_Via_ID(bookID)
    if (bookData is None):
        bookData=get_Entry_Via_Title(bookTitle)
        if (bookData is None):
            return False
    logging.warning(bookData["lastChapter"])
    logging.warning(latestChapter)
    if (bookData["lastChapter"]==latestChapter):
        return True
    elif (bookData["lastChapter"]<=latestChapter):
        return False
    return True
    


#Requires 10 inputs. BookID, bookName, bookAuthor, bookDescription, WebsiteHost, firstChapter#, lastChapter#, totalChapters, directory

default_values = {
        "bookID": 0,
        "bookName": "Template",
        "bookAuthor": "Template",
        "bookDescription": "Template",
        "websiteHost": "Template",
        "firstChapter": -1,
        "lastChapter": -1,
        "totalChapters":-1,
        "directory": "Template"
    }
def create_Entry(**kwargs):
    global default_values
    #If missing keyword arguments, fill with template values.
    book_data = {**default_values, **kwargs}
    book = {
        "bookID": book_data["bookID"],
        "bookName": book_data["bookName"],
        "bookAuthor":book_data["bookAuthor"],
        "bookDescription": book_data["bookDescription"],
        "websiteHost": book_data["websiteHost"],
        "firstChapter": book_data["firstChapter"],
        "lastChapter": book_data["lastChapter"],
        "lastScraped": datetime.datetime.now(),
        "totalChapters": book_data["totalChapters"],
        "directory": book_data["directory"]
    }
    
    
    logging.warning(book)
    db=Database.get_instance()
    savedBooks=db["Books"]
    if (check_existing_book(book_data["bookID"]) and check_existing_book_Title(book_data["bookName"])):
        result=savedBooks.replace_one({"bookID": book_data["bookID"]}, book)
        logging.warning(f"Replaced book: {result}")
    else:
        result = savedBooks.insert_one(book)
        logging.warning(f"Inserted book: {result}")

def create_latest(**kwargs):
        global default_values
        #If missing keyword arguments, fill with template values.
        book_data = {**default_values, **kwargs}
        
        book = {
            "bookID": -1,
            "bookName": book_data["bookName"],
            "bookAuthor":book_data["bookAuthor"],
            "bookDescription": book_data["bookDescription"],
            "websiteHost": book_data["websiteHost"],
            "firstChapter": book_data["firstChapter"],
            "lastChapter": book_data["lastChapter"],
            "lastScraped": datetime.datetime.now(),
            "totalChapters": book_data["totalChapters"],
            "directory": book_data["directory"]
        }
        db=Database.get_instance()
        savedBooks=db["Books"]
        if (check_existing_book(-1)):
            savedBooks.replace_one({"bookID": -1}, book)
        else:
            savedBooks.insert_one(book)




def check_existing_reading_list(userID):
    db=Database.get_instance()
    userBookLibrary=db["UserLists"]
    results=userBookLibrary.find_one({"userID":userID})
    if (results==None):
        return False
    else:
        return results


def create_user_reading_list(**kwargs):
    db=Database.get_instance()
    userBookLibrary=db["UserLists"]
    
    userExists=check_verified_user(kwargs["userID"])
    if (userExists):
        readingListExists=check_existing_reading_list(kwargs["userID"])
        if (readingListExists):
            getFollowList=readingListExists["followList"]
            for i in kwargs["followList"]:
                if (i not in getFollowList):
                    getFollowList.append(i)
            record={
                "userID": kwargs["userID"],
                "followList":getFollowList
            }
            result=userBookLibrary.update_one(record)
            logging.warning("Updated user reading list for:"+str(userBookLibrary.insert_one(record)))

        else:
            record={
                "userID": kwargs["userID"],
                "followList":kwargs["followList"]
            }
            result=userBookLibrary.insert_one(record)
            logging.warning("Created user reading list for:"+str(result))
    else:
        logging.warning("User does not exist; Therefore we cannot make a reading list.")

def remove_from_user_reading_list(**kwargs):
    db=Database.get_instance()
    savedBooks=db["UserLists"]
    results=check_existing_reading_list(kwargs["userID"])
    if (results):
        for i in kwargs["removeList"]:
            if (i in results["followList"]):
                results["followList"].remove(i)
        result=savedBooks.update_one({"userID":results["userID"]},{"$set":{"followList":results["followList"]}})
        return True
    else:
        logging.warning("User does not exist.")
        return False
    
def generate_userID():
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    userID=verifiedUsers.count_documents({})+1
    return userID

def create_new_user(userName, passWord):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    userID=generate_userID()
    results=verifiedUsers.find_one({"userID":userID})
    if (results==None):
        record={
            "userID": userID,
            "username": userName,
            "password": passWord,
            "developer":False,
            "verified":False,
            "dateCreated":datetime.datetime.now(),
            "lastLogin":datetime.datetime.now(),
        }
        result=str(verifiedUsers.insert_one(record))
        write_to_logs(result)
        logging.warning("Created verified user for:"+result)
        return True
    else:
        logging.warning("User already exists.")
    return False

def verify_user(userID):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    results=verifiedUsers.find_one({"userID":userID})
    if (results):
        result=str(verifiedUsers.update_one({"userID":userID},{"$set":{"verified":True}}))
        write_to_logs(result)

def is_verified_user(userID):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    results=verifiedUsers.find_one({"userID":userID})
    if (results):
        logging.warning("User is verified")
    logging.warning("User is not verified")

def delete_verified_user(userID):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    results=verifiedUsers.find_one({"userID":userID})
    if (results==None):
        return False
    else:
        result=str(verifiedUsers.delete_one({"userID":userID}))
        write_to_logs(result)
        return True

def check_verified_user(userID):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    results=verifiedUsers.find_one({"userID":userID})
    if (results==None):
        return False
    else:
        result=str(verifiedUsers.update_one({"userID":userID},{"$set":{"lastLogin":datetime.datetime.now()}}))
        write_to_logs(result)
        return True

def get_hashed_password(username):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    results=verifiedUsers.find_one({"username":username})
    if (results!=None):
        result=str(verifiedUsers.update_one({"username":username},{"$set":{"lastLogin":datetime.datetime.now()}}))
        write_to_logs(result)
        return results["password"]

def check_login_credentials(userID,password):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    results=verifiedUsers.find_one({"userID":userID})
    if (results!=None):
        result=str(verifiedUsers.update_one({"userID":userID},{"$set":{"lastLogin":datetime.datetime.now()}}))
        write_to_logs(result)
        return results["password"]
    return False

#create_user_reading_list(userID=2,followList=[1,2,3,4,5])


def template_server_data():
    template_server={
        "serverID":"Template",
        "serverName":"Template",
        "channelID": [],
        "channelName": [],
        "allowed":False
    }
    if(check_existing_server("Template")):
        botServers.replace_one({"serverID":"Template"},template_server)
    else:
        botServers.insert_one(template_server)


def insert_server_data(serverID,serverName, channelID,channelName):
    server_data={
        "serverID":serverID,
        "serverName":serverName,
        "channelID": [channelID],
        "channelName": [channelName],
        "allowed":True
    }
    if(check_existing_server(serverID)):
        if (check_already_allowed(serverID,channelID)):
            return "Already exists in the \"allowed\" database"
        botServers.update_one({"serverID":serverID},{"$push":{"channelID":channelID}})
        return "Successfully updated list of allowed channels for this Server"
    else:
        botServers.insert_one(server_data)
        return "Successfully added channel and or server to database"

def remove_existing_channel(serverID,channelID):
    if (check_existing_server(serverID)):
        if (check_already_allowed(serverID,channelID)):
            botServers.update_one({"serverID":serverID},{"$pull":{"channelID":channelID}})
            return "Successfully removed channel from server"
        else:
            return "Channel not found in server"
    return "Server not found"

def check_existing_server(serverID):
    results=botServers.find_one({"serverID":serverID})
    if (results==None):
        return False
    else:
        return True
    
def check_already_allowed(serverID,channelID):
    results=botServers.find_one({"serverID":serverID})
    if (channelID in results["channelID"]):
        return True
    else:
        return False
    

#template_server_data()

#insert_server_data(698278375952744584, 1339637629574189197)