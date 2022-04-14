import uasyncio as asyncio
import uerrno
import micropython
 
    
nr_of_connections = 0
buffers = []

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
    
    await add_connection_to_count()
        
    while True:

        await read_request(reader) 

        delay, memory_usage = await read_headers(reader)
        await do_dummy_operation(delay, memory_usage)
        
        await send_response(writer)
        
        await asyncio.sleep_ms(10)
        

#--------------------------------------------------

async def read_request(reader):
    
    items = await reader.readline()

    splitItems = items.decode('ascii').split()
    if len(splitItems) != 3:
        return
    _method, _path, _version = splitItems

    #print("Client:    "+ str(reader.get_extra_info('peername')) + " new request: " + items.decode('ascii')[:-2])


async def read_headers(reader) :
    
    delay = 0
    memory_usage = 0
    
    while True:
        items = await reader.readline()
        
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


async def send_response(writer) :

    gc.collect()
    text = str(gc.mem_alloc())

    await writer.awrite("HTTP/1.1 200 OK\r\n")
    await writer.awrite("Content-Length: " + str(len(text)) + "\r\n")
    await writer.awrite("\r\n")
    await writer.awrite(text)   

#----------------------------------------------------------------------------------------------------
# Server Helper
#----------------------------------------------------------------------------------------------------

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
