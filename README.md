# vrbot
Virtual Regatta Bot for fun.

 - The bot gets a routing plan (called pace notes) from vrzen.org. These notes are based on its current situation and provide instructions (head 106 at this time, change sail at that time etc.)
 - The bot follows these pace notes
 - 4 times a day, after every weather update, the bot creates a new route plan based on its latest information and discard the previous one
 - If the bot is closer than 2500nm from a waypoint, it's going to aim for the next one

Can be run as an AWS Lambda, stays in the free tiers with the following monthly consumption:
 - ~1000 Lambda execution ("Always Free" limit is 1 million)
 - ~3Mo SimpleDB usage ("Always Free" limit is 1 Go)

## Prerequistes
 - Have a Virtual Regatta account for the bot, participating in a race
 - Get the bot code `git clone https://github.com/Ch1nkara/vrbot.git`
 - Rename vrboat.toml_example as vrboat.toml and edit the parameters near the comment blocks:
    - Fill with the credentials of a virtual regatta account so the bot can use it
    - From a browser connected to the game, inspect the page to get the race number and the leg number
    - From a browser connected to the game, inspect the page to get the browser id used during requests
 - Rename routing.toml_example as routing.toml and edit the parameters near comment blocks:
    - From a browser connected to https://routage.vrzen.org/, inspect the page to get the userID and the race name
    - Set the option available to the bot (sails, foils...)
    - Set the trip waypoints (around 1500nm between each) the bot will use for its routing
 - In main.py, edit init() with recent boat data (position, speed, sail, destination...)

## Installation Option 1: As an amazon AWS Lambda
 - bundle the python dependencies
```
cd vrbot
mkdir python
pip install -r requirements.txt --target python/
zip -r dependencies.zip python/
```
 - From AWS Lambda, create a python lambda, python version 3.12
 - Add the dependencies.zip as a custom layer
 - Upload all the .py and .toml files to the lambda
 - Set the lambda_function.py to :
```
import json
import boto3
import main 

def lambda_handler(event, context):
    localMode = False
    #main.init(localMode)
    #main.peek('boat', localMode)
    #main.peek('paceNote0', localMode)
    main.main(localMode)
    return {
        'statusCode': 200,
        'body': json.dumps({
            'message': 'lambda exited successfully',
        })
    }
```
 - From AWS EventBridge, trigger the lambda every 5 minutes
 - Manually trigger the lambda with `main.init(False)` uncommented to initialize the database with recent boad and routing data
 - use `main.peek('boat', False)` to check the database content
 - Leave only `main.main(False)` uncommented for the scheduled trigger
 - Logs can be seen in CloudWatch with the filter `%\[*\]%` to remove noise

## Installation Option 2: Locally, in standalone mode
 - Use python 3.12 and install the dependencies in a virtual environment
```
cd vrbot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
 - Initialyse the local database (stored in storage.json) with the recent boat data
```
python main.py init
```
 - Check that the boat data is correctly initialized
```
python main.py peek boat
python main.py peek paceNote0
# or check the file storage.json
```
 - Start the bot
```
python main.py 
# or, to disown the process and be able to close the terminal
nohup python main.py &
```
