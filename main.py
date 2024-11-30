import time
import random
import schedule
import json
from datetime import datetime, timedelta, timezone
from dateutil import parser
from routing import buildPaceNotes
from virtual_regatta import log, doPacePlan

# In virtual regatta, the weather is updated 4 times a day, at 00Z, 06Z...
GRIB_UPDATES = ["01:00", "07:00", "13:00", "19:00"] # local time


def followPaceNotes():
  with open('pace_notes.json', 'r') as file:
    paceNotes = json.load(file)
  # The instruction as stored in reverse, last one being the one to apply the soonest
  parsed_time = parser.isoparse(paceNotes[-1]['dateHeure'])
  now = datetime.now(timezone.utc)
  # Follow the first instruction if its planned time is in the past
  if parsed_time <= now:
    with open('pace_notes.json', 'w') as file:
      json.dump(paceNotes[:-1], file)
    doPacePlan(paceNotes[-1])
    #log('DEBUG', f"Executed pacePlan: {paceNotes[-1]}")
    log('INFO', f"Executed pacePlan: {paceNotes[-1]['dateHeure']}")


def updatePaceNotes():
  tryCount = 0
  for i in range(5):
    try:
      buildPaceNotes()
      log('INFO', 'Updated Pace Notes')
      return
    except Exception as e:
      tryCount += 1
      log('ERR', f"Error updating route {tryCount}: {e}")
      time.sleep(59)


def schedulePaceNotesUpdates():
  schedule.clear()
  schedule.every().day.at("01:00").do(schedulePaceNotesUpdates)
  # Schedule a updatePaceNotes() at a random time shortly after a weather update
  for gribTime in GRIB_UPDATES:
    gribTime = datetime.strptime(gribTime, "%H:%M").replace(
      year=datetime.now(timezone.utc).year,
      month=datetime.now(timezone.utc).month,
      day=datetime.now(timezone.utc).day
    )
    # Between 5 minutes and 110 minutes after the weather update
    paceNoteUpdateTime = gribTime + timedelta(minutes=random.randint(5, 110))
    paceNoteUpdate = paceNoteUpdateTime.strftime("%H:%M")
    log('INFO', f"Scheduled paceNoteUpdate at:{paceNoteUpdate}")
    schedule.every().day.at(paceNoteUpdate).do(updatePaceNotes)  


if __name__ == '__main__':
  # Schedule the 4 pace notes update of the day
  schedulePaceNotesUpdates()
  # Update the pace notes
  updatePaceNotes()
  time.sleep(30)
  while True:
    # Apply the pace note
    followPaceNotes()
    # Execute schedule job if any are pending
    schedule.run_pending()
    time.sleep(59)





  



