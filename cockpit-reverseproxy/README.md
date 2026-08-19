# Cockpit Reverse Proxy

Kohalik Cockpiti moodul nginx reverse proxy ja WebSocketi haldamiseks.
Sertifikaatide väljastamine, uuendamine ja Synologysse edastamine asub eraldi
Cockpiti **Sertifikaadid** moodulis.

## Paigaldatud asukohad

- Cockpiti kasutajaliides: `/usr/local/share/cockpit/reverseproxy`
- Privilegeeritud helper: `/usr/local/libexec/cockpit-reverseproxy-helper`
- Teenuste andmed: `/etc/cockpit-reverseproxy/sites.json`
- Genereeritud nginx: `/etc/nginx/conf.d/cockpit-reverseproxy.conf`

Proxy teenusele saab valida ükskõik millise serveris oleva sertifikaadi, sealhulgas
mitut domeeni sisaldava SAN-sertifikaadi.
