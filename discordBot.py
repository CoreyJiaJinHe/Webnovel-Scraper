import discord
import os
from discord.ext import commands
from dotenv import load_dotenv
import logging

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
        book=scrape.mainInterface(novelURL)
        if(book==None):
            await ctx.send("Invalid URL")
            return
        else:
            await ctx.send("Novel Found. Generating epub")
            os.stat(book)
            if os.path.getsize(book) > 8*1024*1024:
                await ctx.send("File too large")
                await ctx.send("Please download the file from the link below")
                await ctx.send(PUBLIC_URL)
                return
            
            file=discord.File(book)
            await ctx.send(file=file)
        
        
    #await ctx.send(novelURL)
    
    

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
        
bot.run(''+DISCORD_TOKEN+'')