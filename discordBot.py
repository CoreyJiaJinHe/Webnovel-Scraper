import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import logging
import asyncio
import threading 
import scrape

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
        

import mongodbBotChannels

@bot.command(aliases=['epub','getnovel'])
async def getNovel(ctx):
    if(checkChannel(ctx)):
        novelURL=ctx.message.content.split(' ')[1]
        
        
        ##THIS DOES and DOES NOT WORK.
        #This times out heartbeat but somehow manages to send the epub???
        #task1=asyncio.create_task(scrape.mainInterface(novelURL))
        #thread = threading.Thread(target=scrape.mainInterface(novelURL))
        #thread.start()
        #thread.join()
        
        
        #task = asyncio.create_task(await scrape.mainInterface(novelURL))
        #book=await task
        
        book=await scrape.mainInterface(novelURL)
        
        #https://docs.python.org/3/library/asyncio-eventloop.html#
        #https://docs.python.org/3/library/asyncio-task.html#coroutine
        
        #asyncio.create_task(scrape.mainInterface(novelURL))
        #The blocking code is requests library. To change, I need to migrate to aiohttp. Other libraries could also be blocking.
        logging.warning(book)
        if(book==None or book==False):
            await ctx.send("Invalid URL")
            return
        else:
            await ctx.send("Novel Found. Generating epub")
            #This happens because i'm using asyncio.gather
            if (book is list):
                book=str(book)
            #await os.stat(book)
            
            if os.path.getsize(book) > 8*1024*1024:
                await ctx.send("File too large")
                await ctx.send("Please download the file from the link below")
                await ctx.send(PUBLIC_URL)
                return
            
            file= discord.File(book)
            await ctx.send(file=file)
        
        
    #await ctx.send(novelURL)
    
    

@bot.command(aliases=['addchannel'])
async def addChannel(ctx):
    channel = ctx.channel
    channelName=channel.name
    channelID=channel.id
    serverID=channel.guild.id
    serverName=channel.guild.name
    await ctx.send(mongodbBotChannels.insert_server_data(serverID,serverName, channelID,channelName))
    

@bot.command(aliases=['removechannel'])
async def removeChannel(ctx):
    channel = ctx.channel
    channelID=channel.id
    serverID=channel.guild.id
    await ctx.send(mongodbBotChannels.remove_existing_channel(serverID, channelID))
    
def checkChannel(ctx):
    channel = ctx.channel
    channelID=channel.id
    serverID=channel.guild.id
    return mongodbBotChannels.check_already_allowed(serverID, channelID)
        
bot.run(''+DISCORD_TOKEN+'',log_handler=None)