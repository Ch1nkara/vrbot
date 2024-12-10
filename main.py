import time
import json
import sys
from random import randint
from datetime import datetime, timezone
from dateutil import parser

import virtual_regatta as vr
import routing

# In virtual regatta, the weather is updated 4 times a day, at 00Z, 06Z...
GRIB_UPDATES = [0, 6, 12, 18]  # 00:00Z, 06:00Z, 12:00Z, 18:00Z


def followPaceNotes():
  with open('pace_notes.json', 'r') as file:
    paceNotes = json.load(file)
  # The instruction as stored in reverse, last one being the one to apply the soonest
  parsed_time = parser.isoparse(paceNotes[-1]['dateHeure'])
  now = datetime.now(timezone.utc)
  # Do nothing until the next action is in the past
  if parsed_time > now:
    return
  with open('pace_notes.json', 'w') as file:
    json.dump(paceNotes[:-1], file)
  try:
    vr.doPacePlan(paceNotes[-1])
    vr.log('INFO', f"Executed pacePlan: {paceNotes[-1]['dateHeure']}")
  except Exception as e:
    vr.log('ERR', f"Error executing pacePlan {paceNotes[-1]}: {e}")


def updatePaceNotes():
  with open('update_notes.json', 'r') as file:
    updateNotes = json.load(file)
  if not updateNotes:
    return
  parsed_time = parser.isoparse(updateNotes[list(updateNotes.keys())[0]])
  now = datetime.now(timezone.utc)
  # Do nothing until the next action is in the past
  if parsed_time > now:
    return
  updateNotes.pop(list(updateNotes.keys())[0])
  with open('update_notes.json', 'w') as file:
    json.dump(updateNotes, file)
  try:
    vr.getPosition()
    routing.buildPaceNotes()
    vr.log('INFO', 'Updated Pace Notes')
  except Exception as e:
    vr.log('ERR', f"Error updating Pace Notes: {e}")


def schedulePaceNotesUpdate():
  today = datetime.now(timezone.utc).date()
  updateNotes = {}
  for i, hour in enumerate(GRIB_UPDATES, start=1):
    timestamp = datetime(
      today.year, today.month, today.day, 
      hour, randint(1,59), randint(1,59)).strftime('%Y-%m-%dT%H:%M:%SZ')
    updateNotes[str(i)] = timestamp
  with open("update_notes.json", 'w') as file:
    json.dump(updateNotes, file)
  vr.log('INFO', f"Scheduled paceNoteUpdate:{updateNotes}")


def raceActions():
  now = datetime.now(timezone.utc)
  if now.hour == 0 and now.minute == 0:
    schedulePaceNotesUpdate()
  # Update Pace notes if needed
  updatePaceNotes()
  # Apply the pace note
  followPaceNotes()

if __name__ == '__main__':
  if 'standalone' in sys.argv:
    schedulePaceNotesUpdate()
    while True:
      raceActions()
      time.sleep(59)
  else:
    raceActions()

