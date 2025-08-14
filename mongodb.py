from pymongo import MongoClient
import os
import datetime
import logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

from dotenv import load_dotenv, find_dotenv

env_path = find_dotenv()
load_dotenv(env_path, override=True)


MONGODB_URL=os.getenv('MONGODB_URI')
myclient=MongoClient(MONGODB_URL)
mydb=myclient["BotServers"]
botServers=mydb["Servers"]
from utils import write_to_logs

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
    result=savedBooks.find_one({"bookID":"-1"})
    logging.warning(result)
    logging.error(result)
    return result

#logging.warning(getLatest())

def get_Total_Books():
    db=Database.get_instance()
    savedBooks=db["Books"]
    result=savedBooks.count_documents({})
    return result-2

def get_website_hosts():
    db=Database.get_instance()
    savedBooks=db["Books"]
    result = savedBooks.distinct("websiteHost", {"websiteHost": {"$nin": ["Template", "Unknown"]}})
    return result

def get_Total_Books_Organized(websiteHost):
    db=Database.get_instance()
    savedBooks=db["Books"]
    result=savedBooks.count_documents({"websiteHost": websiteHost, "bookID": {"$nin": ["-1", "0"]}})
    return result

#logging.warning(get_Total_Books_Organized("foxaholic.com"))

def get_all_books():
    db=Database.get_instance()
    savedBooks=db["Books"]
    result = savedBooks.find({"bookID": {"$nin": ["-1", "0"]}}).to_list(length=None).sort('bookName',1)
    result=[[result["bookID"],result["bookName"],(result["lastScraped"]).strftime('%m/%d/%Y'),result["lastChapterTitle"], result["bookDescription"]] for result in result]
    return result

def get_organized_books():
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.distinct("websiteHost")
    #logging.warning(results)
    all_books=[]
    for result in results:
        books=savedBooks.find({"bookID":{"$nin":["-1", "0"]}, "websiteHost":result}).sort('bookName',1).to_list(length=None)  
        books = [
            [
                book["bookID"],
                book["bookName"],
                book["bookAuthor"],
                book["bookDescription"],
                book["websiteHost"],
                book["lastScraped"].strftime('%m/%d/%Y'),
                book["lastChapterTitle"]
            ]
            for book in books
        ]        
        #books=[[book["bookID"],book["bookName"],(book["lastScraped"]).strftime('%m/%d/%Y'),book["lastChapterTitle"], book["bookDescription"]] for book in books]
        if (books):
            all_books.append([result, books])
    return all_books
#logging.warning(get_organized_books())


def check_existing_book(bookID):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID":bookID})
    if (results==None):
        return False
    else:
        logging.warning(f"Checking for bookID: {results['bookID']} ({type(results['bookID'])})")
        logging.warning(f"Checking for bookName: {results['bookName']} ({type(results['bookName'])})")
        return True
    
def check_existing_book_Title(bookTitle):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID":{"$ne": "-1"},"bookName":bookTitle})
    if (results==None):
        return False
    return True

#check_existing_book("sb836982")

#Return existing epub directory if the latest chapter is already stored.
def getEpub(bookID):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find_one({"bookID":bookID})
    book = {
        "directory" :results["directory"],
        "bookName" :results["bookName"]
    }
    return book

def get_Entry_Via_Title(bookTitle):
    db=Database.get_instance()
    savedBooks=db["Books"]
    results = savedBooks.find_one({"bookID": {"$ne": "-1"}, "bookName": bookTitle})
    if not results:
        return None
    return results

def get_existing_order_of_contents(book_title):
        # Default implementation
        dir_location = f"./books/raw/{book_title}/order_of_chapters.txt"
        if os.path.exists(dir_location):
            with open(dir_location, "r") as f:
                return f.readlines()
        return []
    

