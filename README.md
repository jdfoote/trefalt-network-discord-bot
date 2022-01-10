This is a Python program to run the Trefalt network simulation game (https://doi.org/10.1177%2F1052562914521197).

Setup:

1. Clone this repo
2. Set up a developer account in Discord and create a Bot following the instructions at https://discordpy.readthedocs.io/en/latest/discord.html
3. Copy your bot's token and put it in a file called config.py that looks like this:
```
netgamekey = 'YOURTOKENHERE'
```
4. Give the bot the View Channels, Send Messages, Attach Files, Read Message History, and Mention Everyone permissions under bot permissions (instructions at https://discordpy.readthedocs.io/en/latest/discord.html)
5. Install the required packages
```
pip3 install python-igraph pycairo discord.py
```
6. Set up roles on Discord. The bot expects that the user running the game has the "Teachers" role.
7. Set up a "category" for your class. (I think it will probably work without a category, but I haven't tested it). 
8. Run the bot
```
python3 ./networkgamebot.py
```
9. In a text channel in the category, type
```
$network game
```

If everything is set up correctly, then it should start the game, and the NetworkGameBot will send messages to everyone explaining how to play. Note that you will need at least 7 people online in the category before the game will work.

Teachers will get the "observer" role, where they can see the full network graph and who has what. Get an updated version of the network graphs by running:
```
$status
```

I usually run `$status` many, many times during the game and then use those visualizations to show the students how information moved through the network.
