# Cockpit Reverse Proxy

Kohalik Cockpiti moodul nginx reverse proxy ja WebSocketi haldamiseks.
Sertifikaatide väljastamine, uuendamine ja Synologysse edastamine asub eraldi
Cockpiti **Sertifikaadid** moodulis.

## Paigaldatud asukohad

- Cockpiti kasutajaliides: `/usr/local/share/cockpit/reverseproxy`
- Privilegeeritud helper: `/usr/local/libexec/cockpit-reverseproxy-helper`
- Teenuste andmed: `/etc/cockpit-reverseproxy/sites.json`
- Alamradade andmed: `/etc/cockpit-reverseproxy/routes.json`
- Ühisdomeenide andmed: `/etc/cockpit-reverseproxy/route-hosts.json`
- Genereeritud nginx: `/etc/nginx/conf.d/cockpit-reverseproxy.conf`
- Avalik sanitiseeritud teenusekataloog: `/var/lib/cockpit-reverseproxy/services.json`

Proxy teenusele saab valida ükskõik millise serveris oleva sertifikaadi, sealhulgas
mitut domeeni sisaldava SAN-sertifikaadi. Sama domeeni saab kasutada mitme
teenuse jaoks, kui igal teenusel on erinev avalik HTTPS-port.
Täisdomeeni teenuse saab siduda PM2 kasutaja ja rakenduse nimega, et avalik
aadress kuvataks PM2 protsessi juures ka siis, kui protsess parajasti ei tööta.

Moodul toetab ka mitut rakendust ühe HTTPS-domeeni alamradadel. Alamraja puhul
saab valida prefiksi eemaldamise, WebSocketi toe ning eraldi upstream-pordi.
Prefiksi eemaldamisel saadetakse rakendusele `X-Forwarded-Prefix` ja
`X-Original-URI` päised ning kohandatakse küpsiste teed ja upstream-suunamised.

## Teenuseportaal

Aktiivsed teenused ja alamrajad lisatakse vaikimisi avalikku kataloogi. Kirje
saab portaalist peita ning sellele saab määrata avaliku nime, kirjelduse ja
kategooria. Ainult täisdomeeni kirje, millel on valik „serveeri kataloogi“, saab
Nginxis täpse `/api/services` asukoha. JSON ei sisalda upstream-aadresse,
siseporte, sertifikaaditeid ega terviseinfot.
