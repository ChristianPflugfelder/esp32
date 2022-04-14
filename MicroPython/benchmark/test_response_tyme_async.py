import asyncio
import time
import csv
import aiohttp
import sys
import yaml
import random

# Tests how long the response time is for simultaneously started requests

#--------------------------------------------------
# Settings
#--------------------------------------------------

URL = "http://192.168.2.114/p"
NR_SESSIONS = 10
DELAY_BETWEEN_SESSIONS = 0    #[s]
DELAY_BETWEEN_REQUESTS = 1500 #[s]
WRITE_TO_CSV = True

DELAY_ON_SERVER = 500        #[ms]
RANDOMNESS = 0.1
MEMORY_USAGE_ON_SERVER = 500

if len(sys.argv) == 2:
  NR_SESSIONS = int(sys.argv[1])

#--------------------------------------------------
# CSV
#--------------------------------------------------

csv_file_name = "./results/response_time/" + time.strftime("%Y_%m_%d_%H_%M", time.gmtime()) + f"_connection{NR_SESSIONS}_delay_{DELAY_ON_SERVER}_memoryusage_{MEMORY_USAGE_ON_SERVER}" + ".csv"

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

    try:
      async with aiohttp.ClientSession() as session:
          print(f"Send request {session_nr}")

          while True:
              start_time = time.time()

              delay = random.randint(int(DELAY_ON_SERVER * (1 - RANDOMNESS)), int(DELAY_ON_SERVER * (1 + RANDOMNESS)))
              headers = {'Delay': str(delay), 'MomoryUsage': str(MEMORY_USAGE_ON_SERVER)}
              async with session.get(URL, headers = headers) as resp:
                  text = await resp.text()
                  ram_usage = await pars_result(text)
                  elapsed_time = round(time.time() - start_time, 10) * 1000 - delay

                  print(f"    Session {session_nr} {elapsed_time:8.0f}")
                  await append_response_time(session_nr, "{:8.0f}".format(elapsed_time), ram_usage)

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
  
    await append_response_time("Connenctions", "Responsetime [ms]", "Heap Usage [byte]")

    for i in range(1, NR_SESSIONS + 1):
        #print(f"Start {i}/{NR_SESSIONS}")
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
