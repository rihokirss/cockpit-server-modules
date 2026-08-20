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

Proxy teenusele saab valida ükskõik millise serveris oleva sertifikaadi, sealhulgas
mitut domeeni sisaldava SAN-sertifikaadi. Sama domeeni saab kasutada mitme
teenuse jaoks, kui igal teenusel on erinev avalik HTTPS-port.

Moodul toetab ka mitut rakendust ühe HTTPS-domeeni alamradadel. Alamraja puhul
saab valida prefiksi eemaldamise, WebSocketi toe ning eraldi upstream-pordi.
Prefiksi eemaldamisel saadetakse rakendusele `X-Forwarded-Prefix` ja
`X-Original-URI` päised ning kohandatakse küpsiste teed ja upstream-suunamised.
