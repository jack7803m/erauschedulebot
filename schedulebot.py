from discord.ext.commands import Bot
import discord

import os
import re
from dotenv import load_dotenv

import requests
import random
import string
import scheduling
import dbmanagement


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

help_command = discord.ext.commands.DefaultHelpCommand(no_category="Commands")
# if i use the variable cmd_pfx, it uses the variable name instead of the value.
# if it ever needs to be changed, change both
cmd_pfx = "+"
client = Bot(command_prefix="+", help_command=help_command)


async def makeEmbeds(title, description, unformatted_data):
    embed_list = []
    body_list = []
    embed_color = 0xD8B554
    full_body = ""

    # pagination to make sure that the embeds don't go over the character limit
    for classname in unformatted_data.keys():
        full_body += f"<TITLE>{classname}\n"
        if unformatted_data[classname] == []:
            full_body += "None\n"
        else:
            for student in unformatted_data[classname]:
                if len(full_body) > 800:
                    body_list.append(full_body)
                    full_body = ""
                full_body += f"  - {student}\n"
    body_list.append(full_body)

    # go through the pages and convert them into embeds
    for i in range(len(body_list)):
        body = body_list[i]
        current_title = ""
        current_value = ""
        if description != "":
            description = description + "\n"

        # if it's the first embed, make the title and description the ones passed in
        if i == 0:
            current_embed = discord.Embed(
                title=title, description=description, color=embed_color
            )
        # otherwise, just make the title "continued"
        else:
            current_embed = discord.Embed(
                title="Continued", description="\n", color=embed_color
            )

        # go through each line of the body and add it to the embed
        for line in body.splitlines():
            r = re.match("<TITLE>(.+)", line)
            if r != None:
                if current_title == "" and current_value == "":
                    pass
                elif current_title == "" and current_value != "":
                    last_embed = embed_list[i - 1]
                    name = last_embed.fields[-1].name
                    current_embed.add_field(
                        name=f"{name} Continued", value=current_value, inline=False
                    )
                    current_value = ""
                else:
                    current_embed.add_field(
                        name=current_title, value=current_value, inline=False
                    )
                    current_value = ""
                current_title = r.groups()[0]
            else:
                current_value += f"{line}\n"

        # add the last field to the embed
        if current_title == "" and current_value != "":
            last_embed = embed_list[i - 1]
            name = last_embed.fields[-1].name
            current_embed.add_field(name=name, value=current_value, inline=False)
        elif current_value == "":
            current_embed.add_field(name=current_title, value="None", inline=False)
        else:
            current_embed.add_field(
                name=current_title, value=current_value, inline=False
            )
        embed_list.append(current_embed)

    return embed_list


@client.event
async def on_ready():
    print(f"{client.user} has connected to Discord")


