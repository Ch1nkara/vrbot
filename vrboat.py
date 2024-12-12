import requests
import time
import toml
import base64
import json
from datetime import datetime, timezone

config = toml.load('vrboat.toml')

class VrBoat:
  def __init__(self, boatData):
    self.boatData = boatData


  def setSail(self, sailId):
    self.logIn()
    self.sendEvent(
      [{"value": sailId,"type":"sail"}], 
      'Game_AddBoatAction',
    )
    self.boatData['sail'] = sailId


  def setBearing(self, bearing):
    self.logIn()
    self.sendEvent(
      [{'value': bearing, 'autoTwa': False, 'type':'heading'}], 
      'Game_AddBoatAction'
    )
    self.boatData['heading'] = bearing


  def setWaypoints(self, latLngArray):
    self.logIn()
    values = []
    for i, latLng in enumerate(latLngArray, start=1):
      values.append({'lat': latLng[0], 'lon': latLng[1], 'idx': i})
    self.sendEvent(
      [{'values': values, 'nextWpIdx': len(latLngArray) + 1, 'type': 'wp'}],
      'Game_AddBoatAction'
    )


  def doPacePlan(self, pacePlan):
    # Change boat course if the one in the pace plan is different from the current one
    currentHeading = self.boatData['heading']
    if currentHeading != pacePlan['heading']:
      self.setBearing(pacePlan['heading'])
      log('INFO', ''.join([
        'Changed heading from ', str(currentHeading), 
        ' to ', str(pacePlan['heading'])]))
    # Change the boat sail if the one in the pace plan is different from the current one
    currentSail = self.boatData['sail']
    if currentSail != pacePlan['sail']:
      self.setSail(int(pacePlan['sail']))
      log('INFO', ''.join([
        'Changed sail from ', config['sails'][str(currentSail)],
        ' to ', config['sails'][str(pacePlan['sail'])]
      ]))
    # Assume the pace plan is correct about current speed and energy
    self.boatData['speed'] = pacePlan['speed']
    self.boatData['energy'] = pacePlan['energy']


  def updatePosition(self):
    self.logIn()
    trackList = self.sendEvent([], 'Game_GetBoatTrack')['scriptData']['track']
    # Return the last position present in the track
    timestamp = trackList[len(trackList) - 1]['ts'] // 1000
    lat = trackList[len(trackList) - 1]['lat']
    lng = trackList[len(trackList) - 1]['lon']
    self.boatData['ts'] = timestamp
    self.boatData['lat'] = lat
    self.boatData['lng'] = lng


  def isValid(self, token):
    if token == '':
      return False
    tokenJson = base64.b64decode(token.split('.')[1]).decode('utf-8')
    expirationDate = int(json.loads(tokenJson).get('exp'))
    # If token expiration is in less than an hour
    if expirationDate <= int(time.time()) + 3600:
      return False
    return True


  def logIn(self):
    # Login only if the jwt is expired
    if self.isValid(self.boatData['authToken']):
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
    responseData = response.json()
    if 'authToken' not in responseData:
      raise ValueError('error during login: ' + response.text)
    log('INFO', 'Renewed token')
    self.boatData['authToken'] = responseData['authToken']
    self.boatData['userId'] = responseData['userId']


  def sendEvent(self, actions, eventKey):
    eventPayload = {
      '@class': 'LogEventRequest',
      'eventKey': eventKey,
      'race_id': config['race']['race_id'],
      'leg_num': config['race']['leg_num'],
      'actions': actions,
      'ts': int(time.time() * 1000),
      'authToken': self.boatData['authToken'],
      'playerId': self.boatData['userId']
    }
    response = requests.post(
      config['api']['prod_url'] + '/LogEventRequest', 
      headers=config['headers'], 
      json=eventPayload
    )
    response.raise_for_status()
    responseData = response.json()
    if responseData['scriptData']['rc'] == 'ERROR':
      raise ValueError('error during event:' + response.json())
    return responseData


def log(level, message):
  timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d-%Hh%Mm%SsZ")
  print(f"{timestamp} [{level}] {message}")


if __name__ == '__main__':
  vrBoat = VrBoat({"speed": 1, "heading": 1, "sail": 1, "energy": 100, "authToken": "", "userId": "", "ts": int(time.time()), "lat": -50, "lng": 50})
  vrBoat.setBearing(125)
  log('DEBUG', vrBoat.boatData)

