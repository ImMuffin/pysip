#    Copyright 2014 Philippe THIRION
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.

#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.

#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.

import socketserver
import re
import socket
#import threading
import sys
import time
import logging

from matplotlib.text import Text

HOST, PORT = '0.0.0.0', 5060
rx_register = re.compile("^REGISTER")
rx_invite = re.compile("^INVITE")
rx_ack = re.compile("^ACK")
rx_prack = re.compile("^PRACK")
rx_cancel = re.compile("^CANCEL")
rx_bye = re.compile("^BYE")
rx_options = re.compile("^OPTIONS")
rx_subscribe = re.compile("^SUBSCRIBE")
rx_publish = re.compile("^PUBLISH")
rx_notify = re.compile("^NOTIFY")
rx_info = re.compile("^INFO")
rx_message = re.compile("^MESSAGE")
rx_refer = re.compile("^REFER")
rx_update = re.compile("^UPDATE")
rx_from = re.compile("^From:")
rx_cfrom = re.compile("^f:")
rx_to = re.compile("^To:")
rx_cto = re.compile("^t:")
rx_tag = re.compile(";tag")
rx_contact = re.compile("^Contact:")
rx_ccontact = re.compile("^m:")
rx_uri = re.compile("sip:([^@]*)@([^;>$]*)")
rx_addr = re.compile("sip:([^ ;>$]*)")
#rx_addrport = re.compile("([^:]*):(.*)")
rx_code = re.compile("^SIP/2.0 ([^ ]*)")
#rx_invalid = re.compile("^192\.168")
#rx_invalid2 = re.compile("^10\.")
#rx_cseq = re.compile("^CSeq:")
#rx_callid = re.compile("Call-ID: (.*)$")
#rx_rr = re.compile("^Record-Route:")
rx_request_uri = re.compile("^([^ ]*) sip:([^ ]*) SIP/2.0")
rx_route = re.compile("^Route:")
rx_contentlength = re.compile("^Content-Length:")
rx_ccontentlength = re.compile("^l:")
rx_via = re.compile("^Via:")
rx_cvia = re.compile("^v:")
rx_branch = re.compile(";branch=([^;]*)")
rx_rport = re.compile(";rport$|;rport;")
rx_contact_expires = re.compile("expires=([^;$]*)")
rx_expires = re.compile("^Expires: (.*)$")

# global dictionnary
recordroute = ""
topvia = ""
registrar = {}

class call:
    address_list = []
    start_time = 0
    end_time = 0
    duration = 0
    def __init__(self, source, destination):
        self.source_address = source
        self.destination_address = destination
        self.address_list.append(self.source_address)
        self.address_list.append(self.destination_address)
        self.init_time = time.localtime()
        self.status = 'RINGING'

call_list = []

def hexdump( chars, sep, width ):
    while chars:
        line = chars[:width]
        chars = chars[width:]
        line = line.ljust( width, '\000' )
        logging.debug("%s%s%s" % ( sep.join( "%02x" % ord(c) for c in line ),sep, quotechars( line )))

def quotechars( chars ):
	return ''.join( ['.', c][c.isalnum()] for c in chars )

def showtime():
    logging.debug(time.strftime("(%H:%M:%S)", time.localtime()))

