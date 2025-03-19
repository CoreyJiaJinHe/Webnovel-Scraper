from pymongo import MongoClient
import os
import logging

from dotenv import load_dotenv
load_dotenv()


MONGODB_URL=os.getenv('MONGODB_URI')
myclient=MongoClient(MONGODB_URL)
mydb=myclient["BotServers"]
botServers=mydb["Servers"]

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