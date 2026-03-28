import subprocess
import os

# Your icon string
ICON_SVG = r"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" fill="#111"/><path d="M472.5 149.4L85.9 17.1c-11-3.8-22.8 1.7-27.1 12.4-1.9 4.7-1.7 10 .6 14.5l86 172.1 12.9 25.9-12.9 25.9-86 172.1c-2.3 4.5-2.5 9.8-.6 14.5 4.3 10.7 16.1 16.2 27.1 12.4l386.6-132.3c10-3.4 16.6-12.9 16.5-23.6-.1-10.8-6.8-20.2-16.9-23.6zM165.9 256l-59.4-118.7L392.4 256 106.5 374.7 165.9 256z" fill="#eab308"/></svg>"""

def create_png(size, filename):
    print(f"--- Generating {filename} ({size}x{size}) ---")
    
    # 1. Save the temp SVG
    with open("temp.svg", "w") as f:
        f.write(ICON_SVG)
    
    # 2. Convert using ffmpeg
    try:
        # We assume ffmpeg is installed via 'pkg install ffmpeg'
        subprocess.run([
            "ffmpeg", 
            "-y",               # Overwrite output file without asking
            "-i", "temp.svg",   # Input file
            "-vf", f"scale={size}:{size}", # Scale filter
            filename            # Output file
        ], check=True)
        print(f"SUCCESS: {filename} created.")
        
    except subprocess.CalledProcessError as e:
        print(f"ERROR: Failed to create {filename}. Is ffmpeg installed?")
    
    # 3. Clean up
    if os.path.exists("temp.svg"):
        os.remove("temp.svg")

if __name__ == "__main__":
    # Generate the 192 icon
    create_png(192, "icon-192.png")
    
    # Generate the 512 icon
    create_png(512, "icon-512.png")
