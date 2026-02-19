import struct
from pathlib import Path
import json

def extract_credits_data(winit_path: str):
    """
    Extracts all credits-related display data from WINIT.OVR, including
    splash frames and the main animation table.
    """
    data = Path(winit_path).read_bytes()

    def get_val_at(pos):
        """Extracts 16-bit value from a 'MOV AX, imm16' instruction (B8 LL HH)."""
        return struct.unpack("<H", data[pos+1:pos+3])[0]

    def find_draw_call(call_offset):
        """
        Parses a draw call pattern:
        push Y (B8 YY 00 50)
        push X (B8 XX 00 50)
        push Frame (B8 FF 00 50)
        call 0x97C (E8 .. ..)
        """
        # Search backward from the call to find the 3 pushes
        # Patterns is roughly 12 bytes of pushes before the call
        p3 = call_offset - 4  # Frame push
        p2 = call_offset - 8  # X push
        p1 = call_offset - 12 # Y push
        
        return {
            "frame_idx": get_val_at(p3),
            "x_coord":   get_val_at(p2),
            "y_coord":   get_val_at(p1)
        }

    # 1. Extract Splash Frames (Calls to 0x97C)
    # Offsets determined from disassembly
    splash_calls = [0x4F8, 0x507, 0xAF9, 0xB0B]
    splashes = [find_draw_call(addr) for addr in splash_calls]

    # 2. Extract Main Animation Table (MOV [BP-offset], imm16)
    def get_table_val(bp_offset):
        target_byte = bp_offset & 0xFF
        pattern = b'\xC7\x46' + bytes([target_byte])
        pos = data.find(pattern, 0xBA0, 0xD00)
        return struct.unpack("<H", data[pos+3:pos+5])[0] if pos != -1 else None

    columns = {
        "frame_idx": -0x1C,
        "x_coord":   -0x30,
        "y_coord":   -0x44,
        "flag":      -0x58,
        "delay":     -0x6C
    }

    scroll_steps = []
    for i in range(9):
        step = {"step": i + 1}
        for name, start_offset in columns.items():
            step[name] = get_table_val(start_offset + (i * 2))
        scroll_steps.append(step)

    return {
        "intro_splash": splashes[:2],      # Frames 10, 11
        "credits_splash": splashes[2:],    # Frames 13, 9
        "main_scroll": scroll_steps        # The 9-step table
    }

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "gamedata/WINIT.OVR"
    
    if not Path(path).exists():
        print(f"Error: {path} not found.")
        sys.exit(1)
        
    all_data = extract_credits_data(path)
    
    print("=== Intro Splash Sequence ===")
    for i, s in enumerate(all_data["intro_splash"]):
        print(f"Splash {i+1}: Frame {s['frame_idx']:<2} at ({s['x_coord']}, {s['y_coord']})")

    print("\n=== Credits Startup Sequence ===")
    for i, s in enumerate(all_data["credits_splash"]):
        print(f"Startup {i+1}: Frame {s['frame_idx']:<2} at ({s['x_coord']}, {s['y_coord']})")

    print("\n=== Main Scroll Animation Table ===")
    print(f"{'Step':<5} | {'Frame':<6} | {'X':<4} | {'Y':<4} | {'Delay':<6}")
    print("-" * 40)
    for s in all_data["main_scroll"]:
        print(f"{s['step']:<5} | {s['frame_idx']:<6} | {s['x_coord']:<4} | {s['y_coord']:<4} | {s['delay']:<6}")
    
    # Save to JSON
    output_json = Path("output/credits_animation.json")
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w") as f:
        json.dump(all_data, f, indent=2)
    print(f"\nAll data exported to {output_json}")
