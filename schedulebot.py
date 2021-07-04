from discord.ext.commands import Bot
import discord

import os
from dotenv import load_dotenv
#from asyncio import sleep
import requests
import random
import string

import scheduling
import dbmanagement

### need to do 
#

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

help_command = discord.ext.commands.DefaultHelpCommand(no_category = 'Commands')
cmd_pfx = '+'
client = Bot(command_prefix='+', help_command=help_command)

#catuwu = client.get_emoji(841142074593378344)
#sadyeehaw = client.get_emoji(840632884914028544)

#should this be here? nope, but im not making a new file for it. fuck you
async def makeEmbed(title, description, unformatted_data):
    embed_color = 0xD8B554
    if description != '': description = description + '\n'
    response_embed = discord.Embed(title=title, description=description, color=embed_color)
    for field_title in unformatted_data.keys():
        name_list = unformatted_data[field_title]
        field_value = ''
        if name_list == []:
            field_value = 'None'
        else:
            for name in name_list:
                field_value = field_value + f'  - {name}\n'
        response_embed.add_field(name=field_title, value=field_value, inline=False)
    
    return response_embed


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord')
    

@client.event
async def on_message(message):
    if message.author == client.user:
        pass
    elif client.user.mentioned_in(message) or ':catuwu:' in message.content: #or discord.utils.get(message.author.roles, name='Weeb') is not None
        catuwu = client.get_emoji(841142074593378344)
        await message.add_reaction(catuwu)
    await client.process_commands(message)


@client.command(name='uploadschedule', 
                help = f'Usage: upload schedule pdf and "comment" it with {cmd_pfx}uploadschedule\nUsed to upload your class schedule to the bot.\n' + 
                'To get to the document, go to: ERNIE --> Campus Solutions Student Homepage --> (Make sure "Student Homepage" is at the top now) --> Manage Classes --> View My Classes --> Print Schedule (It\'s a blue link in the top right corner of the page) --> Download the PDF it gives you\nNOTE: Do not Print To PDF, just click the "Print Schedule" link and then download the file that it gives you - it\'s already a pdf.')
async def uploadschedule(ctx):
    
    #making sure that the user actually uploaded a file. if so, save the url to attachment_url and if not, then send a message and return
    try:
        attachment_url = ctx.message.attachments[0].url
    except IndexError:
        await ctx.send(f"No attachment provided! You must upload a file and \"comment\" it with {cmd_pfx}uploadschedule.")
        return
    
    #checking to see if it's a pdf file
    #this isn't foolproof at all but it's fine for now
    attachment_filename = ctx.message.attachments[0].filename
    if '.pdf' not in attachment_filename:
        await ctx.send("That is not a pdf. Please upload the document that you downloaded from ERNIE.")
        return
    
    #the existence of an attachment has been confirmed. this signals that the document is uploading properly (even though it's technically downloading)
    await ctx.send("Uploading and processing...")
    
    #set the intended filename to a big random integer and download/save the file. 
    #this could technically download malware, but we'll pretend that is not possible for now
    filename = (''.join(random.choice(string.digits) for x in range(16))) + '.pdf'
    filepath = f'schedules/{filename}'
    with open(filepath, 'wb') as outfile:
        outfile.write(requests.get(attachment_url).content)
    
    #run the file through the processor, returns the dictionary to be added to the database
    try:
        newdbdata = scheduling.extract_data(filepath)
    except NotImplementedError:
        os.remove(filepath)
        await ctx.send("That does not seem to be the right file. Make sure you are uploading the correct file that you downloaded from ERNIE.")
        return
    
    newdbdata['filename'] = filename
    newdbdata['username'] = ctx.message.author.name
    newdbdata['saved_nickname'] = ctx.message.author.display_name
    newdbdata['discord_id'] = ctx.message.author.id

    #get the user's roles, perform role checking to ensure that his/her campus role is correct
    role_names = [role.name for role in ctx.message.author.roles]
    if "Prescott Student" in role_names and "Daytona Student" in role_names:
        await ctx.send("Your roles are set incorrectly, unless you are somehow registered at both campuses. Please fix your roles so I can function properly :)")
        return
    elif "Prescott Student" in role_names: campus = 'prescott'
    elif "Daytona Student" in role_names: campus = 'daytona'
    else: await ctx.send(f"You do not have a campus role! Please set your campus in <#832434178523791391>"); return
    if campus is not newdbdata['campus']:
            ctx.send(f"Your campus role conflicts with your schedule. Please update your campus role or upload the correct schedule.")
            return

    #attempt to add the data to the database; perform check first and update if necessary, otherwise insert data
    mongo = dbmanagement.MongoManage()
    if mongo.checkExisting(newdbdata) is True:
        await ctx.send("It seems like you are already in the database! Your information has been updated.")
    else:
        mongo.insertNew(newdbdata)
        await ctx.send(f"Successfully uploaded! Run {cmd_pfx}checkschedule to see if anyone else who has uploaded will be in your classes!")
        
    #if everything passes up to this point, all the necessary data should be loaded into the database so it can be closed
    mongo.closeConnection()


@client.command(name='checkschedule', 
                help = f'Usage: {cmd_pfx}checkschedule \nChecks the bot\'s database for anyone who will be in your classes.\nOptionally, you can add a studentid like \'+checkschedule 1234567\' and it will return the same thing, but for that student id.')
