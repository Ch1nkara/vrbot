import requests
import toml
import json
import time
import urllib3
from datetime import datetime, timezone
from geopy.distance import geodesic
from geopy.point import Point

config = toml.load('routing.toml')


def buildPaceNotes():
  with open('boat.json', 'r') as file:
    boatData = json.load(file)
  (ts, lat, lng) = (boatData['ts'], boatData['lat'], boatData['lng'])
  (lat, lng) = updatePosition(ts, lat, lng) # Estimate the current position based on speed/heading
  #log('DEBUG', f"buildPaceNotes updated position: {lat}, {lng}")
  (nextLat, nextLng) = getDestination(lat, lng)
  #log('DEBUG', f"buildPaceNotes destination: {nextLat}, {nextLng}")
  paceNotes = getRouting(lat, lng, nextLat, nextLng)
  with open('pace_notes.json', 'w') as file:
    json.dump(paceNotes, file)


def updatePosition(ts, lat, lng):
  now = int(time.time())
  if now - ts > 7200: # last track position older than 2h
    log('WARN', ''.join([
      'Last postion too old to compute current one: ',
      datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M'),
      ' which was ',
      str(datetime.now(timezone.utc) - datetime.fromtimestamp(ts, timezone.utc)),
      ' ago'
    ]))
  with open('boat.json', 'r') as file:
    boatData = json.load(file)
  distance = boatData['speed'] * (now - ts) / 3600
  nowPoint = geodesic(nautical=distance).destination(Point(lat, lng), boatData['heading'])
  return nowPoint.latitude, nowPoint.longitude


def getDestination(lat, lng):
  with open('trip.json', 'r') as file:
    tripData = json.load(file)
  # Update the checkpoint list by removing the first ones as the become closer than 4000nm
  nextPoint = []
  while tripData:
    nextPoint = tripData[list(tripData.keys())[0]]
    # Remove checkpoint when they are closer than 4000nm
    if geodesic([lat, lng], [nextPoint[0], nextPoint[1]]).nautical < 4000:
      nextPoint = tripData.pop(list(tripData.keys())[0])
    else:
      break
  # Case when the finish line is closer than 4000nm
  if not tripData:
    tripData['0'] = nextPoint
  with open('trip.json', 'w') as file:
    json.dump(tripData, file)
  return nextPoint


def getRouting(from_lat, from_lng, dest_lat, dest_lng):
  with open('boat.json', 'r') as file:
    boatData = json.load(file)
  routingPayload = {
    "latitude_origine": from_lat,
    "longitude_origine": from_lng,
    "latitude_cible": dest_lat,
    "longitude_cible": dest_lng
  }
  routingPayload.update(config['parameters'])    
  parametres = [
    config['parametres']['1'],
    str(boatData['sail']), ':',
    str(boatData['heading']),
    config['parametres']['2'],
    str(int(boatData['energy'])),
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
  response_data = response.json()
  if response_data['statut'] == 'KO':
    itinary = f"from [{from_lat},{from_lng}] to [{dest_lat},{dest_lng}]"
    raise ValueError(f"error during routing {itinary}: {response.text}")
  return response_data['listDetailSimulation']


def log(level, message):
  timestamp = datetime.now(timezone.utc).strftime("%Y/%m/%d-%Hh%Mm%SsZ")
  print(f"{timestamp} [{level}] {message}")


if __name__ == '__main__':
  getRouting(-22.625555, -30.1625, 46.49166, -1.79083)
