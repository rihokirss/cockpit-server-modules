# Cockpit Sertifikaadid

Keskne Let's Encrypti sertifikaatide elutsükli ja edastuse moodul.

- sertifikaatide väljastamine, SAN-nimede muutmine ja käsitsi uuendamine;
- `certbot.timer` automaatuuenduse olek ja juhtimine;
- automaatne nginx reload pärast uuendust;
- sertifikaadi turvaline edastamine Synology DSM-i;
- DSM-is sama kirjeldusega sertifikaadi asendamine säilitab teenuste seosed.

## Paigaldatud asukohad

- kasutajaliides: `/usr/local/share/cockpit/certificates`
- privilegeeritud helper: `/usr/local/libexec/cockpit-certificates-helper`
- root-only seadistus: `/etc/cockpit-certificates/config.json`
- Certboti deploy-hook: `/etc/letsencrypt/renewal-hooks/deploy/cockpit-certificates`
- sündmuste logi: `/var/log/cockpit-certificates.log`

Synology konto parooli ei tagastata Cockpiti kasutajaliidesele. Seadistusfaili
õigused on `0600`. Automaatseks DSM API kasutamiseks peab konto kuuluma
`administrators` gruppi ning sellel ei tohiks olla interaktiivset 2FA nõuet.
