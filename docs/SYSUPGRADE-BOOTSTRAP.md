# Eski NAND kurulumunda sysupgrade'i bir kez etkinleştirme

**Yalnız eski proje NAND düzeni içindir.** Normal güncelleme adımları [SYSUPGRADE.md](SYSUPGRADE.md) içindedir. `fit-v1` geçişi yapılmış cihazda bu işlemler tekrarlanmaz. Stok kurulum bu araçla yapılmaz.

Bu geçişte yalnız açılış ENV'sinin ilk 256 KiB alanı güncellenir. Mevcut kernel, rootfs, RESET seçimi, kurtarma imajı ve radyo firmware'leri korunur. İşlem sırasında güç kesilmemelidir. Hazırlanan klasör cihazına özeldir; başka cihaza veya GitHub'a yükleme.

## 1. PC Ubuntu: hazırlık ve yedek

Mevcut root SSH erişimi ve Release'in `mf297d-tools.zip` içindeki `kexec-aarch64` dosyası gerekir.

```sh
sudo apt install python3-paramiko gcc-aarch64-linux-gnu libc6-dev-arm64-cross
cd ~/MF297D
git pull
python3 nss/tools/prepare-sysupgrade.py \
  --router root@192.168.1.1 \
  --kexec ~/mf297d-tools/kexec-aarch64 \
  --out ~/MF297D-upgrade-ready
python3 nss/tools/install-upgrade-support.py \
  --router root@192.168.1.1 \
  --guard ~/MF297D-upgrade-ready/mf297d-upgrade-guard \
  --backup ~/MF297D-upgrade-support-backup
```

Bu komut flash yazmaz. ENV, ayarlar, kurtarma kopyası ve korunan hacim hash'leri yedeklenir; yalnız bu ENV'ye uyan yardımcı hazırlanır. Gereken düzen: UBI 1/2 radyo firmware'leri, 4 kernel, 5 rootfs, 6 ayarlar, 7 kurtarma; 6.18.55 veya 6.18.60 kurtarma/bakım çekirdeği. Farklı düzen reddedilir.

## 2. PC Ubuntu: bir temiz açılış

```sh
cd ~/MF297D
python3 tools/prepare_ram_boot.py stage --out ~/MF297D-clean-start
ssh root@192.168.1.1 reboot
```

Yaklaşık iki dakika bekle. Ardından özgün başlangıç ayarlarını geri yükle; servisleri yeniden başlatma:

```sh
python3 tools/prepare_ram_boot.py restore --out ~/MF297D-clean-start
```

## 3. PC Ubuntu: hazırlanmış bakım sistemini RAM'den aç

```sh
ssh root@192.168.1.1 'mkdir -p /tmp/mf297d-bootstrap-boot'
cd ~/MF297D-upgrade-ready
scp -O Image maintenance.dtb bootargs.txt kexec BOOT-SHA256SUMS \
  root@192.168.1.1:/tmp/mf297d-bootstrap-boot/
```

Aşağıdaki komut **PC Ubuntu** terminalinden çalıştırılır:

```sh
ssh root@192.168.1.1 'set -e
test "$(cat /sys/devices/system/cpu/online)" = 0
test "$(cat /sys/kernel/kexec_loaded)" = 0
! grep -q "^ath11k " /proc/modules
! grep -q "^qca_nss_drv " /proc/modules
for s in mf297d-cpu nss; do
  ! grep -q mf297d-ram-skip- /etc/init.d/$s
done
cd /tmp/mf297d-bootstrap-boot
sha256sum -c BOOT-SHA256SUMS
chmod 500 kexec
ifdown lte 2>/dev/null || true
for s in mf297d-wifi mf297d-wifi-led; do
  [ ! -x /etc/init.d/$s ] || /etc/init.d/$s stop
done
wifi down
for r in /sys/class/remoteproc/remoteproc*; do
  test "$(cat "$r/state")" = offline
done
./kexec -c -l Image --dtb=maintenance.dtb --append="$(cat bootargs.txt)"
sync
mount -o remount,ro /overlay
./kexec -c -e'
```

SSH kesilir. Yaklaşık 90 saniye sonra RAM oturumuna ayrı SSH adıyla bağlan; fingerprint'i kontrol et:

```sh
ssh -o HostKeyAlias=mf297d-maintenance root@192.168.1.1 \
  'uname -r; cat /proc/cmdline'
```

`6.18.55` (veya ilk kurulum kitinde `6.18.60`) ve `mf297d.storage_expand=1` görünmelidir. Hazırlama aracı daha önce doğrulanan kendi kurtarma imajını kullanır; başka firmware'in bakım dosyası karıştırılmaz.

## 4. PC Ubuntu: dosyaları RAM'e yeniden gönder ve geçişi uygula

```sh
ssh -o HostKeyAlias=mf297d-maintenance root@192.168.1.1 \
  'touch /tmp/mf297d-source-keep; mkdir -p /tmp/mf297d-bootstrap'
cd ~/MF297D-upgrade-ready
scp -O -o HostKeyAlias=mf297d-maintenance \
  env-helper mf297d-upgrade-guard prefix.before.sha256 \
  volumes.before.sha256 apply-from-ram.sh SHA256SUMS \
  root@192.168.1.1:/tmp/mf297d-bootstrap/
ssh -o HostKeyAlias=mf297d-maintenance root@192.168.1.1 \
  'chmod 500 /tmp/mf297d-bootstrap/env-helper /tmp/mf297d-bootstrap/mf297d-upgrade-guard; sh /tmp/mf297d-bootstrap/apply-from-ram.sh'
```

Betik önce özgün ENV'yi ve korunan hash'leri doğrular, açılış geçişini yazar, geri okur ve yeniden başlatır. Sabit kernel CRC'si yerine `setenv verify yes` ve FIT hash kontrolü kullanılır; mevcut RESET ve kurtarma komutları değiştirilmez.

## 5. Kontrol ve sonraki güncellemeler

Yaklaşık 90 saniye sonra:

```sh
ssh root@192.168.1.1 '/usr/libexec/mf297d-upgrade-guard --check-env /dev/mtd10ro'
```

`MF297D sysupgrade boot layout ready` hazır olduğunu gösterir. İlk adımdaki destek kurucusu, yükseltme kancalarını eski firmware'in ayar alanına ekler; firmware veya ENV yazmaz. Yeni firmware derlemeleri bu dosyaları doğrudan rootfs içinde taşır.

Artık günlük güncellemeyi [LuCI'den](SYSUPGRADE.md) yap. Hazırlık/ENV geçişi her güncellemede çalıştırılmaz.
