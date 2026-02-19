import struct
import sys

def analyze_mz(filename):
    with open(filename, 'rb') as f:
        data = f.read(64)
    
    # MZ header is 28 bytes usually
    # e_magic: 2s
    # e_lastn: H
    # e_cp: H
    # e_crlc: H
    # e_cparhdr: H
    # e_minalloc: H
    # e_maxalloc: H
    # e_ss: H
    # e_sp: H
    # e_csum: H
    # e_ip: H
    # e_cs: H
    # e_lfarlc: H
    # e_ovno: H
    
    header = struct.unpack('<2s13H', data[:28])
    magic, lastn, cp, crlc, cparhdr, minalloc, maxalloc, ss, sp, csum, ip, cs, lfarlc, ovno = header
    
    if magic != b'MZ':
        print("Not an MZ file")
        return
    
    print(f"MZ Header for {filename}:")
    print(f"  magic: {magic.decode()}")
    print(f"  lastn: {lastn:04x}")
    print(f"  cp (pages): {cp:04x} (total {cp*512} bytes, or {(cp-1)*512+lastn} bytes)")
    print(f"  crlc: {crlc:04x}")
    print(f"  cparhdr (para): {cparhdr:04x} (offset {cparhdr*16:04x})")
    print(f"  minalloc: {minalloc:04x}")
    print(f"  maxalloc: {maxalloc:04x}")
    print(f"  ss: {ss:04x}")
    print(f"  sp: {sp:04x}")
    print(f"  ip: {ip:04x}")
    print(f"  cs: {cs:04x}")
    print(f"  lfarlc: {lfarlc:04x}")
    print(f"  ovno: {ovno:04x}")

if __name__ == "__main__":
    analyze_mz(sys.argv[1])
