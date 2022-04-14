import requests
import asyncio
import time
import csv
import yaml

# Tests how many connections a server can keep open at the same time

#--------------------------------------------------
# Settings
#--------------------------------------------------

URL = "http://192.168.2.114/p"
NR_SESSIONS = 200
DELAY_BETWEEN_SESSIONS = 3    #[s]
DELAY_BETWEEN_REQUESTS = 1500 #[s]
WRITE_TO_CSV = True

#--------------------------------------------------
# CSV
#--------------------------------------------------

csv_file_name = "./results/nr_connections/" + time.strftime("%Y_%m_%d_%H_%M_%S", time.gmtime()) + ".csv"

async def append_response_time(session_nr, response_time, ram_usage):
  if not WRITE_TO_CSV:
      return

  with open(csv_file_name, 'a', encoding='UTF8', newline='') as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow([session_nr, response_time, "", session_nr, ram_usage])

#--------------------------------------------------
# Connections
#--------------------------------------------------

async def start_session(session_nr):
    session = requests.Session()

    try:
      while True:
          response = session.get(URL, timeout=10)
          print(f"    Session {session_nr} {response.elapsed.total_seconds()}")
          #ram_usage = await pars_result(response.text)
          #await append_response_time(session_nr, response.elapsed.total_seconds(), ram_usage)
          await append_response_time(session_nr, response.elapsed.total_seconds(), "")
          await asyncio.sleep(DELAY_BETWEEN_REQUESTS)
    except Exception:
      print(f"Session {session_nr} could not be started")
      loop.stop()


async def pars_result(text):
  if text.isdigit():
    return text

  response_text = yaml.safe_load(text)
  for time in response_text['functionExecutionTimes']:
    print(f"{time['func']} took {time['time']} ms")
  print('\n')
  return response_text['allocMem']


async def main():
  
    await append_response_time("Connenctions", "Responsetime [s]", "Heap Usage [byte]")

    for i in range(1, NR_SESSIONS + 1):
        print(f"Start {i}/{NR_SESSIONS}")
        loop.create_task(start_session(i))
        await asyncio.sleep(DELAY_BETWEEN_SESSIONS)

#--------------------------------------------------
# Main
#--------------------------------------------------

loop = asyncio.get_event_loop()
loop.create_task(main())

try:
 loop.run_forever()
except KeyboardInterrupt:
  pass
