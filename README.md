# vrbot
virtual regatta bot for fun

## Installation
 - Install the dependencies in a virtual environnment
```
git clone https://github.com/Ch1nkara/vrbot.git
cd vrbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
 - Tune the configuration file virtual_regatta.toml to match your account/race
 ```
 cp virtual_regatta.toml_example virtual_regatta.toml
 # Then adapt informations
 ```
 - Tune the configuration file routing.toml to match your routing preferences (sails, userID)
 ```
 cp routing.toml_example routing.toml
 # Then adapt informations
 ```
 - In virtual regatta, start a race and feed the intitial conditions in boat.json
 - Set waypoints that the bot should navigate towards via trip.json 
 - Give the boat the control of the race: `python3 main.py`

## Bot behavior
 - The bot get a routing plan (called pace notes) from vrzen.org. These notes are based on its current situation and provide instruction (head 106 at this time, change sail at that time etc)
 - The bot follow these pace notes
 - 4 times a day, at a random time shortly after every weather update, the bot create a new route plan base on its latest information and discard the previous one
 - If the bot is closer than 4000nm from a waypoint, its going to aim for the next one