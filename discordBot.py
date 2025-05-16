import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import logging
import asyncio
import threading 
import refactor as scrape
import queue

load_dotenv()
PUBLIC_KEY=os.getenv('PUBLIC_KEY')
DISCORD_TOKEN=os.getenv('DISCORD_TOKEN')
PUBLIC_URL =os.getenv('PUBLIC_URL')

    
intents=discord.Intents.default()
intents.message_content=True


bot = commands.Bot(command_prefix='!',intents=intents)

@bot.command()
async def test(ctx):
    if(checkChannel(ctx)):
        await ctx.send("You tested successfully")
        

import mongodb


bookQueue=queue.Queue()

@bot.command(aliases=['epub','getnovel'])
async def getNovel(ctx):
    logging.warning(checkChannel(ctx))
    if(checkChannel(ctx)):
        novelURL=ctx.message.content.split(' ')[1]
        global bookQueue
        bookQueue.put([novelURL,ctx.channel.id])
        
        logging.warning(f"Novel URL: {novelURL}")
        await ctx.send("Request received. Trying to get now.")
        await createThreads()
    
#implement concurrency limit. I dont want to be overloaded with requests.

cookie=None
@bot.command(aliases=['cookie'])
async def setCookie(ctx):
    global cookie
    cookie=ctx.message.content.split(' ')[1]
    await ctx.send(f"Cookie set to {cookie}")


sem = asyncio.Semaphore(2) #Limit concurrent tasks
async def createThreads():
    global bookQueue
    if not bookQueue.empty():
        logging.warning(f"Book Queue: {bookQueue.qsize()}")
        async with sem:
            url, channelID = bookQueue.get()
            global cookie
            book = await scrape.main_interface(url, cookie)  # Await the coroutine directly
            await sendChannelFile(channelID, book)
#The blocking code is requests library. To change, I need to migrate to aiohttp. Other libraries could also be blocking.

    
async def sendChannelFile(channelID,file):
    channel = bot.get_channel(channelID)
    if(file==None or file==False):
        await channel.send("Invalid URL")
        return
    else:
        await channel.send("Novel Found. Generating epub")
        
        if isinstance(file, list):
            file = ''.join(file)  # Join list elements into a single string
            logging.warning(file)
        #await os.stat(book)
        
        if os.path.getsize(file) > 8*1024*1024:
            await channel.send("File too large")
            await channel.send("Please download the file from the link below")
            await channel.send(PUBLIC_URL)
            return
        
        discord_file= discord.File(file)
        await channel.send(file=discord_file)
#Idea: Create a main interface command that will create threads to call scrape.py
#Create a queue to process multiple epub requests in sequence
#use global variables to share the file/directory link

@bot.command(aliases=['addchannel'])
async def addChannel(ctx):
    channel = ctx.channel
    channelName=channel.name
    channelID=channel.id
    serverID=channel.guild.id
    serverName=channel.guild.name
    await ctx.send(mongodb.insert_server_data(serverID,serverName, channelID,channelName))
    

@bot.command(aliases=['removechannel'])
async def removeChannel(ctx):
    channel = ctx.channel
    channelID=channel.id
    serverID=channel.guild.id
    await ctx.send(mongodb.remove_existing_channel(serverID, channelID))
    
def checkChannel(ctx):
    channel = ctx.channel
    channelID=channel.id
    serverID=channel.guild.id
    return mongodb.check_already_allowed(serverID, channelID)
     
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    await bot.change_presence(activity=discord.Game(name="I am online"))
    channel=await bot.fetch_channel(1358957302085849188) or await bot.get_channel(1358957302085849188)
    #await channel.send("I am online")   
    #print(f'We have sent a message as {bot.user} to {channel}')

@bot.command(aliases=['clear','purge'])
async def clear_messages(ctx, limit:int=1):
    this_channel=ctx.channel.id
    channel=bot.get_channel(int(this_channel))
    if (0<limit<=100):
        if (checkChannel(ctx)):  
            deleted=await channel.purge(limit=limit) #,check=is_me
            await channel.send(f'Deleted {len(deleted)} message(s)')
        else:
            await ctx.send("I am not authorized to delete other channel messages")
            
bot.run(''+DISCORD_TOKEN+'',log_handler=None)

    
# "serverID": 580433045501378600,
# "serverName": "Chaotic Tavern ™",
# "channelID": [
# 1358957302085849000
# ],