async def checkschedule(ctx, studentid = 'optional'):
    #basically just checking if student id is entered first, and then also if it is even a number at all
    if studentid == 'optional': 
        lookup_type = 'discord_id'
        lookup_index = ctx.message.author.id
    else:
        try:
            lookup_type = 'studentid'
            lookup_index = int(studentid)
            # the student id is stored as a string in the db so it needs to be converted back
            lookup_index = str(lookup_index)
        except ValueError:
            await ctx.send('If you use the optional student ID argument, please only input your student ID number.')
            return

    
    mongo = dbmanagement.MongoManage()
    try:
        unformatted_response = mongo.findSimilarSection(lookup_index = lookup_index, lookup_type = lookup_type)
        student_name = mongo.getName(lookup_index = lookup_index, lookup_type = lookup_type)
        response_embed = await makeEmbed(title=f'"{student_name}" Sections', description=f'List of classes and sections of "{student_name}" and other students taking the same ones.', unformatted_data=unformatted_response)
    except FileNotFoundError:
        await ctx.send('No entries found in my database. Please upload your schedule; try: \'+help uploadschedule\'')
        return

    mongo.closeConnection()
    await ctx.send(embed=response_embed)


'''@client.command(name='checkclasses', 
                help = f'Usage: {cmd_pfx}checkclasses <id> \nExample: {cmd_pfx}checkclasses 1234567\nChecks the bot\'s database for anyone who has the same class as you, regardless of section/professor/time.')
async def checkclasses(ctx, studentid = 'append'):
    if studentid == 'append': 
        await ctx.send(f'Please append your student number to that command. Ex: {cmd_pfx}checkclasses 1234567')
        return
    try:
        studentid = int(studentid)
    except ValueError:
        await ctx.send('Please input your student id number only.')
        return
    
    studentid = str(studentid)
    
    mongo = dbmanagement.MongoManage()
    try:
        unformatted_response = mongo.findSimilarClass(studentid)
        student_name = mongo.getName(studentid, lookup_type='studentid')
        response_embed = await makeEmbed(title=f'"{student_name}" Classes', description=f'List of classes of "{student_name}" and other students taking those classes.', unformatted_data=unformatted_response)
    except FileNotFoundError:
        await ctx.send('That student ID does not seem to be in the database.')
        return
        
    mongo.closeConnection()
    await ctx.send(embed=response_embed)'''
    
    
@client.command(name = 'checkclass',
                help = f'Usage: {cmd_pfx}checkclass <courseID>\nExample: {cmd_pfx}checkclass MA 241\nReturns the list of people taking a given class.')
async def checkclass(ctx, *, courseid = 'append'):
    #check if user input anything
    if courseid == 'append':
        await ctx.send(f'Please append the courseID to that command. Ex: {cmd_pfx}checkclass MA 241')
        return
    #check if the courseID input is strictly alphanumeric
    allowed_chars = set("1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ")
    validate_input = set(courseid)
    if validate_input.issubset(allowed_chars) == False:
        await ctx.send(f'The courseID must be alphanumeric.')
        return
    
    #at this point, it has been verified that the user has entered alphanumeric data. now we pass it to the db to find
    mongo = dbmanagement.MongoManage()
    try:
        unformatted_response = mongo.findStudentsWithClass(courseid)
        response_embed = await makeEmbed(title=f'Students taking {courseid}', description='', unformatted_data=unformatted_response)
    except SyntaxError:
        await ctx.send(f'The courseID "{courseid}" does not seem to exist in the database.')
        return
    
    mongo.closeConnection()
    await ctx.send(embed=response_embed)
    
    
@client.command(name = 'uploads',
                help = f'Usage: {cmd_pfx}uploads \nReturns the amount of schedules/uploads in the database.')
async def uploads(ctx, *, campus = 'all'):
    if campus in ['daytona', 'db', 'daytona beach', 'florida', 'fl', 'best campus']:
        search_index = 'daytona'
    elif campus in ['prescott', 'pc', 'arizona', 'az']:
        search_index = 'prescott'
    elif campus in ['all', 'total']:
        search_index = None
    else: await ctx.send(f"Campus \"{campus}\" is not currently a valid campus name."); return

    mongo = dbmanagement.MongoManage()
    count = mongo.amountOfDocs(search_index)
    mongo.closeConnection()
    
    if campus == 'all':
        botmessage = await ctx.send(f'A total of {count} students have uploaded their schedules.')
    else:
        botmessage = await ctx.send(f"A total of {count} students at \"{campus}\" have uploaded their schedules.")
    
    #sad reaction for low count
    if count < 0.20 * ctx.guild.member_count:
        sadyeehaw = client.get_emoji(840632884914028544)
        await ctx.message.add_reaction(sadyeehaw)
        await botmessage.add_reaction(sadyeehaw)
        
   
#if i ever get around to adding a whitelist to the minecraft server, this will be useful
'''import mcinterface
RCON_PASSWORD = os.getenv('RCON_PASSWORD')
@client.command(name = 'whitelist',
                help = f'Note: Used for community minecraft server\nUsage: {cmd_pfx}whitelist <username> bedrock/java\nEx: {cmd_pfx}whitelist Jack7803M java\nWhitelists the given username on the minecraft server.')
async def whitelist(ctx, username = None, game_type = 'java'):
    
    
    response = await mcinterface.whitelistUser(username=username, rcon_password=RCON_PASSWORD, game_type = game_type.lower())
    if response == False:
        await ctx.send('Error: Bad username format.')
    elif response == True:
        await ctx.send('Success!')'''

    
client.run(TOKEN)