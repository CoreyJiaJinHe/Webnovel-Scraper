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
    result = savedBooks.find({"bookID": {"$nin": [-1, 0]}}).to_list(length=None)
    result=[[result["bookID"],result["bookName"],(result["lastScraped"]).strftime('%m/%d/%Y'),result["lastChapter"]] for result in result]
    return result




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