@client.command(
    name="uploadschedule",
    help=f'Usage: upload schedule pdf and "comment" it with {cmd_pfx}uploadschedule\nUsed to upload your class schedule to the bot.\n'
    + 'To get to the document, go to: ERNIE --> Campus Solutions Student Homepage --> (Make sure "Student Homepage" is at the top now) --> Manage Classes --> View My Classes --> Print Schedule (It\'s a blue link in the top right corner of the page) --> Download the PDF it gives you\nNOTE: Do not Print To PDF, just click the "Print Schedule" link and then download the file that it gives you - it\'s already a pdf.',
)
async def uploadschedule(ctx):
    # making sure that the user actually uploaded a file. if so, save the url to attachment_url and if not, then send a message and return
    try:
        attachment_url = ctx.message.attachments[0].url
    except IndexError:
        await ctx.send(
            f'No attachment provided! You must upload a file and "comment" it with {cmd_pfx}uploadschedule.'
        )
        return

    # checking to see if it's a pdf file
    # this isn't foolproof at all but it's fine for now
    attachment_filename = ctx.message.attachments[0].filename
    if attachment_filename[-4:] != ".pdf":
        await ctx.send(
            "That is not a pdf. Please upload the document that you downloaded from ERNIE."
        )
        return

    # the existence of an attachment has been confirmed. this signals that the document is uploading properly (even though it's technically downloading)
    await ctx.send("Uploading and processing...")

    # set the intended filename to a big random number and download/save the file.
    # this could technically download malware, but we'll pretend that is not possible for now
    filename = ("".join(random.choice(string.digits) for x in range(16))) + ".pdf"
    filepath = f"schedules/{filename}"
    with open(filepath, "wb") as outfile:
        outfile.write(requests.get(attachment_url).content)

    # run the file through the processor, returns the dictionary to be added to the database
    try:
        newdbdata = scheduling.extract_data(filepath)
    except NotImplementedError:
        os.remove(filepath)
        await ctx.send(
            "That does not seem to be the right file. Make sure you are uploading the correct file that you downloaded from ERNIE."
        )
        return

    newdbdata["filename"] = filename
    newdbdata["username"] = ctx.message.author.name
    newdbdata["saved_nickname"] = ctx.message.author.display_name
    newdbdata["discord_id"] = ctx.message.author.id

    # attempt to add the data to the database; perform check first and update if necessary, otherwise insert data
    mongo = dbmanagement.MongoManage()
    if mongo.checkExisting(newdbdata) is True:
        await ctx.send(
            "It seems like you are already in the database! Your information has been updated."
        )
    else:
        mongo.insertNew(newdbdata)
        await ctx.send(
            f"Successfully uploaded! Run {cmd_pfx}checkschedule to see if anyone else who has uploaded will be in your classes!"
        )

    # if everything passes up to this point, all the necessary data should be loaded into the database so it can be closed
    mongo.closeConnection()


@client.command(
    name="checkschedule",
    help=f"Usage: {cmd_pfx}checkschedule \nChecks the bot's database for anyone who will be in your classes.\nOptionally, you can add a studentid like '+checkschedule 1234567' and it will return the same thing, but for that student id.",
)
async def checkschedule(ctx, studentid="optional"):
    # basically just checking if student id is entered first, and then also if it is even a number at all
    if studentid == "optional":
        lookup_type = "discord_id"
        lookup_index = ctx.message.author.id
    else:
        try:
            lookup_type = "studentid"
            # the student id is stored as a string in the db so it needs to be converted back, but check if it's a number first
            lookup_index = str(int(studentid))
        except ValueError:
            await ctx.send(
                "If you use the optional student ID argument, please only input your student ID number."
            )
            return

    mongo = dbmanagement.MongoManage()
    try:
        unformatted_response = mongo.findSimilarSection(
            lookup_index=lookup_index, lookup_type=lookup_type
        )
        student_name = mongo.getName(lookup_index=lookup_index, lookup_type=lookup_type)
        response_embeds = await makeEmbeds(
            title=f'"{student_name}" Sections',
            description=f'List of classes and sections of "{student_name}" and other students taking the same ones.',
            unformatted_data=unformatted_response,
        )
    except FileNotFoundError:
        await ctx.send(
            "No entries found in my database. Please upload your schedule; try: '+help uploadschedule'. If you have already uploaded your schedule but are now having issues, run '+help reassociate'"
        )
        mongo.closeConnection()
        return

    mongo.closeConnection()
    for embed in response_embeds:
        await ctx.send(embed=embed)


@client.command(
    name="checkclass",
    help=f"Usage: {cmd_pfx}checkclass <courseID>\nExample: {cmd_pfx}checkclass MA 241\nReturns the list of people taking a given class.",
)
async def checkclass(ctx, *, courseid="append"):
    # check if user input anything
    if courseid == "append":
        await ctx.send(
            f"Please append the courseID to that command. Ex: {cmd_pfx}checkclass MA 241"
        )
        return
    # check if the courseID input is strictly alphanumeric
    allowed_chars = set(
        "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ "
    )
    validate_input = set(courseid)
    if validate_input.issubset(allowed_chars) == False:
        await ctx.send(f"The courseID must be alphanumeric.")
        return

    # at this point, it has been verified that the user has entered alphanumeric data. now we pass it to the db to find
    mongo = dbmanagement.MongoManage()
    try:
        unformatted_response = mongo.findStudentsWithClass(courseid)
        response_embeds = await makeEmbeds(
            title=f"Students taking {courseid}",
            description="",
            unformatted_data=unformatted_response,
        )
    except SyntaxError:
        await ctx.send(
            f'The courseID "{courseid}" does not seem to exist in the database. Either nobody is taking the class or it was typed incorrectly.'
        )
        mongo.closeConnection()
        return

    mongo.closeConnection()
    for embed in response_embeds:
        await ctx.send(embed=embed)


