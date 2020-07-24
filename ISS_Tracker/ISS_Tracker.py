import json
import time
import urllib2, base64
from ISStreamer.Streamer import Streamer

''' Test script to familiarize myself with Initial State and cloud services.  Tracks the location
of the ISS and the number of people on it.

script lifted from:
https://github.com/initialstate/ISS-tracker/wiki/Part-1.-Running-on-a-Personal-Computer

'''

FEEDS = ['iss-now', 'astros']
BUCKET_NAME = ':satellite_orbital:ISS Location'
BUCKET_KEY = 'isspython'
ACCESS_KEY = 'IlUUeZKC29aO07z942lXbwZVHbqbIMUZ'
MINUTES_BETWEEN_READS = 2

def get_reading(feed):
    api_read_url = urllib2.Request('http://api.open-notify.org/' + feed + '.json')
    print(api_read_url)
    try:
        f = urllib2.urlopen(api_read_url)
    except:
        print('failed to open JSON')
        return False
    json_reading = f.read()
    f.close()
    return json.loads(json_reading)

# Initialize Initial State Streamer
streamer = Streamer(bucket_name=BUCKET_NAME, bucket_key=BUCKET_KEY, access_key=ACCESS_KEY)

while True:
    for i in FEEDS:
        readings = get_reading(i)
        if (readings != False):
            if 'iss_position' in readings:
                latitude = readings['iss_position']['latitude']
                longitude = readings['iss_position']['longitude']
                location = str(latitude) + ',' + str(longitude)
                streamer.log(':globe_with_meridians:Current Coordinates', location)
                streamer.flush()
            if 'people' in readings:
                num = readings['number']
                streamer.log(':alien:How many people are in orbit?', str(num))

    time.sleep(60 * MINUTES_BETWEEN_READS)
