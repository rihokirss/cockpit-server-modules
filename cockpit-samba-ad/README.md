# Cockpit Samba AD DC

Cockpiti moodul Samba Active Directory domeenikontrolleri haldamiseks.

## Funktsioonid

- domeeni, FSMO rollide, teenuse ja replikatsiooni ülevaade;
- kasutajate loomine, profiili muutmine, detailid, lubamine, keelamine,
  lukustuse avamine, parooli lähtestamine ja kustutamine;
- gruppide loomine ja muutmine ning otsitav visuaalne liikmevalik;
- arvutikontode ning organisatsiooniüksuste loomine, liigutamine,
  ümbernimetamine ja kustutamine;
- DNS-tsoonide ja A, AAAA, CNAME, MX, SRV, TXT, PTR ning NS kirjete
  loomine, muutmine ja kustutamine;
- GPO-de loetelu, loomine, varundamine ja kustutamine;
- DRS/KCC replikatsioon, `dbcheck`, `testparm`, teenuse logid ja restart;
- krüptitud saladusi sisaldav Samba online-domeenivarundus koos arhiivi
  tervikluse, SHA-256 kontrollsumma ja turvalise kustutamisega;
- Cockpitis nähtav muutmistoimingute auditilogi.

GPO ja online-varunduse toimingud küsivad domeeniadministraatori tunnuseid.
Parool edastatakse Cockpiti krüptitud sessioonis, kirjutatakse ainult toimingu
ajaks režiimiga `0600` faili `/run` all ning kustutatakse alati. Parooli ei
kirjutata auditilogisse.

## Asukohad

- Cockpiti pakett: `/usr/local/share/cockpit/samba_ad`
- helper: `/usr/local/libexec/cockpit-samba-ad-helper`
- varukoopiad: `/var/backups/samba-ad`
- audit: `/var/log/cockpit-samba-ad-audit.jsonl`
