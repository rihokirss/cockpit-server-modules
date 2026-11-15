# Cockpit RADIUS

Cockpiti moodul FreeRADIUSi haldamiseks Samba Active Directory domeenikontrolleris.

Funktsioonid:

- UniFi gateway'de, pääsupunktide ja võrkude RADIUS klientide haldus;
- Samba AD grupipõhine ligipääsupoliitika;
- WPA2/WPA3 Enterprise PEAP/EAP-MSCHAPv2;
- VPN-i MSCHAPv2 ja PAP autentimine;
- täiendav AD admin-roll ja kasutajale reserveeritud VPN-aadress;
- privaatne EAP CA ja serverisertifikaat ning CA allalaadimine;
- lokaalne PAP/MSCHAPv2 ahelatest, diagnostika ja sündmuslogi;
- UniFi seadistusjuhend koos kopeeritavate väärtustega.

Paigaldatud Cockpiti pakett: `/usr/local/share/cockpit/radius`

Privilegeeritud abiprogramm: `/usr/local/libexec/cockpit-radius-helper`

AD grupivärav: `/usr/local/libexec/cockpit-radius-ntlm-auth`

Serveri konfiguratsioon: `/etc/cockpit-radius/config.json`

Algse ligipääsugrupi leidmisel eelistatakse nime `ITK radius`; arvestatakse ka
varasemate nimekujudega `radius` ja `RADIUS`.

Kliendi lisamisel/muutmisel saab määrata `Message-Authenticator` nõude.
Vaikimisi on see automaatne. Vanema VPN gateway ühilduvusvalik on lubatud ainult
ühele NAS-i IP-aadressile (`/32` või IPv6 `/128`), mitte tervele kliendivõrgule.
Sellise kliendi `limit_proxy_state = yes` kaitse jääb sisse. Kasuta eraldi
gateway kliendikirjet, et mõne teise sama alamvõrgu seadme päring ei muudaks
gateway jaoks automaatselt nõutavaid atribuute. Jagatud võti peab kattuma UniFi
RADIUS profiiliga; see ei ole Windowsi VPN-i IPsec pre-shared key.

## VPN-i admin-roll

Vaates **Ligipääs → VPN-i administraatori roll** saab valida gateway, AD grupi,
VPN alamvõrgu, reserveeritud vahemiku ja kasutajate aadressid. Kasutajal peab
olema nii üldise RADIUS grupi kui ka admin-grupi liikmesus. Ilma admin-grupita
kasutaja autentib senise poliitika järgi ja saab NAS-i tavalisest poolist aadressi.
Iga admin kasutab üht reserveeritud aadressi ja korraga üht VPN-ühendust.

Roll rakendub alles eduka autentimise järel ja ainult valitud `/32` RADIUS
kliendi tegelikust paketi lähteaadressist saadud päringutele. Kliendi saadetud
`NAS-IP-Address` ei vali admin-rolli. Tavaline WiFi autentimine säilib.
Toetatud on konto nimi, `DOMAIN\\konto`, domeeni realm ja AD-s määratud UPN.
Winbindi grupivahemälu tõttu ei pruugi liikmesuse muudatus kohe nähtav olla.
Olemasoleva VPN-seansi õigused ei muutu enne ühenduse uuendamist.

Moodul genereerib `cockpit_vpn_role` FreeRADIUS mooduli ning mitte salajase
rollikirjelduse failis `/etc/freeradius/3.0/cockpit-vpn-role.json` (root:freerad,
0640). Abiprogramm `/usr/local/libexec/cockpit-radius-vpn-role` kontrollib AD
liikmesust ja tagastab `Framed-IP-Address` ainult kaardistatud adminile.
AD päringu vea korral autentimine keeldub; admin-grupist väljas konto ei saa
admin-aadressi. Grupile vastav GID leitakse igas DC-s eraldi.

Enne admin-aadressidele tulemüüriõiguste andmist tuleb UniFi dünaamilisest
VPN-poolist reserveeritud vahemik välja jätta, vanad seansid uuendada ja päris
VPN-kliendiga kontrollida, et gateway rakendab RADIUS-e antud aadressi.
Cockpiti vorm muudab ainult RADIUS-t; see ei muuda gateway aadressipooli ega
tulemüüri. Varu-RADIUS serverile tuleb salvestada sama roll ja aadressiseosed.
Autentimis- ja accounting-logid näitavad ka päringu lähteaadressi ning VPN-IP-d.

Kontrollid: `python3 -m unittest discover -s cockpit-radius` ja
`node --check cockpit-radius/app.js`.
