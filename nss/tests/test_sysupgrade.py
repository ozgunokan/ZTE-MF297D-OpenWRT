#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
"""Offline safety tests against a real native FIT and squashfs. No device access."""
from pathlib import Path
import argparse,copy,hashlib,json,re,struct,subprocess,sys,tempfile,zlib
P=Path(__file__).resolve().parents[2];sys.path.insert(0,str(P/'tools'))
from inspect_fit import fdt,inspect
from fdt_codec import encode
from upgrade_boot import BOOTARGS,MAIN_BOOT,migrate

def main(a):
    checks=[]
    with tempfile.TemporaryDirectory(prefix='mf297d-upgrade-test-') as temp:
        t=Path(temp)
        def run(name,args,ok=True):
            r=subprocess.run([str(a.guard),*map(str,args)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            assert (r.returncode==0)==ok,(name,r.stdout,r.stderr);checks.append(name)
        run('valid-native-fit',['--check-fit',a.kernel])
        original=a.kernel.read_bytes();fit=fdt(original);dt_original=fit['/images/fdt-1']['data']
        def changed_dt(name,change):
            tree=copy.deepcopy(fit);dt=fdt(dt_original);change(dt);tree['/images/fdt-1']['data']=encode(dt,dt_original)
            data=tree['/images/fdt-1']['data']
            tree['/images/fdt-1/hash-1']['value']=struct.pack('>I',zlib.crc32(data))
            tree['/images/fdt-1/hash-2']['value']=hashlib.sha1(data).digest()
            p=t/name;p.write_bytes(encode(tree,original));return p
        protected=next(n for n,v in fdt(dt_original).items() if v.get('label')==b'0:appsblenv\0')
        p=changed_dt('unsafe.dtb-fit',lambda dt:dt[protected].pop('read-only'));run('reject-writable-env-dts',['--check-fit',p],False)
        storage=next(n for n,v in fdt(dt_original).items() if v.get('label')==b'rootfs\0')
        p=changed_dt('wrong-layout.fit',lambda dt:dt[storage].update(reg=bytes.fromhex('02cc000003a00000')));run('reject-wrong-nand-span',['--check-fit',p],False)
        p=changed_dt('ram.fit',lambda dt:dt['/chosen'].update(bootargs=b'root=/dev/ram0\0'));run('reject-ram-profile',['--check-fit',p],False)
        broken=copy.deepcopy(fit);data=bytearray(broken['/images/kernel-1']['data']);data[len(data)//2]^=1;broken['/images/kernel-1']['data']=bytes(data)
        p=t/'bad-hash.fit';p.write_bytes(encode(broken,original));run('reject-corrupted-kernel',['--check-fit',p],False)
        p=t/'truncated.fit';p.write_bytes(original[:100]);run('reject-truncated-fdt',['--check-fit',p],False)
        mac=t/'mac';mac.write_bytes(bytes.fromhex('020102030405'));out=t/'owned.fit'
        run('personalise-regular-output',['--personalise',a.kernel,out,mac]);new=fdt(out.read_bytes())
        assert new['/images/kernel-1']['data']==fit['/images/kernel-1']['data']
        assert all(h['valid'] for image in inspect(out)['images'].values() for h in image['hashes'])
        macs=[(n,v['local-mac-address']) for n,v in fdt(new['/images/fdt-1']['data']).items() if 'local-mac-address' in v]
        assert len(macs)==2
        base=int.from_bytes(mac.read_bytes(),'big')
        assert all(value==(base-(0x10000 if n.endswith('/ethernet-port@5') else 0x20000)).to_bytes(6,'big') for n,value in macs)
        run('refuse-output-overwrite',['--personalise',a.kernel,out,mac],False)
        root=a.rootfs.read_bytes();head=t/'root.header';head.write_bytes(root[:4096]);size=(len(root)+4095)//4096*4096
        run('valid-aligned-squashfs',['--check-root',head,size]);run('reject-unaligned-root',['--check-root',head,size-1],False)
        bad=bytearray(root[:4096]);struct.pack_into('<Q',bad,40,size+4096);head.write_bytes(bad);run('reject-truncated-squashfs',['--check-root',head,size],False)
        recovery="if ubi read 0x44000000 owrt_recovery; then if crc32 0x44000000 0x1234 0x43000000; then if itest.l *0x43000000 == 0x12345678; then if setenv bootargs 'root=/dev/ram0'; then bootm 0x44000000#config@mp03.3; fi; fi; fi; fi;"
        oldmain="if ubi read 0x44000000 owrt_kernel; then if crc32 0x44000000 0x4567 0x43000000; then if itest.l *0x43000000 == 0xabcdef01; then if setenv bootargs '"+BOOTARGS+"'; then bootm 0x44000000#config@mp03.3; fi; fi; fi; fi;"
        before="sleep 2; if setexpr.l mf297d_button *0x01020004 '&' 1; then if itest.l ${mf297d_button} == 0; then "+recovery+" fi; fi; "+oldmain+' '+recovery+' reset'
        entries=[b'bootdelay=2',b'bootcmd='+before.encode(),b'owner_fixture=unchanged'];body=(b'\0'.join(entries)+b'\0\0').ljust(262140,b'\0')
        raw=struct.pack('<I',zlib.crc32(body))+body+b'\xff'*262144
        old,new,cmd,count=migrate(raw);assert count==4 and old==raw[:262144]
        assert cmd.replace(MAIN_BOOT,oldmain)==before
        p=t/'env.bin';p.write_bytes(new+b'\xff'*262144);run('valid-migrated-env',['--check-env',p])
        p.write_bytes(raw);run('reject-unmigrated-env',['--check-env',p],False)
        try:migrate(new+b'\xff'*262144)
        except AssertionError:checks.append('reject-repeated-migration')
        else:raise AssertionError('Repeated migration accepted')
        # Stock first-install ENV ends with a trailing bootipq fallback after recovery.
        before_stock="sleep 2; if setexpr.l mf297d_button *0x01020004 '&' 1; then if itest.l ${mf297d_button} == 0; then "+recovery+" fi; fi; "+oldmain+' '+recovery+" setenv mtdids ''; setenv mtdparts ''; setenv bootargs 'console=ttyMSM0,115200n8'; bootipq"
        s_entries=[b'bootdelay=2',b'bootcmd='+before_stock.encode(),b'owner_fixture=unchanged'];s_body=(b'\0'.join(s_entries)+b'\0\0').ljust(262140,b'\0')
        s_raw=struct.pack('<I',zlib.crc32(s_body))+s_body+b'\xff'*262144
        _,s_new,s_cmd,_=migrate(s_raw);assert s_cmd.replace(MAIN_BOOT,oldmain)==before_stock
        p.write_bytes(s_new+b'\xff'*262144);run('valid-migrated-stock-env',['--check-env',p])
        bad_bootipq="sleep 2; bootipq; if setexpr.l mf297d_button *0x01020004 '&' 1; then if itest.l ${mf297d_button} == 0; then "+recovery+" fi; fi; "+oldmain+' '+recovery
        b_entries=[b'bootdelay=2',b'bootcmd='+bad_bootipq.encode()];b_body=(b'\0'.join(b_entries)+b'\0\0').ljust(262140,b'\0')
        try:migrate(struct.pack('<I',zlib.crc32(b_body))+b_body+b'\xff'*262144)
        except AssertionError:checks.append('reject-leading-bootipq')
        else:raise AssertionError('Leading bootipq accepted')
        simulation=r'''
sleep() { :; }
setexpr.l() { mf297d_button=$TEST_BUTTON; }
itest.l() { if [[ $1 == '*0x43000000' ]]; then return 0; else [[ $1 == "$3" ]]; fi; }
setenv() { printf -v "$1" '%s' "${2-}"; }
ubi() { if [[ $1 == read ]]; then last=$3; [[ $last == owrt_kernel && $MODE == missing ]] && return 1; fi; return 0; }
crc32() { [[ $last == owrt_recovery ]]; }
bootm() { if [[ $last == owrt_kernel ]]; then [[ $verify == yes ]] || exit 96; [[ $MODE == corrupt ]] && return 1; fi; echo "$last"; exit 0; }
reset() { exit 97; }
'''
        for button,mode,expected in [('1','valid','owrt_kernel'),('0','valid','owrt_recovery'),('1','corrupt','owrt_recovery'),('1','missing','owrt_recovery')]:
            r=subprocess.run(['bash','-c',f'TEST_BUTTON={button}; MODE={mode};\n'+simulation+'\n'+cmd],capture_output=True,text=True)
            assert r.returncode==0 and r.stdout.strip()==expected,(button,mode,r.stdout,r.stderr)
            checks.append('boot-flow-'+button+'-'+mode)
    print(json.dumps({'passed':len(checks),'checks':checks,'device_writes':False},indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--guard',type=Path,required=True);p.add_argument('--kernel',type=Path,required=True);p.add_argument('--rootfs',type=Path,required=True);main(p.parse_args())