def check_latest_chapter(bookID,bookTitle,latestChapter):
    bookData=get_Entry_Via_ID(bookID)
    if (bookData is None):
        bookData=get_Entry_Via_Title(bookTitle)
        if (bookData is None):
            return False
    try:
        logging.warning(bookData["lastChapterTitle"])
        logging.warning(latestChapter)
        
        if (bookData["lastChapterTitle"]==latestChapter):
            return True
        return False
    except KeyError:
        logging.warning("KeyError: 'lastChapterTitle' not found in book data. This is likely because it is an old book entry.")
        return False
def check_recently_scraped(bookID):
    bookData=get_Entry_Via_ID(bookID)
    if (bookData is None):
        bookData=get_Entry_Via_Title(bookID)
        if (bookData is None):
            logging.warning("Book data not found.")
            return False
    lastScraped=bookData["lastScraped"]
    logging.warning(bookData)
    current_time = datetime.datetime.now()
    logging.warning(f"Current time: {current_time}")
    logging.warning(f"Last scraped time: {lastScraped}")
    time_difference = current_time - lastScraped
    logging.warning(f"Time difference in days: {time_difference.days}")
    if time_difference.days < 1:
        #Less than 24 hours since it was last scraped.
        logging.warning("Book was recently scraped. We are not scraping again.")
        return True
    return False

#Requires 10 inputs. BookID, bookName, bookAuthor, bookDescription, WebsiteHost, firstChapter#, lastChapter#, totalChapters, directory

default_values = {
        "bookID": 0,
        "bookName": "Template",
        "bookAuthor": "Template",
        "bookDescription": "Template",
        "websiteHost": "Template",
        "firstChapter": -1,
        "lastChapterID": -1,
        "lastChapterTitle": "N/A",
        "lastScraped": "1970-01-01 00:00:00",
        #Using a default date that is unlikely to be used.
        "totalChapters":-1,
        "directory": "Template",
        "imported": False,  # This is used to determine if the book was imported from a file or not.
        # If it was, then it needs to be edited by a developer.
        "edited": False, #This is used to determine if the book was edited by a developer or not.
        #If it wasn't, then it needs to be edited by a developer.
        "aliases":[] #This is used to store any alternative titles or names for the book.

    }
#This is dict merging.
#Another method is to use .get(value, default_value) for each key, but that's not as clean.




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
        "lastChapterID": book_data["lastChapterID"],
        "lastChapterTitle": book_data["lastChapterTitle"],
        "lastScraped": datetime.datetime.now(),
        "totalChapters": book_data["totalChapters"],
        "directory": book_data["directory"],
        "imported": book_data["imported"],
        "edited": book_data.get("edited", False),  # Default to False if not present
        "aliases": book_data.get("aliases", [])  # Default to empty list if not present
    }
    
    
    logging.warning(book)
    db=Database.get_instance()
    savedBooks=db["Books"]
    
    logging.warning(f"Checking if book with ID {book_data['bookID']} or title {book_data['bookName']} exists.")
    if check_existing_book(book_data["bookID"]):
        result = savedBooks.replace_one({"bookID": book_data["bookID"]}, book)
        logging.warning(f"Replaced book by ID: {result}")
    elif check_existing_book_Title(book_data["bookName"]):
        result = savedBooks.replace_one({"bookName": book_data["bookName"]}, book)
        logging.warning(f"Replaced book by Title: {result}")
    else:
        result = savedBooks.insert_one(book)
        logging.warning(f"Inserted book: {result}")

def create_latest(**kwargs):
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
            "lastChapterID": book_data["lastChapterID"],
            "lastChapterTitle": book_data["lastChapterTitle"],
            "lastScraped": datetime.datetime.now(),
            "totalChapters": book_data["totalChapters"],
            "directory": book_data["directory"],
            "imported": book_data["imported"],
            "edited": book_data.get("edited", False),  # Default to False if not present
            "aliases": book_data.get("aliases", [])  # Default to empty list if not present
        }
        db=Database.get_instance()
        savedBooks=db["Books"]
        if (check_existing_book("-1")):
            logging.warning(savedBooks.replace_one({"bookID": "-1"}, book))
        else:
            logging.warning(savedBooks.insert_one(book))