class UDPHandler(socketserver.BaseRequestHandler):   
    
    def debugRegister(self):
        logging.debug("*** REGISTRAR ***")
        logging.debug("*****************")
        for key in registrar.keys():
            logging.debug("%s -> %s" % (key,registrar[key][0]))
        logging.debug("*****************")
    
    def changeRequestUri(self):
        # change request uri
        md = rx_request_uri.search(self.data[0])
        if md:
            method = md.group(1)
            uri = md.group(2)
            if uri in registrar:
                uri = "sip:%s" % registrar[uri][0]
                self.data[0] = "%s %s SIP/2.0" % (method,uri)
        
    def removeRouteHeader(self):
        # delete Route
        data = []
        for line in self.data:
            if not rx_route.search(line):
                data.append(line)
        return data
    
    def addTopVia(self):
        branch= ""
        data = []
        for line in self.data:
            if rx_via.search(line) or rx_cvia.search(line):
                md = rx_branch.search(line)
                if md:
                    branch=md.group(1)
                    via = "%s;branch=%sm" % (topvia, branch)
                    data.append(via)
                # rport processing
                if rx_rport.search(line):
                    text = "received=%s;rport=%d" % self.client_address
                    via = line.replace("rport",text)   
                else:
                    text = "received=%s" % self.client_address[0]
                    via = "%s;%s" % (line,text)
                data.append(via)
            else:
                data.append(line)
        return data
                
    def removeTopVia(self):
        data = []
        for line in self.data:
            if rx_via.search(line) or rx_cvia.search(line):
                if not line.startswith(topvia):
                    data.append(line)
            else:
                data.append(line)
        return data
        
    def checkValidity(self,uri):
        addrport, socket, client_addr, validity = registrar[uri]
        now = int(time.time())
        if validity > now:
            return True
        else:
            del registrar[uri]
            logging.warning("Registracia cisla %s expirovala!" % uri)
            return False
    
    def getSocketInfo(self,uri):
        addrport, socket, client_addr, validity = registrar[uri]
        return (socket,client_addr)
        
    def getDestination(self):
        destination = ""
        for line in self.data:
            if rx_to.search(line) or rx_cto.search(line):
                md = rx_uri.search(line)
                if md:
                    destination = "%s@%s" %(md.group(1),md.group(2))
                break
        return destination
                
    def getOrigin(self):
        origin = ""
        for line in self.data:
            if rx_from.search(line) or rx_cfrom.search(line):
                md = rx_uri.search(line)
                if md:
                    origin = "%s@%s" %(md.group(1),md.group(2))
                break
        return origin
        
    def sendResponse(self,code):
        request_uri = "SIP/2.0 " + code
        self.data[0]= request_uri
        index = 0
        data = []
        for line in self.data:
            data.append(line)
            if rx_to.search(line) or rx_cto.search(line):
                if not rx_tag.search(line):
                    data[index] = "%s%s" % (line,";tag=123456")
            if rx_via.search(line) or rx_cvia.search(line):
                # rport processing
                if rx_rport.search(line):
                    text = "received=%s;rport=%d" % self.client_address
                    data[index] = line.replace("rport",text) 
                else:
                    text = "received=%s" % self.client_address[0]
                    data[index] = "%s;%s" % (line,text)      
            if rx_contentlength.search(line):
                data[index]="Content-Length: 0"
            if rx_ccontentlength.search(line):
                data[index]="l: 0"
            index += 1
            if line == "":
                break
        data.append("")
        text = "\r\n".join(data)
        self.socket.sendto(text.encode("utf-8"),self.client_address)
        
    def processRegister(self):
        fromm = ""
        contact = ""
        contact_expires = ""
        header_expires = ""
        expires = 10
        validity = 10
        authorization = ""
        index = 0
        auth_index = 0
        data = []
        size = len(self.data)
        for line in self.data:
            if rx_to.search(line) or rx_cto.search(line):
                md = rx_uri.search(line)
                if md:
                    fromm = "%s@%s" % (md.group(1),md.group(2))
            if rx_contact.search(line) or rx_ccontact.search(line):
                md = rx_uri.search(line)
                if md:
                    contact = md.group(2)
                else:
                    md = rx_addr.search(line)
                    if md:
                        contact = md.group(1)
                md = rx_contact_expires.search(line)
                if md:
                    contact_expires = md.group(1)
            md = rx_expires.search(line)
            if md:
                header_expires = md.group(1)
        
        # if rx_invalid.search(contact) or rx_invalid2.search(contact):
        #     if registrar.has_key(fromm):
        #         del registrar[fromm]
        #     self.sendResponse("488 Not Acceptable Here")    
        #     return
        if len(contact_expires) > 0:
            expires = int(contact_expires)
        elif len(header_expires) > 0:
            expires = int(header_expires)

        if expires == 0:
            if fromm in registrar:
                del registrar[fromm]
                self.sendResponse("200 Klient uspesne odregistrovany!")
                logging.info("Klient %s sa odregistroval." % fromm)
                return
        else:
            now = int(time.time())
            validity = now + expires

        if fromm in registrar:
            self.sendResponse("200 Klient uz bol registrovany!")
            logging.info("Klient %s uz registrovany." % fromm)
        else:
            self.sendResponse("200 Klient uspesne zaregistrovany!")
            logging.info("Registroval sa novy klient %s" % fromm)

        registrar[fromm]=[contact,self.socket,self.client_address,validity]
        self.debugRegister()

    def processInvite(self):
        origin = self.getOrigin()
        if len(origin) == 0 or not origin in registrar: # 
            self.sendResponse("400 Vasa adresa nie je registrovana!")
            logging.warning("Neregistrovana adresa \'%s\' sa pokusila uskutocnit hovor!" % origin)
            return
        destination = self.getDestination()
        if len(destination) > 0:
            if destination in registrar and self.checkValidity(destination):
                socket,claddr = self.getSocketInfo(destination)
                #self.changeRequestUri()
                self.data = self.addTopVia()
                data = self.removeRouteHeader()
                #insert Record-Route
                data.insert(1,recordroute)
                text = "\r\n".join(data)
                socket.sendto(text.encode("utf-8") , claddr)
                new_call = call(origin, destination)
                logging.info("Klient %s vola klientovi %s." % (new_call.source_address, new_call.destination_address))
                call_list.append(new_call)
            else:
                self.sendResponse("480 Volana stanica neexistuje!")
                logging.warning("Klient %s sa pokusal volat na neexistujuce cislo %s." % (origin, destination))
        else:
            self.sendResponse("500 Chyba je na nasej strane!")
            logging.error("Cielova adresa nebola najdena!")

    def processAck(self):
        destination = self.getDestination()
        if len(destination) > 0:
            if destination in registrar:
                socket,claddr = self.getSocketInfo(destination)
                #self.changeRequestUri()
                self.data = self.addTopVia()
                data = self.removeRouteHeader()
                #insert Record-Route
                data.insert(1,recordroute)
                text = "\r\n".join(data)
                socket.sendto(text.encode("utf-8"),claddr)

    def processNonInvite(self):
        origin = self.getOrigin()
        if len(origin) == 0 or not origin in registrar:
            self.sendResponse("400 Si sa sekol")
            return
        destination = self.getDestination()
        if len(destination) > 0:
            if destination in registrar and self.checkValidity(destination):
                socket,claddr = self.getSocketInfo(destination)
                #self.changeRequestUri()
                self.data = self.addTopVia()
                data = self.removeRouteHeader()
                #insert Record-Route
                data.insert(1,recordroute)
                text = "\r\n".join(data)
                socket.sendto(text.encode("utf-8") , claddr)
                for c in call_list:
                    if (destination in c.address_list) and (origin in c.address_list) and c.status == "CALLING":
                        c.status = "ENDED"
                        c.end_time = time.time()
                        c.duration = round(c.end_time - c.start_time)
                        logging.info("Hovor medzi %s a %s bol ukonceny. Trval: %s sekund." % (c.destination_address, c.source_address, c.duration))
                    elif (destination in c.address_list) and (origin in c.address_list) and c.status == "RINGING":
                        c.status = "CANCELED"
                        logging.info("Klient %s zrusil hovor s %s." % (c.source_address, c.destination_address))

            else:
                self.sendResponse("406 Vasa poziadavka bola zamietnuta!")
        else:
            self.sendResponse("500 Chyba je na nasej strane!")

    def processCode(self):
        origin = self.getOrigin()
        if len(origin) > 0:
            if origin in registrar:
                socket,claddr = self.getSocketInfo(origin)
                self.data = self.removeRouteHeader()
                data = self.removeTopVia()
                # uprava sip kodov
                code = data[0].split(" ")[1]
                if code == "100":
                    data[0] = "SIP/2.0 100 Druha strana sa hlada."
                elif code == "180":
                    data[0] = "SIP/2.0 180 Druha strana vyzvana."
                elif code == "603":
                    data[0] = "SIP/2.0 603 Hovor bol odmietnuty."
                elif code == "487":
                    data[0] = "SIP/2.0 487 Hovor bol zruseny."
                elif code == "486":
                    data[0] = "SIP/2.0 486 Ucastnik je obsadeny."    
                text = "\r\n".join(data)
                socket.sendto(text.encode("utf-8"),claddr)
                # spracovanie denniku hovorov
                if code == "200":
                    for c in call_list:
                        if (self.getDestination() in c.address_list) and (origin in c.address_list) and c.status == "RINGING":
                            c.status = "CALLING"
                            c.start_time = time.time()
                            logging.info("Klient %s prijal hovor od %s." % (c.destination_address, c.source_address))
                        
                if code == "603" or code == "486":
                    for c in call_list:
                        if (self.getDestination() in c.address_list) and (origin in c.address_list) and c.status == "RINGING":
                            c.status = "DECLINED"
                            logging.info("Klient %s odmietol hovor od %s" % (c.destination_address, c.source_address))
                
                
    def processRequest(self):
        if len(self.data) > 0:
            request_uri = self.data[0]
            if rx_register.search(request_uri):
                self.processRegister()
            elif rx_invite.search(request_uri):
                self.processInvite()
            elif rx_ack.search(request_uri):
                self.processAck()
            elif rx_bye.search(request_uri):
                self.processNonInvite()
            elif rx_cancel.search(request_uri):
                self.processNonInvite()
            elif rx_options.search(request_uri):
                self.processNonInvite()
            elif rx_info.search(request_uri):
                self.processNonInvite()
            elif rx_message.search(request_uri):
                self.processNonInvite()
            elif rx_refer.search(request_uri):
                self.processNonInvite()
            elif rx_prack.search(request_uri):
                self.processNonInvite()
            elif rx_update.search(request_uri):
                self.processNonInvite()
            elif rx_subscribe.search(request_uri):
                self.sendResponse("200 Tento server nepodporuje tuto funkciu ale OK :D")
            elif rx_publish.search(request_uri):
                self.sendResponse("200 Tento server nepodporuje tuto funkciu ale OK :D")
            elif rx_notify.search(request_uri):
                self.sendResponse("200 Tento server nepodporuje tuto funkciu ale OK :D")
            elif rx_code.search(request_uri):
                self.processCode()
            else:
                logging.error("Neznama poziadavka na server: %s" % request_uri)
                self.sendResponse("500 Chyba je na nasej strane")          
    
    def handle(self):
        data = self.request[0].decode("utf-8")
        self.data = data.split("\r\n")
        self.socket = self.request[1]
        request_uri = self.data[0]
        if rx_request_uri.search(request_uri) or rx_code.search(request_uri):
            self.processRequest()
        else:
            if len(data) > 4:
                showtime()
                logging.warning("---\n>> server received [%d]:" % len(data))
                hexdump(data,' ',16)
                logging.warning("---")

