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

## SYSVOL replikatsioon

Replikatsioonivaade eristab AD andmebaasi DRS replikatsiooni, SYSVOL-i failide
sünkroonimist ja mõlema DC kohalike GPO-õiguste kontrolli. Üldolek ei ole roheline,
kui SYSVOL-i kontroll ebaõnnestub või viimane edukas sünkroonimine on üle 15 minuti
vana. DRS-i „Sünkrooni AD domeeniandmed” nupp ei kopeeri SYSVOL-i faile.

Paigaldaja lisab SYSVOL-i abiprogrammi ja systemd ühikud, kuid ei lülita neid
automaatselt sisse ega kirjuta üle olemasolevaid Unisoni profiile. Kasutusele
võtmiseks on vaja Unisoni mõlemas DC-s, töötavat root SSH võtmeautentimist ja
kontrollitud SSH hostivõtmeid. Repositooriumis ei ole privaatvõtmeid ega tegelikke
serveriaadresse.

1. Loo mõlemas DC-s root-omanduses `/etc/cockpit-samba-ad/sysvol.json`
   (õigused `0600`), lähtudes failist `sysvol.example.json`. Täpselt ühes DC-s
   peab `role` olema `coordinator`, teises `peer`; `peer` on teise DC aadress.
2. Koordinaatori `/root/.unison/sysvol.prf` peab sisaldama täpselt kahte juurt:

   ```text
   root = /var/lib/samba/sysvol
   root = ssh://root@dc2.example.test//var/lib/samba/sysvol
   auto = true
   batch = true
   perms = 0
   owner = false
   group = false
   times = false
   ```

   Mõlemad DC-d peavad kuuluma samasse domeeni. Ära kopeeri Linuxi numbrilisi
   kasutaja-/grupi-ID-sid ega `security.NTACL` atribuute DC-de vahel.
3. Käivita koordinaatoris esmane kontrollitud sünkroonimine:

   ```bash
   sudo /usr/local/libexec/cockpit-samba-sysvol-helper sync
   ```

4. Eemalda vana sünkroonimisskripti aktiivne cron-käivitus, et ajastusi oleks üks.
   Seejärel lülita automaatne sünkroonimine Cockpiti replikatsioonivaates sisse.

Cockpitist saab mõlemas DC-s automaatse sünkroonimise sisse/välja lülitada ja
SYSVOL-i kohe sünkroonida. Partneri vaates suunatakse need toimingud SSH kaudu
koordinaatorisse, mitte ei käivitata teist ajastust. Automaatne töö kasutab
`cockpit-samba-sysvol.timer` ühikut: käivitus pärast alglaadimist ja seejärel
iga viie minuti järel. Pika töö ajal teist Unisoni käivitust ei alustata.

Pärast failide ülekannet tuletab kumbki DC GPO-õigused oma AD andmebaasist ning
taastab ainult erinevad õigused. Taastatakse ka Samba kontrollitavad SYSVOL-i
baaskataloogide õigused. SYSVOL-is olevate muude andmejagamiste sisu õigusi ei
kirjutata rekursiivselt üle. Kõik kavandatud GPO-teed kontrollitakse enne
muutmist; sümbollinke ja puuduvaid GPO-katalooge käsitletakse veana.

Unisoni konflikt või ajalõpp ei muutu edukaks tulemuseks. Ka osalise ülekande
korral üritatakse mõlemas DC-s õigused taastada ning viga jääb nähtavaks. AD-s
ja SYSVOL-is samaaegsete muudatuste tõttu puuduv GPO-kataloog võib vajada järgmist
sünkroonimiskatset. Konfliktseid faile ei kirjutata automaatselt ühe poole kasuks
üle; lahenda konflikt pärast varundamist Unisoni abil.

Õiguste varasemad omanikud, režiimid ja laiendatud atribuudid salvestatakse enne
muutmist root-only JSONL-failidesse kataloogis
`/var/backups/cockpit-samba-ad/sysvol-acls/`. Need on õiguste tagasipööramiseks,
mitte SYSVOL-i sisu või domeeni täieliku varukoopia asendus. Vanad ACL-varukoopiad
jäävad administraatori kontrolli alla ega kustu automaatselt.

Diagnostika:

```bash
sudo /usr/local/libexec/cockpit-samba-sysvol-helper status
sudo /usr/local/libexec/cockpit-samba-sysvol-helper check
sudo /usr/local/libexec/cockpit-samba-sysvol-helper repair
sudo journalctl -u cockpit-samba-sysvol.service
```

Viimane tulemus: `/var/lib/cockpit-samba-ad/sysvol-status.json`.
Kohalike õiguste paranduse tulemus: `sysvol-acl.json` samas kataloogis.
