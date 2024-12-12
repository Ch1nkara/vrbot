import requests
import toml
import json
import time
import urllib3
import ast
from datetime import datetime, timezone
from geopy.distance import geodesic
from geopy.point import Point

config = toml.load('routing.toml')

class Routing:
  def __init__(self, destination, boatData):
    self.destination = destination
    self.boatData = boatData


  def getPaceNotes(self):
    # Estimate the current position based on speed/heading
    (lat, lng) = self.getPosition() 
    #log('DEBUG', f"buildPaceNotes updated position: {lat}, {lng}")
    (nextLat, nextLng) = self.getDestination(lat, lng)
    #log('DEBUG', f"buildPaceNotes destination: {nextLat}, {nextLng}")
    vrZenNotes = self.getRouting(lat, lng, nextLat, nextLng)
    return self.parseVRZen(vrZenNotes)


  def getPosition(self):
    (ts, lat, lng) = (self.boatData['ts'], self.boatData['lat'], self.boatData['lng'])
    now = int(time.time())
    if now - ts > 7200: # last track position older than 2h
      log('WARN', ''.join([
        'Last postion too old to compute current one: ',
        datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M'),
        ' which was ',
        str(datetime.now(timezone.utc) - datetime.fromtimestamp(ts, timezone.utc)),
        ' ago'
      ]))
    distance = self.boatData['speed'] * (now - ts) / 3600
    nowPoint = geodesic(nautical=distance).destination(Point(lat, lng), self.boatData['heading'])
    return nowPoint.latitude, nowPoint.longitude


  def getDestination(self, lat, lng):
    wpt = self.destination['waypoint']
    wpt_lat = ast.literal_eval(config['trip'][str(wpt)])[0]
    wpt_lng = ast.literal_eval(config['trip'][str(wpt)])[1]
    # Until the last waypoint, go to next if this one is closer than 2500nm
    while str(wpt + 1) in config['trip']:
      if geodesic([lat, lng], [wpt_lat, wpt_lng]).nautical > 2500:
        break
      else:
        wpt += 1
        wpt_lat = ast.literal_eval(config['trip'][str(wpt)])[0]
        wpt_lng = ast.literal_eval(config['trip'][str(wpt)])[1]
        self.destination = {'waypoint': wpt}    
    #log('DEBUG', f"Destination chosen: {wpt}: {wpt_lat}, {wpt_lng}")
    return (wpt_lat, wpt_lng)


  def getRouting(self, fromLat, fromLng, destLat, destLng):
    routingPayload = {
      "latitude_origine": fromLat,
      "longitude_origine": fromLng,
      "latitude_cible": destLat,
      "longitude_cible": destLng
    }
    routingPayload.update(config['parameters'])    
    parametres = [
      config['parametres']['1'],
      str(self.boatData['sail']), ':',
      str(self.boatData['heading']),
      config['parametres']['2'],
      str(int(self.boatData['energy'])),
      config['parametres']['3']
    ]
    routingPayload['parametres'] = ''.join(parametres)
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    response = requests.get(
      config['api']['url'], 
      headers=config['headers'], 
      params=routingPayload,
      verify=False
    )
    response.raise_for_status()
    responseData = response.json()
    if responseData['statut'] == 'KO':
      itinary = f"from [{fromLat},{fromLng}] to [{destLat},{destLng}]"
      raise ValueError(f"error during routing {itinary}: {response.text}")
    return responseData['listDetailSimulation']


  def parseVRZen(self, lds):
    maxId = max(lds, key=lambda x: x['id'])['id']
    paceNotes = {
      f"paceNote{maxId - item['id']}": {
        'date': item['dateHeure'][:-4] + item['dateHeure'][-1], 
        'heading': item['cap'],
        'speed': (item['vitesse'] / 1.852 if item['vitesse'] is not None else None),
        'sail': item['typeVoile'],
        'energy': item['energie']
      } 
      for item in lds
      # keep only the first 80 paceNotes
      if maxId - item['id'] <= 80
    }
    return paceNotes


def log(level, message):
  timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d-%Hh%Mm%SsZ")
  print(f"{timestamp} [{level}] {message}")


if __name__ == '__main__':
  boatData = {
    "speed": 1, 
    "heading": 1, 
    "sail": 1, 
    "energy": 100, 
    "authToken": "", 
    "userId": "", 
    "ts": int(time.time()), 
    "lat": -45, 
    "lng": 55
  }
  destination = {"waypoint": 4}

  routing = Routing(destination, boatData)
  with open('temp.json', 'w') as file:
    json.dump(routing.getPaceNotes(), file)
