# this file contains all the functions used for minecraft commands
# at the time of creation, this is only being used for whitelisting

from mcrcon import MCRcon


def whitelistUser(username, rcon_password, game_type):
    
    #filter username for generally allowed characters
    #may have to later be adjusted for bedrock users
    allowed_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_ ')
    input_validate = set(username)
    if input_validate.issubset(allowed_chars) == False:
        return False
    
    #make this work for bedrock players. needs to add a * in front of the username
    if game_type != 'java' and game_type != 'pc':
        username = f'*{username}'
    
    #send command to whitelist
    with MCRcon('127.0.0.1', rcon_password) as mcsocket:
        mcsocket.command(f'/whitelist add {username}')
    return True