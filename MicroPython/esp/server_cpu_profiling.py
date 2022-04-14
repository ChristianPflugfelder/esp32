import uasyncio as asyncio
import uerrno
import micropython
import utime
 
    
nr_of_connections = 0
buffers = []
execution_time_format = '- func: {}\n  time: {:8.0f}\n'
verbose_profiling = False

class Response:
    connection_nr = None
    function_execution_times = []


    def __init__(self, connection_nr):
        self.connection_nr = connection_nr
        self.function_execution_times = []


    def addFunctionExectuionTime(self, name, start_time):
        delta = utime.ticks_diff(utime.ticks_us(), start_time)
        if verbose_profiling or ('-' not in name):
            self.function_execution_times.append(execution_time_format.format(name, delta/1000))


    async def getText(self):
        gc.collect()

        response = "connectionNr: " + str(self.connection_nr) + "\n"
        response += "freeMem: " + str(gc.mem_free()) + "\n"
        response += "allocMem: " + str(gc.mem_alloc()) + "\n"
        response += "functionExecutionTimes:\n"

        for execution_time in self.function_execution_times:
            response += execution_time
        
        return response


#----------------------------------------------------------------------------------------------------
# Server
#----------------------------------------------------------------------------------------------------

async def run_server():    
    await print_memory_usage()
    return await asyncio.start_server(handle_client_save, '0.0.0.0', 80)


async def handle_client_save(reader, writer):
    try:
        await handle_client(reader, writer)
    except Exception as e:
        if (e.args[0] != uerrno.ECONNRESET      # Connection terminated by the client - both can be ignored
            and e.args[0] != uerrno.ECONNABORTED):
                raise
    finally:
        await remove_connection_from_count()
        await writer.aclose()
        await reader.aclose()


async def handle_client(reader, writer):
    
    connection_nr = await add_connection_to_count()
        
    while True:
        response = Response(connection_nr)

        # waits until a request is received
        start_time = utime.ticks_us()
        await read_request(reader, response) 
        response.addFunctionExectuionTime("read_request", start_time)
        
        # waits until all headers have been received
        start_time = utime.ticks_us()
        delay, memory_usage = await read_headers(reader, response)
        response.addFunctionExectuionTime("read_headers", start_time)

        await do_dummy_operation(delay, memory_usage)
        
        # respond
        start_time = utime.ticks_us()
        await send_response(writer, response) 
        response.addFunctionExectuionTime("send_response", start_time)
        
        await asyncio.sleep_ms(10)

#--------------------------------------------------

async def read_request(reader, response):
    
    start_time = utime.ticks_us()
    items = await reader.readline()
    response.addFunctionExectuionTime("read_request - reader.readline", start_time)

    splitItems = items.decode('ascii').split()
    if len(splitItems) != 3:
        return
    _method, _path, _version = splitItems

    #print("Client:    "+ str(reader.get_extra_info('peername')) + " new request: " + items.decode('ascii')[:-2])


async def read_headers(reader, response) :
    
    delay = 0
    memory_usage = 0
    
    while True:
        start_time = utime.ticks_us()
        items = await reader.readline()
        response.addFunctionExectuionTime("read_headers - reader.readline", start_time)
        
        splitItems = items.decode('ascii').split(":", 1)

        # header
        if len(splitItems) == 2:
            header, value = splitItems
            value = value.strip()
            
            if(header == "Delay"):
                delay = int(value)
            
            if(header == "MomoryUsage"):
                memory_usage = int(value)
                
            
        # CRLF -> finished sending headeres
        elif len(splitItems) == 1:
            return delay, memory_usage


async def send_response(writer, response) :
    
    text = await response.getText()
    
    start_time = utime.ticks_us()
    await writer.awrite("HTTP/1.1 200 OK\r\n")
    await writer.awrite("Content-Length: " + str(len(text) + get_respone_time_lengt()) + "\r\n") # get_respone_time_lengt is the size of the execution-time-info sent after the response text
    header_writing_time = utime.ticks_diff(utime.ticks_us(), start_time)
        
    start_time = utime.ticks_us()
    await writer.awrite("\r\n")
    await writer.awrite(text)   
    text_writing_time = utime.ticks_diff(utime.ticks_us(), start_time)
    
    await awrite_send_response_time(writer, header_writing_time, text_writing_time)
    
#----------------------------------------------------------------------------------------------------
# Server Helper
#----------------------------------------------------------------------------------------------------

def get_respone_time_lengt():
    if verbose_profiling:
        return 110 + 39
    else:
        return 39

async def awrite_send_response_time(writer, header_writing_time, text_writing_time):
    
    if verbose_profiling:
        header_wt_text = execution_time_format.format("send_response - writer.awrite", header_writing_time/1000)
        text_wt_text = execution_time_format.format("send_response - writer.awrite", text_writing_time/1000)
        await writer.awrite(header_wt_text)
        await writer.awrite(text_wt_text)
        print(len(header_wt_text) + len(text_wt_text))
    
    total_wt_text = execution_time_format.format("send_response", (header_writing_time + text_writing_time + 2500)/1000)
    await writer.awrite(total_wt_text) # average total time from other measurements
    
    print(len(total_wt_text))

async def do_dummy_operation(delay, memory_usage):

    if(memory_usage > 0):
        global buffers    
        buffer = bytearray([0] * memory_usage)
        buffers.append(buffer)

    if(delay > 0):
        await asyncio.sleep_ms(delay)

#----------------------------------------------------------------------------------------------------
# Memory & Connection
#----------------------------------------------------------------------------------------------------

async def print_memory_usage():
    gc.collect()
    print('Free: {} allocated: {}'.format(gc.mem_free(), gc.mem_alloc()))
    print('\n')


async def add_connection_to_count():
    global nr_of_connections
    nr_of_connections = nr_of_connections + 1
    print("Active connections: " + str(nr_of_connections))
    return nr_of_connections


async def remove_connection_from_count():
    global nr_of_connections
    nr_of_connections = nr_of_connections - 1
    print("Active connections: " + str(nr_of_connections))

#----------------------------------------------------------------------------------------------------
# LED
#----------------------------------------------------------------------------------------------------

async def blink_led():
    while True:
        led.value(1)
        await asyncio.sleep_ms(500)
        led.value(0)
        await asyncio.sleep_ms(500)
        
#----------------------------------------------------------------------------------------------------
# Main
#----------------------------------------------------------------------------------------------------

asyncio.create_task(blink_led())
asyncio.create_task(run_server())

loop = asyncio.get_event_loop()
try:
 loop.run_forever()
except KeyboardInterrupt:
  pass
