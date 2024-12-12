import requests
import toml
import json
import time
import urllib3
from datetime import datetime, timezone
from geopy.distance import geodesic
from geopy.point import Point

config = toml.load('routing.toml')

class Routing:
  def __init__(self, trip, boatData):
    self.trip = trip
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
    # Update the checkpoint list by removing the first ones as the become closer than 4000nm
    nextPoint = []
    while self.trip:
      nextPoint = self.trip[list(self.trip.keys())[0]]
      # Remove checkpoint when they are closer than 4000nm
      if geodesic([lat, lng], [nextPoint[0], nextPoint[1]]).nautical < 4000:
        nextPoint = self.trip.pop(list(self.trip.keys())[0])
      else:
        break
    # Case when the finish line is closer than 4000nm
    if not self.trip:
      self.trip['0'] = nextPoint
    return nextPoint


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
    paceNotes = sorted(
      [{
        'date': item['dateHeure'], 
        'heading': item['cap'],
        'speed': (item['vitesse'] / 1.852 if item['vitesse'] is not None else None),
        'sail': item['typeVoile'],
        'energy': item['energie']
      } for item in lds],
      key=lambda x: x['date'],
    )
    return paceNotes


def log(level, message):
  timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d-%Hh%Mm%SsZ")
  print(f"{timestamp} [{level}] {message}")


if __name__ == '__main__':
  trip = {"4": [-53, -170], "5": [-53, -120], "6": [-57, -80], "7": [-53, -56.5], "8": [-31, -40], "9": [-4, -31], "10": [20, -30], "11": [43, -25], "12": [46.49166, -1.79083]}
  boatData = {"speed": 1, "heading": 1, "sail": 1, "energy": 100, "authToken": "", "userId": "", "ts": int(time.time()), "lat": -50, "lng": 50}
  routing = Routing(trip, boatData)
  with open('temp.json', 'w') as file:
    json.dump(routing.getPaceNotes(), file)
