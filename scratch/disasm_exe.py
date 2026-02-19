import capstone
import sys

def disasm(filename, offset, length, mode=capstone.CS_MODE_16):
    md = capstone.Cs(capstone.CS_ARCH_X86, mode)
    with open(filename, 'rb') as f:
        f.seek(offset)
        code = f.read(length)
    
    for i in md.disasm(code, offset):
        print(f"0x{i.address:x}: {i.mnemonic}	{i.op_str}")

if __name__ == "__main__":
    disasm(sys.argv[1], int(sys.argv[2], 16), int(sys.argv[3], 16))
