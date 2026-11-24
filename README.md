# ZTE MF297D — OpenWrt + NSS ve LuCI güncelleme

## Xray/VPN performans düzeltmeleri (kaynak güncellemesi)

Sorumluluk reddi. Cihazın bilinen bir brick kurtarma yöntemi yok. Uart erişimi bulamadık. Cihazınızı brick ederseniz çöp etmiş olursunuz. Sorumluluk tamamen size aittir.

MF297D NSS için IPv4 TX checksum, NSS sahibiyle uyumlu TSO kontrolü ve WAN
GRO/GSO durum düzeltmesi eklendi. Özgün Xray ile ölçümler:

- TTL 64 açık uzun internet VPN testleri: **345–438 Mbps**; 438 Mbps sabit hız değildir.
- Geçici CPU1 yerleşimiyle en yüksek: **473 Mbps**; sürekli hız garantisi değildir.
- Yaklaşık **202 Mbps** sabit VPN trafiğinde ortalama **%52 CPU**.
- Ayrı yerel TLS/VLESS Vision testi: **574 Mbps**; internet hızı değildir.

Canlı test LAN1 ve IPv4 üzerinde yapıldı. Servis yeniden başlatma, otomatik
tekrar uygulama, yanlış çekirdek kimliğini reddetme ve geri alma doğrulandı.
Yeniden açılış sonuçları ve test kapsamı
[VPN/TTL doğrulama belgesinde](docs/VPN-TTL-VALIDATION.md).
CPU sabitleme veya değiştirilmiş Xray kalıcı olarak eklenmedi.

**TTL sabitleme varsayılan olarak kapalıdır.** LuCI'de Network → TTL Control
sayfasından isteğe bağlı açılır; hazır IPv4 değeri 64'tür. TSO/GRO performans
düzeltmeleri TTL kapalıyken de etkindir. Mevcut derleme ayarların korunur.

**Bu düzeltmeler kaynak kodundadır. Önceden yayımlanan Release imajları bunları
içermez; kaynakları güncelleyip firmware'i yeniden derlemelisin.** Çekirdek modülü
her imajın kendi çekirdeğiyle derlenir; başka imajdan `.ko` kopyalama.
Mevcut derleme alanında örnek:

```sh
cd ~/MF297D
git pull --ff-only
sh nss/build.sh nand ~/build-mf297d-nand
```

[Teknik açıklama, testler ve devre dışı bırakma](nss/HOST-TX-TUNING.md).


## OpenWrt zaten kuruluysa: arayüzden güncelle

**LuCI sysupgrade desteği eklendi ve gerçek NAND yükseltmesiyle test edildi.**
`fit-v1` açılış desteği etkin cihazda:

