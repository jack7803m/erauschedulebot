# ERAU Schedule Bot

> This is an old project that has been reuploaded for archival purposes. It's one of the first projects that I coded! It's not used or even particularly useful anymore given some of the library and API updates, but I wanted to keep it here to look back on.

## Description

This application is a python program that manages a Discord bot with the purpose of finding people in an Embry-Riddle server with the same classes or professor. The goal of this project is to allow students to upload their schedules and easily find other students who are in the same class or have the same professor to make study groups or just collaborate in general. This is primarily intended for pre-freshman students who have already registered.

In order to function, the bot allows students to upload their schedules in PDF format (downloaded directly from the ERAU Campus Solutions webapp). Once uploaded, the file is downloaded by the bot and scraped - this scraped data is added to a database for quick retrieval later. 

The bot exposes several commands, all of which have a help/usage message associated for ease-of-use. 

## Dependencies

### Python Packages

You can install the required python packages by running `pip install -r ./requirements.txt` from the root of the project.

### Database

This project relies on a MongoDB database running locally. To work out of the box, the database should be configured with default settings and no password. The only configuration required should be creating one database called `scheduledb` and a collection called `schedules` . This is where everything will be stored.

### Environment (.env)

There needs to exist a `.env` file within the root directory of the project with the format:

```
DISCORD_TOKEN=insert_token_here
```

...replacing `insert_token_here` with your Discord Bot API key. 
