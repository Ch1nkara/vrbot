import requests
import toml
import json
import time
import urllib3
from datetime import datetime, timezone
from geopy.distance import geodesic
from geopy.point import Point
from virtual_regatta import getPosition, log

config = toml.load('routing.toml')


def buildPaceNotes():
  (ts, lat, lng) = getPosition() # Get last postition from vr track
  (lat, lng) = updatePosition(ts, lat, lng) # Estimate the current position based on speed/heading
  #log('DEBUG', f"buildPaceNotes updated position: {lat}, {lng}")
  (nextLat, nextLng) = getDestination(lat, lng)
  #log('DEBUG', f"buildPaceNotes destination: {nextLat}, {nextLng}")
  paceNotes = getRouting(lat, lng, nextLat, nextLng)
  #paceNotes = getRouting(-22.625555, -30.1625, 46.49166, -1.79083)
  with open('pace_notes.json', 'w') as file:
    json.dump(paceNotes, file)


def updatePosition(ts, lat, lng):
  now = int(time.time())
  if now - ts > 7200: # last track position older than 2h
    log('WARN', ''.join([
      'Last postion too old to compute current one: ',
      datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M'),
    ]))
  log('INFO', ''.join([
    'Last position was from ',
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
  newTripData = {}
  foundNext = False
  # Update the checkpoint list by removing the first ones as the become closer than 4000nm
  for checkpoint in tripData:
    if foundNext:
      newTripData[checkpoint] = tripData[checkpoint]
      continue
    if geodesic([lat, lng], [tripData[checkpoint][0], tripData[checkpoint][1]]).nautical < 4000:
      continue
    else:
      newTripData[checkpoint] = tripData[checkpoint]
      foundNext = True
  # Case when the finish line is closer than 4000nm
  if len(newTripData) == 0:
    newTripData = {max(tripData.keys()): tripData[max(tripData.keys())]}
  with open('trip.json', 'w') as file:
    json.dump(newTripData, file)
  return next(iter(newTripData.items()))[1]


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


if __name__ == '__main__':
  getRouting(-22.625555, -30.1625, 46.49166, -1.79083)
