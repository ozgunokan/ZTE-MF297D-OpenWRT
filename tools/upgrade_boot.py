# SPDX-License-Identifier: GPL-2.0-only
"""One-time V1 fixed-CRC -> V2 FIT-verified main boot migration; no flash I/O."""
import re,struct,zlib

BOOTARGS='console=ttyMSM0,115200n8 root=/dev/ubiblock0_5 rootfstype=squashfs ro rootwait ubi.mtd=21 ubi.block=0,owrt_rootfs clk_ignore_unused maxcpus=1 panic=20 mf297d.permanent=1 mf297d.boot_span=wide coherent_pool=2M mf297d.nss_nand=20261114'
MAIN_BOOT="if ubi read 0x44000000 owrt_kernel; then if setenv verify yes; then if setenv bootargs '"+BOOTARGS+"'; then bootm 0x44000000#config@mp03.3; fi; fi; fi;"
OLD_MAIN=r"if ubi read 0x44000000 owrt_kernel; then if crc32 0x44000000 0x[0-9a-f]+ 0x43000000; then if itest\.l \*0x43000000 == 0x[0-9a-f]+; then if setenv bootargs '([^']*)'; then bootm 0x44000000#config@mp03\.3; fi; fi; fi; fi;"
MARKER=b'mf297d_sysupgrade=fit-v1'

def migrate(raw):
    assert len(raw)==524288 and raw[262144:]==b'\xff'*262144,'unsupported ENV geometry/tail'
    old=raw[:262144];assert struct.unpack_from('<I',old)[0]==zlib.crc32(old[4:]),'ENV CRC mismatch'
    entries=old[4:].split(b'\0\0',1)[0].split(b'\0')
    assert len({e.split(b'=',1)[0] for e in entries})==len(entries),'duplicate ENV variable'
    assert MARKER not in entries,'boot migration already installed'
    commands=[e[8:].decode() for e in entries if e.startswith(b'bootcmd=')];assert len(commands)==1
    cmd=commands[0];matches=list(re.finditer(OLD_MAIN,cmd));assert len(matches)==1,'unrecognised fixed-CRC main boot'
    m=matches[0];assert m[1]==BOOTARGS,'unexpected NAND boot arguments'
    assert "setexpr.l mf297d_button *0x01020004 '&' 1;" in cmd[:m.start()],'RESET selection missing'
    assert 'owrt_recovery' in cmd[:m.start()] and 'owrt_recovery' in cmd[m.end():],'recovery branches missing'
    assert 'bootipq' not in cmd[:m.end()] and 'saveenv' not in cmd
    newcmd=cmd[:m.start()]+MAIN_BOOT+cmd[m.end():]
    # Every RESET and fallback byte remains in its original position relative to main.
    assert newcmd.split(MAIN_BOOT)==[cmd[:m.start()],cmd[m.end():]]
    result=[b'bootcmd='+newcmd.encode() if e.startswith(b'bootcmd=') else e for e in entries]+[MARKER]
    data=b'\0'.join(result)+b'\0\0';assert len(data)<=262140
    data=data.ljust(262140,b'\0');new=struct.pack('<I',zlib.crc32(data))+data
    return old,new,newcmd,len(result)
