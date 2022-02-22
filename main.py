import sipfullproxy
from sipfullproxy import *
IP = '192.168.100.2'

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',filename='proxy.log',level=logging.INFO,datefmt='%H:%M:%S')
logging.info(time.strftime("Sip proxy bolo spustene: %a, %d %b %Y %H:%M:%S ", time.localtime()))
logging.info("Serverova adresa je nastavena na %s" % IP)
sipfullproxy.recordroute = "Record-Route: <sip:%s:%d;lr>" % (IP,PORT)
sipfullproxy.topvia = "Via: SIP/2.0/UDP %s:%d" % (IP,PORT)
sipfullproxy.server = socketserver.UDPServer((HOST, PORT), UDPHandler)
sipfullproxy.server.serve_forever()