def remove_excess_spaces():
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find({"bookID":{"$ne":"-1"}})
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
        logging.warning(savedBooks.update_one({"bookID":result["bookID"]},{"$set":{'bookDescription':bookDescription, 'bookAuthor':bookAuthor}}))
#remove_excess_spaces()



import re
def fix_websiteHost_links():
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find({"bookID":{"$ne":"0"}})
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

def fill_existing_records():
    db = Database.get_instance()
    savedBooks = db["Books"]
    results = list(savedBooks.find({"bookID": {"$nin": ["-1", "0"]}}).sort('bookName', 1))
    for result in results:
        book = {
            "bookID": result["bookID"],
            "bookName": result["bookName"],
            "bookAuthor":result["bookAuthor"],
            "bookDescription": result["bookDescription"],
            "websiteHost": result["websiteHost"],
            "firstChapter": result["firstChapter"],
            "lastChapterID": result.get("lastChapterID", "N/A"),
            "lastChapterTitle": result.get("lastChapterTitle", "N/A"),
            "lastScraped": result["lastScraped"],
            "totalChapters": result["totalChapters"],
            "directory": result["directory"],
            "imported": result.get("imported", False),  # Default to False if not present
            "edited": result.get("edited", False),  # Default to False if not present
            "aliases": result.get("aliases", [])  # Default to empty list if not present
        }
        if "lastChapter" in results:
            if not (str(result["lastChapter"]).isdigit()):
                book["lastChapterID"] = -1
            else:
                book["lastChapterID"] = int(results["lastChapter"])
        
        logging.warning(savedBooks.replace_one({"_id": result["_id"]}, book))

#fill_existing_records()

def fix_existing_record_data_types():
    db = Database.get_instance()
    savedBooks = db["Books"]
    results = list(savedBooks.find({"bookID": {"$nin": ["-1", "0"]}}).sort('bookName', 1))
    for result in results:
        
        if not (str(result["firstChapter"])).isdigit():
            result["firstChapter"] = -1
        if not (str(result["lastChapterID"])).isdigit():
            result["lastChapterID"] = -1
            
        book = {
            "bookID": str(result["bookID"]),
            "bookName": str(result["bookName"]),
            "bookAuthor":str(result["bookAuthor"]),
            "bookDescription": result["bookDescription"],
            "websiteHost": result["websiteHost"],
            "firstChapter": int(result["firstChapter"]),
            "lastChapterID": int(result["lastChapterID"]),
            "lastChapterTitle": result["lastChapterTitle"],
            "lastScraped": result["lastScraped"],
            "totalChapters": int(result["totalChapters"]),
            "directory": result["directory"],
            "imported": result["imported"],
            "edited": result.get("edited", False),  # Default to False if not present
            "aliases": result.get("aliases", [])  # Default to empty list if not present
        }
        logging.warning(savedBooks.replace_one({"_id": result["_id"]}, book))

#fix_existing_record_data_types()

def update_entry(record):
    db=Database.get_instance()
    savedBooks=db["Books"]
    # Check if the record exists first
    existing = savedBooks.find_one({"bookID": record["bookID"]})
    if not existing:
        logging.warning(f"No record found for bookID {record['bookID']}. Update aborted.")
        return None
    # Update the record with new values from the dict
    result = savedBooks.update_one(
        {"bookID": record["bookID"]},
        {"$set": record}
    )
    logging.warning(f"Updated record for bookID {record['bookID']}: {result.raw_result}")
    return result
        











































def generate_userID():
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    userID=verifiedUsers.count_documents({})+1
    return userID


def create_new_user(userName, passWord):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    userID=generate_userID()
    results=verifiedUsers.find_one({"username":userName})
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
        write_to_logs("Function: create_new_user. Success: Created verified user for:"+result)
        return True
    else:
        write_to_logs("Function: create_new_user. Error: User already exists.")
    return False

def verify_user(userID):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    results=verifiedUsers.find_one({"userID":userID})
    if (results):
        result=str(verifiedUsers.update_one({"userID":userID},{"$set":{"verified":True}}))
        write_to_logs(result)
        return True
    return False