1. [Güncel Release'ten](https://github.com/ozgunokan/ZTE-MF297D-OpenWRT/releases/latest) **`openwrt-mf297d-nss-sysupgrade.bin`** indir.
2. **<http://192.168.1.1> → System → Backup / Flash Firmware** bölümünü aç.
3. **Flash new firmware image** ile dosyayı seç. Ayarların kalsın istiyorsan **Keep settings** açık olsun.
4. Doğrulama sonrası **Continue** ile yükle; birkaç dakika güç ve Ethernet bağlantısını kesme.

**RESET kurtarması, radyo firmware'leri, ART/MAC ve bootloader korunur.** Normal
sysupgrade ENV'ye de yazmaz. Eski `...-nand.bin` bu dosyayla aynı biçimde değildir;
arayüzde yalnız **`...-sysupgrade.bin`** kullanılır.

[Basit güncelleme ve kendi firmware'ini derleme](docs/SYSUPGRADE.md) ·
[Eski kurulumda tek seferlik etkinleştirme](docs/SYSUPGRADE-BOOTSTRAP.md)

## Stok Turkcell sisteminden ilk kurulum

Sıra: **1. Telnet → 2. yükleyiciyi aktar/hazırla → 3. RAM'de aç ve yedekle →
4. RESET kurtarmasını doğrula → 5. en son NAND'a kur.**

Bu sürümde stok RAM yükleyicisi, iki aşamalı ilk NAND/kurtarma kurucusu ve
CPU/Wi-Fi LED düzeltmeli imajlar birlikte veriliyor. **Yeni stoktan ilk kurulum
kiti canlı bir stok cihazda henüz baştan sona denenmedi; deneysel ön sürümdür.**
Emülasyon, stok yedekleriyle hazırlama ve mevcut çekirdekte rootfs testleri geçti.
Genel RAM imajı ayrıca mevcut OpenWrt üzerinden canlı açıldı: iki CPU, NSS,
iki Wi-Fi radyosu ve IPv4/IPv6 iletimi geçti. Bu, stoktan ilk NAND kurulumunun
canlı testi değildir.
Çalışan cihazı stok yazılıma döndürerek test edilmedi.

Doğrulanan donanım/firmware: **ZTE MF297D, Turkcell B18**. Başka model/sürüm
desteklenmez. Stok sistem 32 bit ARM'dır; `kexec-aarch64` dosyasını tek başına
stokta çalıştıramazsın. İlk RAM geçişini aşağıdaki **Stok RAM** aracı yapar;
sonraki bakım geçişlerinde gerçek AArch64 kexec kullanılır.

## Komutları nerede çalıştıracağım?

| Etiket | Neresi? |
| --- | --- |
| PC Windows | Bilgisayardaki PowerShell, tarayıcı veya EXE. |
| PC Ubuntu | Bilgisayardaki Ubuntu/WSL terminali; modem terminali değil. |
| Modem Telnet/SSH | Modeme bağlandıktan sonraki komut ekranı. |

Kurulumda kablo **PC ↔ modem LAN1/LAN2/LAN3** arasında kalır. Yalnız 1B'deki ACS
Telnet açma işlemi için WAN kullanılır; ne zaman LAN'a dönüleceği orada yazıyor.
PC Ethernet **192.168.1.2/24**, modem **192.168.1.1**. Ethernet ağ geçidi/DNS
boş; PC'nin internet için kullandığı Wi-Fi değişmeyecek.

> **Windows 10/11 + WSL2 notu:** Ayrı bir Ubuntu bilgisayarı veya VMware kurmadan
> Windows üzerinde `wsl --install -d Ubuntu-24.04` ile kurulan WSL2 Ubuntu
> terminalinden tüm **PC Ubuntu** adımları çalıştırılabilir. Evdeki ana router'ınız
> da `192.168.1.1` kullanıyorsa, kurulum sırasında IP çakışmasını önlemek için
> ana ağdan geçici olarak ayrılın veya ikinci bir Ethernet adaptöründe ayrı alt ağ
> kullanın.

## İndir

[Bütün dosyalar — Release](https://github.com/ozgunokan/ZTE-MF297D-OpenWRT/releases/tag/mf297d-2026.11.20-install-kit.3)

| Dosya | Ne işe yarıyor? |
| --- | --- |
| MF297D-Telnet-CFG.exe | Kendi CFG yedeğinden LAN Telnet açık CFG üretir. |
| MF297D-Yerel-Yonetici.exe | ACS üzerinden sUser/LAN Telnet yardımcısı. |
| MF297D-Stok-RAM.zip | Stok B18 için EXE, ARM32 modüller, kernel ve RAM dosya sistemi. |
| mf297d-tools.zip | AArch64 kexec, kişiselleştirme ve ilk/güncelleme kurulum araçları. |
| openwrt-mf297d-6.18.60-nss-initramfs.itb | Genel RAM imajı ve kurucunun RAM şablonu. |
| RAM-PROFILE.json | Yukarıdaki RAM imajına ait hash ve yerleşim bilgisi; aynı sürümden indir. |
| openwrt-mf297d-6.18.60-nss-nand.bin | Kernel + hizalı rootfs paketi; kurucu kullanır. |
| mf297d-nss-source.zip | DTS, yamalar, profiller, stok yükleyici/kurucu kaynakları. |
| VALIDATION.json / SHA256SUMS | Test kapsamı ve bütün dosyaların SHA256 değerleri. |

**NAND `.bin` dosyası factory veya sysupgrade imajı değildir. Stok firmware
güncelleme ekranına yükleme.** Stok işletim sistemi ancak son B aşamasında
kaldırılır. Korunan stok yedekleri ve radyo verileri her cihazın kendisine aittir.

## 1. İlk iş: LAN Telnet aç


Doğrulanan stok sürüm **CR_TKCTURMF297DV1.0.0B18**. Modem zaten OpenWrt
çalıştırıyorsa bu adımı atla; stok CFG'yi OpenWrt'ye yükleme.

### 1A. CFG dosyasıyla

**PC / Windows:**

1. Kendi modeminin **yapılandırma yedeğini (`.CFG`)** al. Firmware `.bin` veya
   ham flash yedeği değil. Panelde yedekleme yoksa 1B'deki uygulamanın
   **Yedekler → Config** işlemiyle alınabilir.
2. Orijinal CFG'yi sakla. `MF297D-Telnet-CFG.exe` dosyasına çift tıkla.
3. İlk pencerede kendi orijinal CFG dosyanı seç.
4. İkinci pencerede yeni dosyayı **MF297D-LAN-Telnet.CFG** adıyla kaydet.
5. Araç yalnız `telnet_lan_enable=0` değerini `1` yapar. Şifreleri değiştirmez;
   modeme kendisi dosya göndermez.
6. Stok panelinde **ayar/config geri yükleme** seçeneği varsa yeni CFG'yi
   oradan yükle. Bu, firmware güncelleme ekranı değildir. Modemin yeniden
   açılmasını bekle. **Config içe aktarma menüsü yoksa 1B yöntemini kullan.**

Bizim testte kullanılan eski CFG, test cihazının şifrelerini ve kimlik
bilgilerini içeriyor. Herkese o dosyayı vermek yerine bu araç herkesin kendi
yedeğinden aynı Telnet değişikliğini üretir. Çıktı dosyasını GitHub'a yükleme.

Python ile alternatif, **PC terminalinde**:

```sh
python tools/telnet_cfg.py kendi-yedegim.CFG --out MF297D-LAN-Telnet.CFG
```

### 1B. sUser şifresini bilmiyorsan veya CFG geri yükleme menün yoksa

**PC / Windows ve stok modem paneli:**

1. [Npcap](https://npcap.com/#download) kur. Diğer TR069ACS uygulamalarını kapat.
2. `MF297D-Yerel-Yonetici.exe` aç. **Yönetici olarak yeniden aç** düğmesine
   basıp Windows onayını ver.
3. Modemin panelinde çalışma modunu **Kablolu genişbant**, WAN bağlantı türünü
   **Dinamik IP / DHCP** yap.
4. Ethernet kablosunu **PC ↔ modem WAN** olarak bağla.
5. Uygulamada doğru fiziksel **Ethernet** adaptörünü seç. **WAN servislerini
   başlat** düğmesine bas. Bu aşamada PC Ethernet'i `192.168.50.1/24` yapılır.
6. Modemi normal yeniden başlat. Uygulamada cihazın ve **sUser** hesabının
   görülmesini bekle.
7. Kullanacağın sUser parolasını gir. Mevcut parolayı bilmiyorsan **sUser
   parolasını değiştir** kutusunu seç. **sUser + LAN Telnet uygula** düğmesine bas.
8. Başarı ve geçici WAN Telnet'in kapatıldığı sonucu gelince, kablo hâlâ
   WAN'dayken **WAN servislerini durdur** düğmesine bas.
9. Kabloyu **WAN'dan çıkarıp LAN1/LAN2/LAN3'e** tak.
10. **LAN root bağlantısını doğrula** düğmesine bas. PC `192.168.1.2/24` olur;
    modem `192.168.1.1:2323` üzerinden kontrol edilir.

ACS EXE'sinin bütün akışı fabrika ayarlı ikinci cihazda uçtan uca denenmedi;
aynı modem üzerindeki erişim adımları ayrı komutlarla doğrulandı.
[Uygulama ayrıntıları](tools/windows-manager/README.md).

### 1C. Açıldığını kontrol et

**PC / Windows:** PuTTY'de tür **Telnet**, adres **192.168.1.1**, port **2323**.
Kullanıcı **sUser**, parola yukarıda belirlediğin sUser parolası. Paneldeki
`admin` parolasıyla aynı olmak zorunda değil. Windows Telnet istemcin kuruluysa:

```text
telnet 192.168.1.1 2323
```

**MODEM / Telnet — giriş yaptıktan sonra:**

```sh
id
uname -m
uname -r
nv get telnet_lan_enable
```

`id` içinde **uid=0**, son komutta **1** görmelisin.

## 2. Stok RAM yükleyicisini hazırla ve kontrol et


PC Ethernet `192.168.1.2`, maske `255.255.255.0`, ağ geçidi/DNS boş.
Kablo **PC ↔ modem LAN1/LAN2/LAN3** arasında. Modem `192.168.1.1:2323` Telnet.

ZIP'i örneğin `C:\MF297D\MF297D-Stok-RAM` içine çıkar. PowerShell:

```powershell
cd C:\MF297D\MF297D-Stok-RAM
.\MF297D-Stok-RAM.exe --check
```

Sorunca **sUser parolasını** gir. Parola komuta yazılmaz, kaydedilmez.
Sürüm/ABI kontrolü hata verirse devam etme.

Dosyaları modem PC'den yerel TCP18869 üzerinden alır; **TFTP kullanılmaz**.
Windows engellerse **Yönetici PowerShell** ile yalnız bu bağlantıya izin ver:

```powershell
New-NetFirewallRule -DisplayName MF297D-RAM-Aktarim -Direction Inbound -Protocol TCP -LocalPort 18869 -LocalAddress 192.168.1.2 -RemoteAddress 192.168.1.1 -Action Allow
```

## 3. OpenWrt'yi önce RAM'de aç

Normal **PC Windows / PowerShell** terminalinde:

```powershell
.\MF297D-Stok-RAM.exe --boot
```

Araç dosyaları aktarır, SHA256/CRC ve hazırlık modülünü kontrol eder, Wi-Fi/USB
yardımcılarını durdurur ve RAM geçişini gönderir. **NAND/ENV yazmaz.** Yaklaşık
90 saniye sonra SSH22 açılmasını ve bütün 25 NAND bölümünün salt okunur olmasını
kontrol eder. Doğrulama başarısızsa otomatik tekrar yapmaz.

Bu ilk RAM ortamı kurulum içindir; NSS ve Wi-Fi başlangıçta kapalıdır, Ethernet
ve LuCI kullanılır. `reboot` stok sisteme döner; henüz kalıcı OpenWrt kurulmadı.
İş bitince eklenen Windows kuralını **Yönetici PowerShell** ile kaldır:

```powershell
Remove-NetFirewallRule -DisplayName MF297D-RAM-Aktarim
```

Python alternatifi: `python boot.py --bundle . --boot`; gözlem için Paramiko gerekir.

### 3A. PC Ubuntu: kendi yedeğini al, kurulum dosyalarını hazırla

Ubuntu 24.04/Python3.12 kullan. İndirilen `.itb`, `.bin`, `RAM-PROFILE.json`
dosyalarını `~/MF297D-kurulum` klasörüne koy; `mf297d-tools.zip` dosyasını da
bu klasöre aç. Kexec dosyası `~/MF297D-kurulum/mf297d-tools/kexec-aarch64` olacak.

```sh
sudo apt update
sudo apt install gh git python3 python3-paramiko gcc-aarch64-linux-gnu libc6-dev-arm64-cross mtd-utils squashfs-tools unzip
gh auth login
gh repo clone ozgunokan/ZTE-MF297D-OpenWRT ~/MF297D
cd ~/MF297D
python3 stock/prepare_install.py --nand ~/MF297D-kurulum/openwrt-mf297d-6.18.60-nss-nand.bin --ram ~/MF297D-kurulum/openwrt-mf297d-6.18.60-nss-initramfs.itb --profile ~/MF297D-kurulum/RAM-PROFILE.json --kexec ~/MF297D-kurulum/mf297d-tools/kexec-aarch64 --out ~/MF297D-ilk-kurulum
```

Bu komut **henüz flash yazmaz**. Bütün 25 fiziksel MTD veri alanını ve stok
UBI dosyalarını indirip boyut/SHA256 ile kontrol eder. `.CFG`, tam flash yedeğinin
yerine geçmez. Bu yedek data-only/ECC düzeltilmiştir; OOB'lu programlayıcı imajı değildir.
`~/MF297D-ilk-kurulum/backups` klasörünü ikinci bir yere kopyala.
Bu klasörü ve `owner` dosyalarını GitHub'a yükleme; sana özeldir.

Hazırlama sırasında kernel/model, tüm MTD'lerin salt okunur olması, stok hacim
düzeni, bootloader ve kendi MAC verin kontrol edilir. Hata varsa aşama A'ya geçilmez.

### 3B. Önce kurtarmayı kur — A aşaması

**Bu komut recovery hacmini ve bootloader ENV'sini yazar.** Stok işletim sistemi
hacimlerini henüz silmez. Güç kesilmemeli; hata sonrası otomatik tekrar yapılmaz.

```sh
cd ~/MF297D
python3 stock/install.py --ready ~/MF297D-ilk-kurulum --phase-a
```

Araç kexec/dosyaları **SCP yerine kendi SSH aktarımıyla** `/tmp` içine gönderir;
RAM bakım ortamını açar, dosyaları yeni RAM'e yeniden aktarır. Kurtarma imajını
yazıp geri okur; yalnız bu cihaza bağlı ENV yardımcı programını çalıştırır.
Stok kernel/rootfs hacimleri ve radyo firmware korunur. Sonunda yeniden başlar.

## 4. Fiziksel RESET kurtarmasını gerçekten dene

1. Ethernet LAN'da, PC `192.168.1.2/24` kalsın.
2. Modemin fişini çıkar.
3. **RESET'e basılı tutarken** fişi tak.
4. Fişi taktıktan **7 saniye sonra RESET'i bırak**.
5. Yaklaşık **90 saniye** bekle.

**PC Ubuntu:**

```sh
cd ~/MF297D
python3 stock/install.py --ready ~/MF297D-ilk-kurulum --verify-reset
```

Sadece paneli açılmış görmek yetmez: araç owner kimliğini, U-Boot'tan
**fiziksel RESET seçimiyle** açıldığını, RAM kökü, salt okunur NAND'ı ve korunan
bölüm hashlerini doğrular. Başarılıysa yerel RESET kanıtı kaydeder.
Bu kanıt olmadan B aşaması başlamaz. RESET kurtarma **TFTP beklemez**;
modemde kayıtlı kurtarma imajını açar.

## 5. PC Ubuntu: en son stok OS'yi kaldır ve NAND'a kur — B aşaması

**Bu komut stok işletim sistemi hacimlerini kaldırır.** Doğrulanmış kurtarma,
bootloader/ART/MAC ve radyo firmware korunur. Sonuç tek OpenWrt'dir.

```sh
cd ~/MF297D
python3 stock/install.py --ready ~/MF297D-ilk-kurulum --phase-b
```

Araç doğrulanan kurtarma oturumundan ayrı RAM bakımına geçer. Yedeklenmiş üst
NAND alanını hazırlar; eski UBI'nin alt 58MiB'inin ve korunan bölümlerin
değişmediğini kontrol eder. Rootfs ve boş overlay yazılıp doğrulanır; kernel
**en son** yazılır. İşlem sonunda normal yeniden başlar. Hata varsa logu ve
yedekleri sakla; komutu körlemesine tekrar çalıştırma. Otomatik yarım-kurulum
devam ettirme/rollback uygulaması bu kitte yoktur.

Yaklaşık 90 saniye sonra **PC Ubuntu**:

```sh
ssh root@192.168.1.1 'uname -r; cat /sys/devices/system/cpu/online; nss-status -j; df -h /overlay'
```

Kernel `6.18.60`, CPU `0-1`, NSS `active` beklenir. Tarayıcıda
`http://192.168.1.1` aç. Root parolasını belirle; Wi-Fi'ye şifre koyup etkinleştir;
SIM/APN'yi ayarla. Genel imaj kişisel Wi-Fi şifresi taşımaz ve radyolar başlangıçta kapalıdır.
İlk kurulumun başarılı sayılması için normal açılış ve RESET kurtarma geri dönüşü
cihaz üzerinde ayrıca doğrulanmalıdır. Kitin yeni sürümünde bu canlı uçtan uca
test henüz yapılmadı; çevrimdışı testler bunun yerine geçmez.

## Sık karşılaşılan sorunlar ve kurulum sonrası notlar

Aşağıdaki maddeler gerçek Turkcell B18 → OpenWrt + NSS → `fit-v1` / LuCI sysupgrade
kurulumunda doğrudan karşılaşılmış sorunlar ve çözümleridir:

### Kurulum sırasında

- **1B (ACS) adımında cihaz görünmüyor veya DNS/port çakışıyor:**
  Stok panelde çalışma modunun **Kablolu genişbant** ve WAN türünün **DHCP**
  yapıldığından emin ol. Windows'ta **Internet Connection Sharing (`SharedAccess`)**
  servisi `UDP/53` portunu tutuyorsa yerel DNS servisiyle çakışabilir; işlem
  sırasında `SharedAccess` servisini durdur.
- **`MF297D-Stok-RAM --boot` sırasında `can't create /sys/bus/platform/drivers/dwc3/unbind: File exists`:**
  Bazı durumlarda önceki aktarım adımında Telnet kabuğunda `set -C` (noclobber)
  açık kalabiliyor. `boot.py` üzerinden çalıştırırken `quiesce()` öncesinde
  `set +C` çalıştırılması gerekir.
- **3B (`--phase-a`) adımında `kexec_load failed: Resource busy` (`Can't kexec: CPUs are stuck in the kernel`):**
  Stok RAM DTB'sinde `maxcpus=1` kullanıldığında açılışta `S18mf297d-cpu` servisi
  `cpu1`'i çevrimiçi yapmayı dener; stok boot akışında bu işlem başarısız olunca
  çekirdek `cpus_stuck_in_kernel` sayacını artırır ve `kexec` reddedilir.
  Çözüm, geçici stok RAM DTB'sinde `maxcpus=1` yerine `nr_cpus=1` kullanıp
  (`build.py` ile CRC ve modülleri birlikte) yeniden derlemektir. Bu değişiklik
  yalnız geçici RAM yükleyicisini etkiler; kalıcı NAND OpenWrt yine `0-1` çift
  çekirdek açılır.
- **`prepare_install.py` ile `--phase-a` arasında modemi yeniden başlatınca `mtd17ro` / `mtd18ro` doğrulama hatası:**
  `mtd17` (`cfg-param`) ve `mtd18` (`log`) stok B18 her açıldığında güncellenir.
  `prepare_install.py` sonrası stok sisteme yeniden girilirse `--phase-a` hiçbir
  flash yazımı yapmadan güvenli şekilde durur. Hazırlık adımını kesintisiz aynı
  RAM oturumunda tamamla veya stok açılışı sonrası güncel hash'lerle yeniden hazırla.
- **İlk kurulum sonrası LuCI'den `...-sysupgrade.bin` (ör. DivineWRT) yüklenmiyor:**
  İlk kurulum kitinin (`install-kit.3`) yazdığı U-Boot ENV sabit kernel CRC'sine
  kilitlidir ve LuCI sysupgrade kancası (`/lib/upgrade/mf297d.sh`) henüz kurulu
  değildir. Önce tek seferlik **`fit-v1`** geçişini
  ([SYSUPGRADE-BOOTSTRAP.md](docs/SYSUPGRADE-BOOTSTRAP.md)) uygulaman gerekir.
  *(Not: `6.18.60` kurtarma imajıyla kurulan cihazlarda eski `6.18.55` sürüm
  denetimi ve stok kurucunun eklediği son `bootipq` yedeği nedeniyle betik
  uyumluluğunu geçiş öncesi kontrol et.)* `fit-v1` tamamlandıktan sonra tüm
  sonraki `...-sysupgrade.bin` güncellemeleri doğrudan LuCI'den tek tıkla yapılır.

### Kurulum sonrasında (Wi-Fi, LTE ve ağ ayarları)

- **Wi-Fi görünmüyor:**
  Temiz OpenWrt / DivineWRT kurulumunda güvenlik gereği 2.4 GHz ve 5 GHz radyoları
  varsayılan olarak kapalı (`disabled='1'`) gelir. LuCI → **Network → Wireless**
  üzerinden şifre belirleyip bölge kodunu **TR** seçerek radyoları etkinleştir.
- **SIM kart takılı ama LTE kendiliğinden bağlanmıyor:**
  `lte` arayüzü de ilk kurulumda varsayılan olarak kapalı (`auto='0'`,
  `autoconnect='0'`) gelir. Her açılışta otomatik bağlanması için LuCI →
  **Network → Interfaces → `lte` → Edit** menüsünden **Bring up on boot**
  seçeneğini aç (veya SSH ile `uci set network.lte.auto='1'`,
  `uci set network.lte.autoconnect='1'`, `uci commit network`, `ifup lte`).
  İlk bağlantıda QMI modemi SIM'i 1–2 kez yeniden başlatabilir; 15–30 saniye
  içinde `wwan0` IP alır.
- **Başka bir router'a (ör. Keenetic `192.168.1.1`) LAN'dan bağlayınca kablosuz internet kesiliyor:**
  Aynı ağda iki DHCP sunucusu çakışır. MF297D'yi erişim noktası (AP) olarak
  mevcut router'ın LAN portuna bağlayacaksan:
  1. MF297D LAN IP'sini boş bir adrese al (ör. `192.168.1.100`).
  2. **Network → Interfaces → `lan` → DHCP Server** sekmesinde **Ignore interface**
     işaretle; IPv6 sekmesinde **RA / DHCPv6 / NDP** seçeneklerini **disabled** yap.
  3. MF297D'nin kendi güncellemeleri için `lan` **IPv4 gateway** ve **DNS**
     alanına ana router IP'sini (`192.168.1.1`) yaz.
- **AP modundan bağımsız LTE / Xray router kullanımına geçince telefon bağlanamıyor veya internete çıkamıyor:**
  İki noktayı kontrol et:
  1. AP modu için eklenen `network.lan.gateway` ve `network.lan.dns` kayıtlarını
     mutlaka sil; aksi hâlde Ethernet çıkarıldığında trafik `wwan0` (LTE) yerine
     olmayan statik ağ geçidine gitmeye çalışır.
  2. `dnsmasq`, Ethernet kablosu ana router'a takılıyken yeniden başlatıldıysa
     ağda başka DHCP sunucusu gördüğü için kendi DHCP'sini başlatmayı reddedebilir
     (`refusing to start`). Ethernet kablosunu çıkardıktan sonra `dnsmasq`
     servisini yeniden başlat veya bağımsız kullanım için `dhcp.lan.force='1'`
     ayarını aç.

## Kaynak ve test

`loader/` ARM32 modül, ARM64 shim ve aktarım yardımcılarının kaynaklarını içerir.
Sabit paketi Zig ile yeniden derlemek: `python stock/build.py --bundle PAKET --zig ZIG_YOLU`.
Kernel/rootfs kaynak reçetesi `nss/` altındadır. `tests/test_handoff.py` gerçek
derlenmiş geçiş kodunu Unicorn ile çalıştırır; Capstone/Unicorn gerekir.
Yeni image/DTB ile eski sabit modül karıştırılmaz; CRC ve bellek tablosu birlikte üretilmelidir.

## Zaten bu projenin OpenWrt'si kuruluysa

Stok kurucusunu yeniden çalıştırma. [Mevcut NAND sistemini güncelleme ve temiz derleme](docs/NSS-GUNCELLEME.md)
anlatımını kullan. Kullanımdaki cihazda CPU ve LED düzeltmeleri ayrıca kalıcı kurulmuştur.

## Ubuntu / VMware Ubuntu'da derleme

Mevcut derleme alanında seçtiğin paketler korunur:

```sh
cd ~/MF297D
git pull
cd ~/build-mf297d-nand
cp .config .config.backup
make menuconfig
JOBS=8 sh ~/MF297D/nss/build.sh nand "$PWD"
```

Arayüze yükleyeceğin dosya `bin/mf297d/openwrt-mf297d-nss-sysupgrade.bin`.
Derlemek modeme kendiliğinden yazmaz. [Temiz alan kurulumu](docs/NSS-GUNCELLEME.md#3-ubuntuda-paket-ekleyip-derleme),
[sysupgrade adımları ve korunan bölümler](docs/SYSUPGRADE.md), lisanslar [NOTICE](NOTICE.md).
