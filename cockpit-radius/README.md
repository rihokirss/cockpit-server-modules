# Cockpit RADIUS

Cockpiti moodul FreeRADIUSi haldamiseks Samba Active Directory domeenikontrolleris.

Funktsioonid:

- UniFi gateway'de, pääsupunktide ja võrkude RADIUS klientide haldus;
- Samba AD grupipõhine ligipääsupoliitika;
- WPA2/WPA3 Enterprise PEAP/EAP-MSCHAPv2;
- VPN-i MSCHAPv2 ja PAP autentimine;
- privaatne EAP CA ja serverisertifikaat ning CA allalaadimine;
- lokaalne PAP/MSCHAPv2 ahelatest, diagnostika ja sündmuslogi;
- UniFi seadistusjuhend koos kopeeritavate väärtustega.

Paigaldatud Cockpiti pakett: `/usr/local/share/cockpit/radius`

Privilegeeritud abiprogramm: `/usr/local/libexec/cockpit-radius-helper`

AD grupivärav: `/usr/local/libexec/cockpit-radius-ntlm-auth`

Serveri konfiguratsioon: `/etc/cockpit-radius/config.json`

Algse ligipääsugrupi leidmine arvestab ka nimekujudega `radius` ja `RADIUS`.

Kliendi lisamisel/muutmisel saab määrata `Message-Authenticator` nõude.
Vaikimisi on see automaatne. Vanema VPN gateway ühilduvusvalik on lubatud ainult
ühele NAS-i IP-aadressile (`/32` või IPv6 `/128`), mitte tervele kliendivõrgule.
Sellise kliendi `limit_proxy_state = yes` kaitse jääb sisse. Kasuta eraldi
gateway kliendikirjet, et mõne teise sama alamvõrgu seadme päring ei muudaks
gateway jaoks automaatselt nõutavaid atribuute. Jagatud võti peab kattuma UniFi
RADIUS profiiliga; see ei ole Windowsi VPN-i IPsec pre-shared key.