def is_verified_user(userID,username):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    results=verifiedUsers.find_one({"userID":int(userID)})
    if (results):
        #logging.warning(results["username"])
        #logging.warning(username)
        if (results["username"]==username):
            logging.warning("User is verified")
            return True
    logging.warning("User is not verified")
    return False

#is_verified_user("1","tes")

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

def get_unverified_users():
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    results=verifiedUsers.find({"verified":False})
    unverifiedUsers=[]
    if (results):
        for result in results:
            unverifiedUser = {
            "username": result["username"],
            "userID": result["userID"],
            "dateCreated": result["dateCreated"].strftime('%m/%d/%Y')
            }
            unverifiedUsers.append(unverifiedUser)
    return unverifiedUsers

def get_hashed_password(username):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    results=verifiedUsers.find_one({"username":username})
    if (results!=None):
        result=str(verifiedUsers.update_one({"username":username},{"$set":{"lastLogin":datetime.datetime.now()}}))
        write_to_logs(result)
        return results["password"]

def update_password(username,password):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    results=verifiedUsers.find_one({"username":username})
    if (results!=None):
        result=str(verifiedUsers.update_one({"username":username},{"$set":{"lastLogin":datetime.datetime.now(), "password":password}}))
        write_to_logs(result)
        return True
    return False
    

def get_userID(username):
    db=Database.get_instance()
    verifiedUsers=db["VerifiedUsers"]
    results=verifiedUsers.find_one({"username":username})
    if (results!=None):
        userID=results["userID"]
        result=str(userID)
        write_to_logs("function: get_userID. Success: Retrieved userID for:"+result)
        return str(userID)
    return None

def check_existing_reading_list(userID):
    db=Database.get_instance()
    userBookLibrary=db["UserLists"]
    results=userBookLibrary.find_one({"userID":userID})
    if (results==None):
        write_to_logs("Function: check_existing_reading_list. Error: User does not exist")
        return False
    else:
        return results

def get_Followed_Books(username):
    db=Database.get_instance()
    userBookLibrary=db["VerifiedUsers"]
    results=userBookLibrary.find_one({"username":username})
    
    logging.warning(results)
    userID=results["userID"]
    
    savedBooks=db["Books"]
    distinctSites=savedBooks.distinct("websiteHost")
    
    results=check_existing_reading_list(userID)
    followListResults=[]
    if (results):
        followList=results["followList"]
        for site in distinctSites:
            bookList=[]
            for i in followList:    
                logging.warning(i)

                bookData=savedBooks.find_one({"bookID":i,"websiteHost":site})
                if (bookData):
                    book =[
                        bookData["bookID"],
                        bookData["bookName"],
                        bookData["bookAuthor"],
                        bookData["bookDescription"],
                        bookData["websiteHost"],
                        bookData["lastScraped"].strftime('%m/%d/%Y'),
                        bookData["lastChapterTitle"]
                    ]
                    #book=[bookData["bookID"],bookData["bookName"],(bookData["lastScraped"]).strftime('%m/%d/%Y'),bookData["lastChapterTitle"]]
                    bookList.append(book)
            if (bookList):
                followListResults.append([site,bookList])
        logging.warning(followListResults)
        write_to_logs("Function: get_Followed_Books. Success: Retrieved followed books for userID:"+str(userID))
        return followListResults
    return None

#logging.warning(get_Followed_Books("tes"))

    
#Must use a userID. Therefore, using username login, get the user's ID and start using that.
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
            result=str(userBookLibrary.update_one(record))
            write_to_logs("Function: create_user_reading_list. Success: Updated user reading list for:"+result)

        else:
            record={
                "userID": kwargs["userID"],
                "followList":kwargs["followList"]
            }
            result=str(userBookLibrary.insert_one(record))
            write_to_logs("Function: create_user_reading_list. Success: Created user reading list for:"+result)
    else:
        write_to_logs("Function: create_user_reading_list. Error: User does not exist; Therefore we cannot make a reading list.")

