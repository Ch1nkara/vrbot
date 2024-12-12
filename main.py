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
    now = dt.datetime.now(dt.timezone.utc)
    # Iterate over paceNotes in order
    for note in sorted(paceNotes.keys(), key=lambda k: int(k.replace("paceNote", ""))):
      noteDate = dt.datetime.strptime(paceNotes[note]['date'], "%Y-%m-%dT%H:%M:%S.%fZ")
      noteDate = noteDate.replace(tzinfo=dt.timezone.utc)
      # Look for the next note to apply: it's date is less than 5 minutes ago
      if noteDate < now - dt.timedelta(minutes=5):
        #vrboat.log('DEBUG', f"note {note} too old: {paceNotes[note]['date']}")
        continue
      # Check if it's time to apply it: it's date is in the past
      if noteDate <= now:
        #vrboat.log('DEBUG', f"note {note} must be applied: {paceNotes[note]['date']}")
        try:
          self.vrboat.doPacePlan(paceNotes[note])
          self.sdb.setObj('boat', self.vrboat.boatData)
          vrboat.log('INFO', f"Executed pacePlan: {paceNotes[note]['date']}")
        except Exception as e:
          vrboat.log('ERR', f"Error executing pacePlan {paceNotes[note]}: {e}")
      else:
        #vrboat.log('DEBUG', f"note {note} still in the futur: {paceNotes[note]['date']}")
        pass
      break


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
    rtng = routing.Routing(self.sdb.getObj('destination'), self.vrboat.boatData)
    self.sdb.setPaceNotes(rtng.getPaceNotes())
    self.sdb.setObj('destination', rtng.destination)
    self.sdb.setObj('boat', self.vrboat.boatData)
    vrboat.log('INFO', f"Updated Pace Notes")


def init(localMode):
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

  storage.flushAndInit('vrbot', boatData, destination, localMode)
  sdb = storage.SimpleDBWrapper('vrbot', localMode)
  boat = vrboat.VrBoat(sdb.getObj('boat'))
  skipper = Skipper(boat, sdb)
  skipper.updateActions()
  vrboat.log('INFO', 'Database: initialized')
  sys.exit(0)


def peek(objName, localMode):
  sdb = storage.SimpleDBWrapper('vrbot', localMode)
  vrboat.log('INFO', f"{objName}: {sdb.getObj(objName)}")
  sys.exit(0)


def main(localMode):
  sdb = storage.SimpleDBWrapper('vrbot', localMode)
  if localMode:
    while True:
      boat = vrboat.VrBoat(sdb.getObj('boat'))
      skipper = Skipper(boat, sdb)
      skipper.updatePaceNotes()
      skipper.followPaceNotes()
      #sleep around 5 min between race actions
      time.sleep(293)
  else:
    boat = vrboat.VrBoat(sdb.getObj('boat'))
    skipper = Skipper(boat, sdb)
    skipper.updatePaceNotes()
    skipper.followPaceNotes()
 

if __name__ == '__main__':
  localMode = True
  if 'init' in sys.argv:
    init(localMode)
  if 'peek' in sys.argv:
    peek(sys.argv[sys.argv.index('peek') + 1], localMode)
  main(localMode)
