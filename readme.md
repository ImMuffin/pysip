# SIP Proxy Ondrej Ambruš
GIT: https://github.com/ImMuffin/pysip
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

## Implementácia knižnice sipfullproxy.py
Po importovaní knižnice inicializujem premennú IP ktorou definujem adresu proxy serveru. Následne nastavím konfiguráciu logovania, vypíšem info o spustení serveru a jeho adresu. Po výpisoch nastavím globálne premenné v knižnici a spustím server.
``` python
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
```

## Registrácia účastníka
Registrácia účastníka je založená na jednoduchej výmene kde klient požiada o registráciu paketom REGISTER a server odpovedá paketom 200. [V tomto prípade bol paket upravený aby obsahoval informácie o tom k čomu došlo na serveri.](##Upravovanie-kódov)


![PCAP registracia](https://raw.githubusercontent.com/ImMuffin/pysip/master/img/Registracia.png)

V prvej výmene sa vráti odpoveď "Klient bol úspešne registrovaný!"

![PCAP opakovana registracia](https://raw.githubusercontent.com/ImMuffin/pysip/master/img/Opakovana_registracia.png)

V druhej výmene bol klient už registrovany, teda sa vráti odpoveď "Klient už bol registrovaný!"

## Vytočenie hovoru a zvonenie na druhej strane
Po vytočení čísla pošle volajúci na volané číslo pomocou proxy paket `INVITE`. Volaná strana na tento odpovedá zaslaním paketov `100 Trying` a `180 Ringing`. Proxy server zmení text týchto správ na "Druhá strana sa hľadá." a "Druhá strana vyzváňa." ([Viac v sekcii Úprava preposielaných sip kódov](###Úprava-preposielaných-sip-kódov))
![PCAP vytocenie a zvonenie](https://raw.githubusercontent.com/ImMuffin/pysip/master/img/Vyzvananie.png)

## Prijatie hovoru druhou stranou
Na prijatie hovoru odošle volaná strana paket `200 OK`. Volajúca strana potvrdí prijatie `200 OK` paketom `ACK`.

![PCAP volanie](https://raw.githubusercontent.com/ImMuffin/pysip/master/img/Volanie.png)

Hneď po prijatí paketu `200 OK` obe strany naviažu navzájom spojenie pomocou `RTP` paketov. Tie nie sú viditeľné na prvom obrázku keďže bol nahratý na proxy serveri ktorý samotná komunikácia obchádza.

![PCAP volanie s RTP](https://raw.githubusercontent.com/ImMuffin/pysip/master/img/Hovor_RTP.png)

Na tomto obrázku je vidno `RTP` komunikáciu ale iba jednu stranu zvyšnej komunikácie keďže bol nahrávaný na volajúcej strane.

## Ukončenie hlasového hovoru
K ukončeniu hovoru dochádza niekoľkými spôsobmi podľa aktuálneho stavu hovoru.
V prípade, že ukončujeme prebiehajúci pošle strana ktorá chce hovor ukončiť paket `BYE` na ktorý druhá strana odpovie `200 OK` a hovor je ukončený.

![PCAP ukončenie hovoru](https://raw.githubusercontent.com/ImMuffin/pysip/master/img/Volanie_zrusenie.png)

V prípade, že volaný odmietne hovor, odošle volajúcemu paket `603 Decline`. Volajúci na daný paket odpovie paketom `ACK`.

![PCAP odmietnutie](https://raw.githubusercontent.com/ImMuffin/pysip/master/img/Odmietnutie.png)

Nakoniec, pokiaľ chce volajúci zrušiť hovor predtým ako ho volaný zdvihne, odošle paket `CANCEL`. Volaná strana naň odpovie paketom `200 OK`, zruší zvonenie zariadenia a odošle `487 Request terminated`. Volajúca strana potvrdí prijatie `487 Request terminated` paketom `ACK`.

![PCAP zrusenie volajucim](https://raw.githubusercontent.com/ImMuffin/pysip/master/img/Zrusenie.png)

## Konferenčný hovor

Pri konferenčnom hovore dochádza k inicializácií tak ako pri klasickom hovore, až na to, že volajúci inicializuje niekoľko spojení naraz, podľa počtu účastníkov. V mojom prípade inicializuje 2 hovory zaslaním `INVITE` obom účastníkom. 

![PCAP zrusenie volajucim](https://raw.githubusercontent.com/ImMuffin/pysip/master/img/Konferencny_hovor.png)
## Presmerovanie

Hovor sa dá presmerovať po jeho prijatí. K samotnému presmerovaniu dochádza pomocou paketu `REFER`. Po jeho prijatí druhá strana odpovedá paketom `202 Accepted`. Následne posiela `INVITE` tretej strane a nadväzuje s ňou spojenie ako pri bežnom hovore.

![PCAP zrusenie volajucim](https://raw.githubusercontent.com/ImMuffin/pysip/master/img/Presmerovanie.png)

## Videohovor

Po naviazaní bežného hovoru sa dá spustiť videohovor. Pri spustení videohovoru incializátor odošle nový `INVITE` paket na ktorý druhá strana odpovie paketom `100 Trying`. Po akceptovaní videohovoru na druhej strane sa odošle paket `OK 200` čím sa spustí videohovor.

![PCAP zrusenie volajucim](https://raw.githubusercontent.com/ImMuffin/pysip/master/img/Videohovor.png)

---

## Denník hovorov
Denník hovorov som implementoval pomocou novej `class`. Táto sa inicializuje na začiatku každého hovoru a obsahuje adresy oboch strán, čas inicializácie, časy zodvihnutia, ukončenia a dĺžku hovoru. Pri vytvorení sa nastaví `status = 'RINGING'` čo je prvé štádium hovoru.
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
Inicializácia nového hovoru, nastavenie IP adries, pridanie hovoru do zoznamu a zápis do logu.
``` python
...
new_call = call(origin, destination)
logging.info("Klient %s vola klientovi %s." % (new_call.source_address, new_call.destination_address))
call_list.append(new_call)
...
```
Po zodvihnutí (teda prijatí kódu `200`) sa prezre zoznam hovorov. Pokiaľ sa v ňom nachádza hovor medzi danými účastníkmi nastaví sa na `CALLING`, nastaví čas zdvihnutia hovoru a urobí sa zápis do logu. V prípade, že server dostane kód `603` alebo `486` a hovor medzi danými účastníkmi iba zvoní, nastaví sa na `DECLINED` a urobí sa zápis do logu. S takýmto hovorom sa ďalej nič nerobí, keďže bol ukončený.
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
Pokiaľ server dostane ukončujúci paket `BYE`, nastaví hovor na status `ENDED`, spraví zápis do logu pričom vypočíta dĺžku hovoru pomocou času zdvihnutia a ukončenia. Pokiaľ volajúci ukončí hovor pred zdvihnutím, status sa nastaví na `CANCELED` a urobí sa zápis do logu.
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
### Ukážka logu hovorov
``` log
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
V kóde upravujem SIP kódy na dvoch miestach. Prvým je úprava kódov ktoré server posiela, tieto obsahujú spresňujúcu správu k danému kódu. Taktiež upravujem kódy preposielané serverom tak aby bol ich text po slovensky.
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
Pri odosielaní upravených kódov sa robia zápisy do logu pre lepšie sledovanie užívateľských požiadaviek.
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