def remove_from_user_reading_list(userID, bookID):
    db=Database.get_instance()
    savedBooks=db["UserLists"]
    results=check_existing_reading_list(int(userID))
    if (results):            
        if (bookID in results["followList"]):
            results["followList"] = [b for b in results["followList"] if b != str(bookID)]
            savedBooks.update_one(
                {"userID": results["userID"]},
                {"$set": {"followList": results["followList"]}}
            )
            logText="Function: remove_from_user_reading_list. Sucess: Removed from user reading list:"+str(results)
            logging.warning(logText)
            write_to_logs(logText)
            return True
    else:
        logText="Function: remove_from_user_reading_list. Error: User does not exist."
        logging.warning(logText)
        write_to_logs("Function: remove_from_user_reading_list. Error: User does not exist.")
        return False

def add_to_user_reading_list(userID, bookID):
    db=Database.get_instance()
    savedBooks=db["UserLists"]
    results=check_existing_reading_list(int(userID))
    
    if (results):
        if (bookID not in results["followList"]):
            results["followList"].append(str(bookID))
            result=savedBooks.update_one({"userID":results["userID"]},{"$set":{"followList":results["followList"]}})
            logText="Function: add_to_user_reading_list. Sucess: Added to user reading list:"+str(result)
            write_to_logs(logText)
            logging.warning(logText)
            return True
    else:
        logText="Function: add_to_user_reading_list. Error: User does not exist."
        logging.warning(logText)
        write_to_logs("Function: add_to_user_reading_list. Error: User does not exist.")
        return False
    
#add_to_user_reading_list(userID=1,addList=[1,2,3,4,5])
    
def check_developer(username):
    db=Database.get_instance()
    savedBooks=db["VerifiedUsers"]
    results=savedBooks.find_one({"username":username, "developer":True})
    if (results):
        write_to_logs("Function: check_developer. Success: User is a developer.")
        return True
    
    write_to_logs("Function: check_developer. Error: User is not a developer.")
    return False
    


#create_user_reading_list(userID=2,followList=[1,2,3,4,5])





def get_all_book_titles():
    db=Database.get_instance()
    savedBooks=db["Books"]
    results=savedBooks.find({"bookID":{"$nin":["-1","0"]}})
    bookTitles=[]
    for result in results:
        bookTitles.append(result["bookName"])
    return bookTitles



def get_total_imported_books() -> int:
    db=Database.get_instance()
    savedBooks=db["Books"]
    results = savedBooks.find({"bookID": {"$nin": ["-1", "0"]}, "imported": True})
    total_imported=0
    for result in results:
        total_imported+=1
    return total_imported

def get_all_imported_books() -> list:
    db=Database.get_instance()
    savedBooks=db["Books"]
    results = savedBooks.find({"bookID": {"$nin": ["-1", "0"]}, "imported": True})
    all_imported=[]
    for result in results:
        #logging.warning(result)
        data = [[result["bookID"], result["bookName"], result["bookAuthor"], result["imported"]]]
        all_imported.append(data)
    return all_imported

# logging.warning(get_total_imported_books())
# logging.warning(get_all_imported_books())

#We only care about editing books that have been imported as their contents may be out of order.
def get_total_non_edited_books()-> int:
    db=Database.get_instance()
    savedBooks=db["Books"]
    results = savedBooks.find({"bookID": {"$nin": ["-1", "0"]}, "imported": True, "edited": False})
    total_edited=0
    for result in results:
        total_edited+=1
    return total_edited

def get_all_non_edited_books() -> list:
    db=Database.get_instance()
    savedBooks=db["Books"]
    results = savedBooks.find({"bookID": {"$nin": ["-1", "0"]}, "imported": True, "edited": False})
    all_non_edited=[]
    for result in results:
        data = [[result["bookID"], result["bookName"], result["bookAuthor"], result["edited"]]]
        all_non_edited.append(data)
    return all_non_edited




















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



