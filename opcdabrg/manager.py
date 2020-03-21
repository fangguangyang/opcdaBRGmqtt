import threading
import logging
import re
import time
import json
import os
from ping3 import ping
import configparser
import requests
import hashlib
from time import sleep
from opcdabrg.opcda import *
from opcdabrg.opcda_tunnel import OPCDATunnel


def GetFileMd5(filename):
    if not os.path.isfile(filename):
        return None
    myHash = hashlib.md5()
    f = open(filename, 'rb')
    while True:
        b = f.read(8096)
        if not b:
            break
        myHash.update(b)
    f.close()
    return myHash.hexdigest().upper()

class OPCDABRGManager(threading.Thread):
    def __init__(self, stream_pub):
        threading.Thread.__init__(self)
        self._thread_stop = False
        self._mqtt_stream_pub = stream_pub
        self._opcdaclient = None
        self._opcdatunnel = None

    @property
    def opcservers_list(self):
        result = opcServersList()
        return result

    def opctags_list(self):
        result = []
        return result

    def on_setConfig(self, opcConfig):
        if not self._opcdatunnel.mqtt_clientid:
            self._opcdatunnel.start_opctunnel(opcConfig)
            return {"status": "starting"}
        else:
            return {"status": "busying"}

    def on_setConfigForced(self, opcConfig):
        if self._opcdatunnel.opctunnel_clean():
            self._opcdatunnel.start_opctunnel(opcConfig)
        return {"status": "starting"}

    def on_getConfig(self):
        return self._opcdatunnel.get_opcConfig()

    def on_deviceRead(self):
        if self._opcdatunnel.opctunnel_isrunning():
            return self._opcdatunnel.get_opcDatas()
        else:
            return None

    def on_deviceWrite(self, tags, values):
        if not self._opcdatunnel.opctunnel_isrunning():
            return self._opcdatunnel.set_opcDatas(tags, values)
        else:
            return None

    def api_tunnelPause(self):
        return self._opcdatunnel.opctunnel_pause()

    def on_tunnelResume(self):
        return self._opcdatunnel.opctunnel_resume()

    def on_tunnelClean(self):
        return self._opcdatunnel.opctunnel_clean()

    def opctunnel_isrunning(self):
        return self._opcdatunnel.opctunnel_isrunning()

    def on_opcRead(self, client, items):
        datas = opcReadItem(client, items)
        return {"datas": datas}

    def on_event(self, event, ul_value):
        return True

    def start(self):
        self._opcdaclient = OpenOPC.client()
        self._opcdatunnel = OPCDATunnel(self, self._mqtt_stream_pub)
        self._opcdatunnel.start()
        threading.Thread.start(self)

    def run(self):
        while not self._thread_stop:
            time.sleep(1)
            # if self._opcdaclient.isconnected:
            #     try:
            #         datas = self.on_opcRead(self._opcdaclient, ['Random.Int1', 'Random.Int2', 'Random.Real4'])
            #         self._mqtt_stream_pub.opcdabrg_datas('x1x1', json.dumps(datas))
            #     except Exception as ex:
            #         logging.warning('readItem err!err!err!')
            #         logging.exception(ex)
            #         self._mqtt_stream_pub.opcdabrg_log_pub('x1x1', str(ex))
            #         self._opcdaclient.close()
            # else:
            #     print("opcda link status:: ", self._opcdaclient.isconnected)
            #     self._mqtt_stream_pub.opcdabrg_log_pub('x1x1', "opcda link error! ")
            #     self._opcdaclient.connect('Matrikon.OPC.Simulation.1')
        logging.warning("Close OPCDABRG!")

    def stop(self):
        self._opcdatunnel.stop()
        self._thread_stop = True
        self.join()
