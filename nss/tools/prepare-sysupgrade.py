#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Prepare the one-time, owner-bound boot migration for existing MF297D NAND.

Read-only preparation. The generated apply-from-ram.sh is run separately from
the matched RAM maintenance system; normal sysupgrade never writes ENV.
"""
from pathlib import Path
import argparse,hashlib,json,lzma,re,struct,subprocess,sys,zlib
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'tools'))
from upgrade_boot import migrate
from inspect_fit import fdt,inspect
from fdt_codec import encode

def sha(b):return hashlib.sha256(b).hexdigest()
def prepare(a):
    assert re.fullmatch(r'(?:[A-Za-z0-9_-]+@)?[A-Za-z0-9.:-]+',a.router)
    out=a.out.resolve();out.mkdir(parents=True,mode=0o700,exist_ok=False)
    def read(command):return subprocess.check_output(['ssh',a.router,command])
    assert read('cat /tmp/sysinfo/board_name').strip()==b'zte,mf297d'
    assert b'root=/dev/ubiblock0_5' in read('cat /proc/cmdline')
    assert read('cat /sys/class/ubi/ubi0/mtd_num').strip()==b'21'
    raw=read('cat /dev/mtd10ro');old,new,cmd,count=migrate(raw)
    (out/'ENV-before.private.bin').write_bytes(raw);(out/'ENV-after.private.bin').write_bytes(new+raw[262144:])
    prefix=read('for i in $(seq 0 20); do sha256sum /dev/mtd${i}ro; done')
    (out/'prefix.before.sha256').write_bytes(prefix)
    (out/'settings.private.tgz').write_bytes(read('tar -C / -czf - etc/config etc/dropbear etc/passwd etc/shadow etc/group etc/hosts root'))
    volumes={str(i):read(f'sha256sum /dev/ubi0_{i}').decode().split()[0] for i in [1,2,4,5,7]}
    recovery=read('cat /dev/ubi0_7');assert sha(recovery)==volumes['7'];(out/'recovery.private.itb').write_bytes(recovery)
    assert all(h['valid'] for image in inspect(out/'recovery.private.itb')['images'].values() for h in image['hashes'])
    tree=fdt(recovery);image=lzma.decompress(tree['/images/kernel-1']['data'],format=lzma.FORMAT_ALONE)
    km=re.search(rb'Linux version (6\.18\.(?:55|60)) ',image);assert km,'unsupported recovery kernel version'
    kver=km.group(1).decode()
    original=tree['/images/fdt-1']['data'];d=fdt(original);d['/chosen']['mf297d,storage-expand']=b''
    for name,v in d.items():
        if '/partitions/partition@' not in name or 'reg' not in v or 'label' not in v:continue
        if v['label'].lower()==b'0:appsblenv\0':v.pop('read-only',None)
        elif v['reg']==bytes.fromhex('02cc00000d340000'):v.pop('read-only',None);v['label']=b'maintenance_storage\0'
        else:v['read-only']=b''
    args=d['/chosen']['bootargs'].rstrip(b'\0').decode()+' mf297d.storage_expand=1'
    (out/'Image').write_bytes(image);(out/'maintenance.dtb').write_bytes(encode(d,original));(out/'bootargs.txt').write_text(args+'\n')
    def array(name,b):return 'static const unsigned char '+name+'[262144]={\n'+''.join(','.join(f'0x{x:02x}' for x in b[i:i+32])+',\n' for i in range(0,len(b),32))+'};\n'
    (out/'owner_env.h').write_text(array('probe_data',new)+array('before_data',old)+'\n#define EXPECTED_VAR_COUNT '+str(count)+'\nstatic const char expected_bootcmd[]='+json.dumps('bootcmd='+cmd)+';\n')
    source=(P/'nss/src/env_transition.c').read_text().replace('expanded-layout-auto-crc','owner-bound-boot-transition').replace('strcmp(uts.release,"6.18.55")',f'strcmp(uts.release,"{kver}")')
    (out/'env_transition.c').write_text(source)
    subprocess.run([a.cc,'-static','-Os','-s','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',str(out/'env_transition.c'),'-o',str(out/'env-helper')],check=True)
    subprocess.run([a.cc,'-static','-Os','-s','-Wall','-Wextra','-Werror','-Wno-misleading-indentation',str(P/'nss/src/upgrade_guard.c'),'-o',str(out/'mf297d-upgrade-guard')],check=True)
    (out/'kexec').write_bytes(a.kexec.read_bytes())
    state={'env_before':sha(raw),'env_after':sha(new+raw[262144:]),'volumes':volumes,'rootfs_and_kernel_written':False,'boot_schema':'fit-v1'}
    (out/'owner-plan.private.json').write_text(json.dumps(state,indent=2)+'\n')
    script='''#!/bin/sh
set -eu
cd /tmp/mf297d-bootstrap
test "$(uname -r)" = @KVER@
grep -q mf297d.storage_expand=1 /proc/cmdline
test "$(cat /sys/class/mtd/mtd21/name)" = maintenance_storage
test "$(cat /sys/class/mtd/mtd21/flags)" = 0x400
test "$(cat /sys/class/mtd/mtd10/flags)" = 0x400
! grep -q ' ubifs ' /proc/mounts
test ! -e /sys/class/ubi/ubi0/mtd_num
sha256sum -c SHA256SUMS
sha256sum -c prefix.before.sha256
touch /tmp/mf297d-source-keep
./env-helper --selftest
./env-helper --check
ubiattach /dev/ubi_ctrl -m 21 -d 0
sha256sum -c volumes.before.sha256
ubidetach /dev/ubi_ctrl -d 0
./env-helper --install
test "$(sha256sum /dev/mtd10ro | cut -d' ' -f1)" = '@ENV_AFTER@'
./mf297d-upgrade-guard --check-env /dev/mtd10ro
grep -v '/dev/mtd10ro$' prefix.before.sha256 | sha256sum -c -
ubiattach /dev/ubi_ctrl -m 21 -d 0
sha256sum -c volumes.before.sha256
ubidetach /dev/ubi_ctrl -d 0
sync
echo 'MF297D FIT boot migration verified; all UBI volumes and RESET recovery unchanged.'
reboot
'''.replace('@ENV_AFTER@',state['env_after']).replace('@KVER@',kver)
    (out/'apply-from-ram.sh').write_text(script);subprocess.run(['sh','-n',str(out/'apply-from-ram.sh')],check=True)
    (out/'volumes.before.sha256').write_text(''.join(h+'  /dev/ubi0_'+i+'\n' for i,h in volumes.items()))
    names=['env-helper','mf297d-upgrade-guard','prefix.before.sha256','volumes.before.sha256','apply-from-ram.sh']
    (out/'SHA256SUMS').write_text(''.join(sha((out/n).read_bytes())+'  '+n+'\n' for n in names))
    names=['Image','maintenance.dtb','bootargs.txt','kexec']
    (out/'BOOT-SHA256SUMS').write_text(''.join(sha((out/n).read_bytes())+'  '+n+'\n' for n in names))
    print('Prepared private one-time migration:',out,'\nNo device writes performed. Keep owner files private.')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--router',default='root@192.168.1.1');p.add_argument('--out',type=Path,required=True);p.add_argument('--cc',default='aarch64-linux-gnu-gcc');p.add_argument('--kexec',type=Path,required=True);a=p.parse_args();prepare(a)
