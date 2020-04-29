from kivy.uix.boxlayout import BoxLayout
from kivymd.app import MDApp
from kivymd.uix.list import OneLineIconListItem, MDList
from plyer import gps
from kivy.properties import StringProperty, ObjectProperty
from kivy.clock import mainthread
from kivy.utils import platform
import json, time
from kivy.clock import Clock
from functools import partial
import httpx
import trio

async def send_data_to_awsiot_async(data, cert, root_ca):
    """
    This function publishes gps data to the AWS IOT Device gateway asynchronously
    """
    async with httpx.AsyncClient(cert=cert, verify=root_ca) as client:
        endpoint = 'https://a2dzivea2zp8mx-ats.iot.ap-south-1.amazonaws.com:8443/topics/trackersweb-iot-topic?qos=1'
        response = await client.post(endpoint, data=data)
        print('=====================>>>>>>>>>>>>>>===============')
        awsiot_resp = 'Data sent: {}'.format(data)
        print(awsiot_resp)
        print('Response status: {}'.format(response))
        print('Response body: {} '.format(response.text))
        return json.loads(data), json.loads(response.text)

class Trackersweb(MDApp):
    """
    The main app class. Extends from kivymd.app
    """
    gps_location = StringProperty()
    gps_location_raw = StringProperty('GPS_RAW_INITIAL_VALUE: from mobile')
    gps_status = StringProperty('Click Start to get GPS location updates')
    gps_stream_status = StringProperty('Click Start to stream to cloud')
    awsiot_resp = StringProperty('Not Streaming!')
    
    def request_android_permissions(self):
        """
        The request will produce a popup if permissions have not already been
        been granted, otherwise it will do nothing.
        """
        from android.permissions import request_permissions, Permission

        def callback(permissions, results):
            """
            Defines the callback to be fired when runtime permission
            has been granted or denied. 
            """
            if all([res for res in results]):
                print("callback. All permissions granted.")
            else:
                print("callback. Some permissions refused.")

        request_permissions([Permission.ACCESS_COARSE_LOCATION,
                             Permission.ACCESS_FINE_LOCATION], callback)
   
    def build(self):
        try:
            gps.configure(on_location=self.on_location, on_status=self.on_status)
        except NotImplementedError:
            import traceback
            traceback.print_exc()
            self.gps_status = 'GPS is not implemented for your platform'

        if platform == "android":
            print("gps.py: Android detected. Requesting permissions")
            self.request_android_permissions()

        self.load_kv('main.kv')

    def start(self, minTime, minDistance):
        self.gps_status = 'Click Stop to Stop GPS location updates'
        gps.start(minTime, minDistance)

    def stop(self):
        self.gps_status = 'Click Start to Start GPS location updates'
        gps.stop()

    def stream_start(self, minTime, minDistance):
        pub_cert = 'data/certs/01f7e16e80-certificate.pem.crt'
        private_key = 'data/certs/01f7e16e80-private.pem.key'
        root_ca = 'data/certs/AmazonRootCA1.pem'
        
        self.gps_stream_status = "Click \'Stop Streaming\' to stop streaming"
        data_sent, iot_response = trio.run(partial(send_data_to_awsiot_async, self.gps_location_raw, (pub_cert, private_key), root_ca))

        # To Do: Add continuous streaming
        # Clock.schedule_interval(partial(send_data_to_awsiot, self.gps_location_raw), 0.7)

        display_stream_details = {
            'Data Sent': data_sent,
            'Iot Cloud Response': iot_response
        }
        self.awsiot_resp = json.dumps(display_stream_details)
        print("IOT Resp: ", self.awsiot_resp)

    def stream_stop(self):
        self.awsiot_resp = 'Not Streaming'
        self.gps_stream_status = "Click \'Start Streaming\' to stream to Cloud"

    @mainthread
    def on_location(self, **kwargs):
        self.gps_location_raw = json.dumps(kwargs)
        self.gps_location = '\n'.join([
            '{}={}'.format(k, v) for k, v in kwargs.items()])

    @mainthread
    def on_status(self, stype, status):
        self.gps_status = 'type={}\n{}'.format(stype, status)

    def on_pause(self):
        gps.stop() 
        return True

    def on_resume(self):
        gps.start(1000, 0)
        pass    

class ContentNavigationDrawer(BoxLayout):
    """
    The contents of the main page in the app. 
    Extended in the main.kv file with : <ContentNavigationDrawer>
    """
    pass

if __name__ == '__main__':
    """
    Initializing the kivy app.
    """
    Trackersweb().run()

