import time
import json
import sys
import datetime as dt
from random import randint
from dateutil import parser

import vrboat
import routing
import storage

# In virtual regatta, the weather is updated 4 times a day, at 00Z, 06Z...
GRIB_UPDATES = [0, 6, 12, 18]  # 00:00Z, 06:00Z, 12:00Z, 18:00Z
TIMERANGES = []
for hour in GRIB_UPDATES:
  TIMERANGES.append((dt.time(hour + 1, 15), dt.time(hour + 1, 20)))

class Skipper:
  def __init__(self, vrboat, simpledb):
    self.vrboat = vrboat
    self.sdb = simpledb


  def followPaceNotes(self):
    paceNotes = self.sdb.getPaceNotes()
    # If paceNotes is empty, do nothing
    if not paceNotes:
      return
    nextActionTime = parser.isoparse(paceNotes[0]['date'])
    now = dt.datetime.now(dt.timezone.utc)
    # Do nothing until the next action is in the past
    if nextActionTime > now:
      return
    pacePlan = paceNotes.pop(0)
    try:
      self.vrboat.doPacePlan(pacePlan)
      self.sdb.setObj('boat', self.vrboat.boatData)
      vrboat.log('INFO', f"Executed pacePlan: {pacePlan['date']}")
    except Exception as e:
      vrboat.log('ERR', f"Error executin pacePlan {pacePlan}: {e}")
    self.sdb.setPaceNotes(paceNotes)


  def updatePaceNotes(self):
    now = dt.datetime.now(dt.timezone.utc)
    for start, end in TIMERANGES:
      if start <= now.time() <= end:
        vrboat.log('INFO', f"Starting Pace Notes update")
        try:
          self.updateActions()
        except Exception as e:
          vrboat.log('ERR', f"Error updating Pace Notes: {e}")
        return


  def updateActions(self):
    self.vrboat.updatePosition()
    rtng = routing.Routing(self.sdb.getObj('trip'), self.vrboat.boatData)
    self.sdb.setPaceNotes(rtng.getPaceNotes())
    self.sdb.setObj('trip', rtng.trip)
    self.sdb.setObj('boat', self.vrboat.boatData)
    vrboat.log('INFO', f"Updated Pace Notes")


def maintenance(localMode):
  boatData = {"speed": 1, "heading": 1, "sail": 1, "energy": 100, "authToken": "", "userId": "", "ts": int(time.time()), "lat": -50, "lng": 50}

  trip = {"0":[-40, 25], "1":[-45, 60], "2":[-43, 100], "3":[-47, 140], "4":[-53, -170], "5":[-53, -120], "6":[-57, -80], "7":[-53, -56.5], "8":[-31, -40], "9":[-4, -31], "10":[20, -30], "11":[43, -25], "12":[46.49166, -1.79083]}

  storage.flushAndInit('vrbot', boatData, trip, localMode)
  sdb = storage.SimpleDBWrapper('vrbot', localMode)
  boat = vrboat.VrBoat(sdb.getObj('boat'))
  skipper = Skipper(boat, sdb)
  skipper.updateActions()
  storage.printDb(sdb)
  sys.exit(0)


def main(localMode):
  sdb = storage.SimpleDBWrapper('vrbot', localMode)
  #maintenance(localMode)
  boat = vrboat.VrBoat(sdb.getObj('boat'))
  skipper = Skipper(boat, sdb)
  skipper.updateActions()
  if localMode:
    while True:
      boat = vrboat.VrBoat(sdb.getObj('boat'))
      skipper = Skipper(boat, sdb)
      skipper.updatePaceNotes()
      skipper.followPaceNotes()
      sdb.setObj('boat', skipper.vrboat.boatData)
      #sleep around 5 min between race actions
      time.sleep(293)
  else:
    boat = vrboat.VrBoat(sdb.getObj('boat'))
    skipper = Skipper(boat, sdb)
    skipper.updatePaceNotes()
    skipper.followPaceNotes()
    sdb.setObj('boat', skipper.vrboat.boatData)


if __name__ == '__main__':
  localMode = False
  if 'standalone' in sys.argv:
    localMode = True
  main(localMode)