# this will check the database for students that have the same prof and will send a list of them
@client.command(
    name="checkprof",
    help=f"Usage: {cmd_pfx}checkprof <courseID>\nExample: {cmd_pfx}checkclass MA 241\nReturns a menu/list of professors for a given class and then shows everyone in any of a given professor's classes.",
)
async def checkprof(ctx, *, courseid="append"):
    # check if user input anything
    if courseid == "append":
        await ctx.send(
            f"Please append the courseID to that command. Ex: {cmd_pfx}checkclass MA 241"
        )
        return
    # check if the courseID input is strictly alphanumeric
    allowed_chars = set(
        "1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ "
    )
    validate_input = set(courseid)
    if validate_input.issubset(allowed_chars) == False:
        await ctx.send(f"The courseID must be alphanumeric.")
        return

    # at this point, it has been verified that the user has entered alphanumeric data. now we pass it to the db to find
    mongo = dbmanagement.MongoManage()
    # get all the professors for the given class, send the list to the user
    professorList = mongo.queryProfs(courseid)
    current_embed = discord.Embed(
        title=f"Professors for {courseid}",
        description="Enter a number to choose.",
        color=0x00529B,
    )
    professorsString = ""
    i = 0
    check_exists = 0
    for instructor in professorList:
        i += 1
        check_exists = 1
        professorsString += f"{i}: {instructor}\n"
    if check_exists == 0:
        await ctx.send(
            f'The courseID "{courseid}" does not seem to exist in the database. Either nobody is taking the class or it was typed incorrectly.'
        )
        mongo.closeConnection()
        return
    current_embed.add_field(name=courseid, value=professorsString, inline=False)
    await ctx.send(embed=current_embed)

    # wait for the user to input a number
    def check(m):
        return m.author == ctx.message.author and m.channel == ctx.message.channel

    while True:
        try:
            user_input = await client.wait_for("message", timeout=30.0, check=check)
        except:
            await ctx.send("Sorry! Timed out.")
            return

        # check if the user input is a number
        try:
            user_input = int(user_input.content)
        except ValueError:
            await ctx.send("You did not enter a number. Please try again.")
            continue

        # check if the user input is in the range of the professor list
        if user_input >= 1 and user_input <= len(professorList):
            # get the professor the user chose
            prof = professorList[user_input - 1]
            break
        else:
            await ctx.send("That is not a valid number! Please try again.")

    unformatted_response = mongo.findStudentswithProfessor(prof)
    response_embeds = await makeEmbeds(
        title=f"Students with {prof} for {courseid}",
        description="",
        unformatted_data=unformatted_response,
    )

    mongo.closeConnection()
    for embed in response_embeds:
        await ctx.send(embed=embed)


@client.command(
    name="sourcecode",
    help=f"Usage: {cmd_pfx}sourcecode \nLinks to the github for my source code :)",
)
async def sourcecode(ctx):
    await ctx.send("https://github.com/jack7803m/erauschedulebot")


@client.command(
    name="uploads",
    help=f"Usage: {cmd_pfx}uploads \nReturns the amount of schedules/uploads in the database.",
)
async def uploads(ctx, *, campus="all"):
    if campus in ["daytona", "db", "daytona beach", "florida", "fl", "best campus"]:
        search_index = "daytona"
    elif campus in ["prescott", "pc", "arizona", "az", "worse campus"]:
        search_index = "prescott"
    elif campus in ["all", "total"]:
        search_index = None
    else:
        await ctx.send(f'Campus "{campus}" is not currently a valid campus name.')
        return

    mongo = dbmanagement.MongoManage()
    count = mongo.amountOfDocs(search_index)
    mongo.closeConnection()

    if campus == "all":
        await ctx.send(f"A total of {count} students have uploaded their schedules.")
    else:
        await ctx.send(
            f'A total of {count} students at "{campus}" have uploaded their schedules.'
        )


client.run(TOKEN)
