# Running on Raspberry Pi 5

Yes! This application runs excellent on a Raspberry Pi 5. The Pi 5's Cortex-A76 processor is more than capable of handling the lightweight "small" Vosk model in real-time.

## Prerequisites

Unlike Windows, the Raspberry Pi requires a few system-level dependencies before you can install the Python libraries.

### 1. Hardware
- **Raspberry Pi 5** (Pi 4 and 3B+ also work).
- **USB Microphone** (The Pi does not have a built-in microphone).
- **Display** (Since this is a GUI app).

### 2. System Dependencies
Open the terminal and run:

```bash
sudo apt update
sudo apt install python3-tk libportaudio2 libatlas-base-dev
```
*   `python3-tk`: Required for the Tkinter GUI.
*   `libportaudio2`: Required for sounddevice.
*   `libatlas-base-dev`: Required for NumPy optimization (often pre-installed, but good to ensure).

### 3. Virtual Environment (Recommended)
On modern Raspberry Pi OS (Bookworm), you should use a virtual environment to avoid conflicts with system packages.

```bash
# Create the virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate
```

### 4. Install Application Dependencies
With the virtual environment activated:

```bash
pip install -r requirements.txt
```
*Note: This will automatically download the correct ARM64 versions of Vosk and NumPy.*

## Running the Application

```bash
python main.py
```

## Performance Tips
- **Overheating**: Real-time speech recognition can keep a CPU core active. Ensure your Pi 5 has the active cooler or a good heatsink case.
- **Audio Input**: If the app listens but "hears" nothing, you may need to select the correct input device.
    - Run `python -m sounddevice` to list devices.
    - Additional configuration in `main.py` might be needed to select a specific device index if the default isn't correct.
