# SIP Proxy Ondrej Ambruš
## Zadanie
```
Rozsah povinných funkcionalít:
- Registrácia účastníka (bez nutnosti autentifikácie)
- Vytočenie hovoru a zvonenie na druhej strane
- Prijatie hovoru druhou stranou, fungujúci hlasový hovor
- Ukončenie hlasového hovoru (prijatého aj neprijatého)
Ak sú splnené všetky tieto podmienky, študent získava 5 bodov, ktoré sú minimom na absolvovanie 
tohoto zadania.

Doplnkové funkcionality (ktoré môžete, ale nemusíte urobiť):
- Možnosť zrealizovať konferenčný hovor (aspoň 3 účastníci)
- Možnosť presmerovať hovor
- Možnosť realizovať videohovor
- Logovanie “denníka hovorov” – kto kedy komu volal, kedy bol ktorý hovor prijatý, kedy bol ktorý 
hovor ukončený, do ľubovoľného textového súboru v ľubovoľnom formáte
- Úprava SIP stavových kódov z zdrojovom kóde proxy, napr. “486 Busy Here” zmeníte na “486 
Obsadené”
Každá doplnková funkcionalita predstavuje plus 1 bod.
Počas prezentácie zadania musíte byť schopní na zariadení, kde beží ústredňa urobiť SIP trace a otvoriť 
ho pomocou tcpdump alebo Wireshark, a v primeranom rozsahu vysvetliť cvičiacemu, ako daná 
signalizácia prebieha.
```

## Registrácia účastníka
Registrácia účastníka je založená na jednoduchej výmene 


## Denník hovorov
``` python
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
```

``` python
...
new_call = call(origin, destination)
logging.info("Klient %s vola klientovi %s." % (new_call.source_address, new_call.destination_address))
call_list.append(new_call)
...
```

``` python
...
for c in call_list:
if (destination in c.address_list) and (origin in c.address_list) and c.status == "CALLING":
    c.status = "ENDED"
    c.end_time = time.time()
    c.duration = round(c.end_time - c.start_time)
    logging.info("Hovor medzi %s a %s bol ukonceny. Trval: %s sekund." % (c.destination_address, c.source_address, c.duration))
elif (destination in c.address_list) and (origin in c.address_list) and c.status == "RINGING":
    c.status = "CANCELED"
    logging.info("Klient %s zrusil hovor s %s." % (c.source_address, c.destination_address))
...
```

``` python
...
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
...
```
### V
``` json
15:32:40:INFO:Sip proxy bolo spustene: Tue, 01 Mar 2022 15:32:40 
15:32:40:INFO:Serverova adresa je nastavena na 192.168.100.2
15:32:48:WARNING:Neregistrovana adresa '002@192.168.100.2' sa pokusila uskutocnit hovor!
15:32:51:INFO:Registroval sa novy klient 002@192.168.100.2
15:32:53:WARNING:Klient 002@192.168.100.2 sa pokusal volat na neexistujuce cislo 005@192.168.100.2.
15:33:11:INFO:Registroval sa novy klient 005@192.168.100.2
15:33:18:INFO:Klient 002@192.168.100.2 vola klientovi 005@192.168.100.2.
15:33:24:INFO:Klient 005@192.168.100.2 prijal hovor od 002@192.168.100.2.
15:33:33:INFO:Hovor medzi 005@192.168.100.2 a 002@192.168.100.2 bol ukonceny. Trval: 9 sekund.
15:33:37:INFO:Klient 002@192.168.100.2 vola klientovi 005@192.168.100.2.
15:33:39:INFO:Klient 005@192.168.100.2 prijal hovor od 002@192.168.100.2.
15:33:43:INFO:Hovor medzi 005@192.168.100.2 a 002@192.168.100.2 bol ukonceny. Trval: 4 sekund.
15:33:48:INFO:Klient 002@192.168.100.2 vola klientovi 005@192.168.100.2.
15:33:50:INFO:Klient 005@192.168.100.2 odmietol hovor od 002@192.168.100.2
15:33:55:INFO:Klient 002@192.168.100.2 vola klientovi 005@192.168.100.2.
15:33:56:INFO:Klient 002@192.168.100.2 zrusil hovor s 005@192.168.100.2.
```
## Upravovanie kódov
### Úprava preposielaných sip kódov
``` python
...
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
...
```
### Úprava generovaných kódov
``` python
...
    else:
        self.sendResponse("480 Volana stanica neexistuje!")
        logging.warning("Klient %s sa pokusal volat na neexistujuce cislo %s." % (origin, destination))
else:
    self.sendResponse("500 Chyba je na nasej strane!")
    logging.error("Cielova adresa nebola najdena!")
...
```