import requests
import time
import toml
import base64
import json
from datetime import datetime, timezone

config = toml.load('virtual_regatta.toml')


def setSail(sailId):
  logIn()
  sendEvent(
    [{"value": sailId,"type":"sail"}], 
    'Game_AddBoatAction'
  )


def setBearing(bearing):
  logIn()
  sendEvent(
    [{'value': bearing, 'autoTwa': False, 'type':'heading'}], 
    'Game_AddBoatAction'
  )


def setWaypoints(latLngArray):
  logIn()
  values = []
  for i, latLng in enumerate(latLngArray, start=1):
    values.append({'lat': latLng[0], 'lon': latLng[1], 'idx': i})
  sendEvent(
    [{'values': values, 'nextWpIdx': len(latLngArray) + 1, 'type': 'wp'}],
    'Game_AddBoatAction'
  )


def doPacePlan(pacePlan):
  with open('boat.json', 'r') as file:
    boatData = json.load(file)
  # Change boat course if the one in the pace plan is different from the current one
  if boatData['heading'] != pacePlan['cap']:
    setBearing(pacePlan['cap'])
    log('INFO', ''.join([
      'Changed heading from ', str(boatData['heading']), ' to ', str(pacePlan['cap'])]))
  boatData['heading'] = pacePlan['cap']
  # Change the boat sail if the one in the pace plan is different from the current one
  if boatData['sail'] != pacePlan['typeVoile']:
    setSail(int(pacePlan['typeVoile']))
    log('INFO', ''.join([
      'Changed sail from ', config['sails'][str(boatData['sail'])],
      ' to ', config['sails'][str(pacePlan['typeVoile'])]
    ]))
    boatData['sail'] = pacePlan['typeVoile']
  # Assume the pace plan is correct about current speed and energy
  boatData['speed'] = pacePlan['vitesse']
  boatData['energy'] = pacePlan['energie']
  with open('boat.json', 'w') as file:
    json.dump(boatData, file)


def getPosition():
  logIn()
  track_list = sendEvent([], 'Game_GetBoatTrack')['scriptData']['track']
  # Return the last position present in the track
  timestamp = track_list[len(track_list) - 1]['ts'] // 1000
  lat = track_list[len(track_list) - 1]['lat']
  lng = track_list[len(track_list) - 1]['lon']
  with open('boat.json', 'r') as file:
    boatData = json.load(file)
  boatData['ts'] = timestamp
  boatData['lat'] = lat
  boatData['lng'] = lng
  with open('boat.json', 'w') as file:
    json.dump(boatData, file)
  return timestamp, lat, lng


def isValid(token):
  if token == '':
    return False
  token_json = base64.b64decode(token.split('.')[1]).decode('utf-8')
  expirationDate = int(json.loads(token_json).get('exp'))
  # If token expiration is in less than an hour
  if expirationDate <= int(time.time()) + 3600:
    return False
  return True


def logIn():
  with open('boat.json', 'r') as file:
    boatData = json.load(file)
  # Login only if the jwt is expired
  if isValid(boatData['authToken']):
    #log('DEBUG', 'token still valid')
    return
  loginPayload = {
    '@class': 'AuthenticationRequest',
    'userName': config['user']['username'],
    'password': config['user']['password']
  }
  # Exchange the credentials for a jwt token valid 12 hours
  response = requests.post(
    config['api']['prod_url'] + '/AuthenticationRequest', 
    headers=config['headers'], 
    json=loginPayload
  )
  response.raise_for_status()
  response_data = response.json()
  if 'authToken' not in response_data:
    raise ValueError('error during login: ' + response.text)
  log('INFO', 'Renewed token')
  with open('boat.json', 'r') as file:
    boatData = json.load(file)
  boatData['authToken'] = response_data['authToken']
  boatData['userId'] = response_data['userId']
  with open('boat.json', 'w') as file:
    json.dump(boatData, file)


def sendEvent(actions, eventKey):
  with open('boat.json', 'r') as file:
    boatData = json.load(file)
  eventPayload = {
    '@class': 'LogEventRequest',
    'eventKey': eventKey,
    'race_id': config['race']['race_id'],
    'leg_num': config['race']['leg_num'],
    'actions': actions,
    'ts': int(time.time() * 1000),
    'authToken': boatData['authToken'],
    'playerId': boatData['userId']
  }
  response = requests.post(
    config['api']['prod_url'] + '/LogEventRequest', 
    headers=config['headers'], 
    json=eventPayload
  )
  response.raise_for_status()
  response_data = response.json()
  if response_data['scriptData']['rc'] == 'ERROR':
    raise ValueError('error during event:' + response.json())
  return response_data


def log(level, message):
  timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d-%Hh%Mm%SsZ")
  print(f"{timestamp} [{level}] {message}")


if __name__ == '__main__':
  test='a'
  with open('boat.json', 'r') as file:
    boatData = json.load(file)
    print("config sail 1:",config['sails']['1'])
    print("sail data boat:", boatData['sail'])
    print(f"from {config['sails'][str(boatData['sail'])]}")

