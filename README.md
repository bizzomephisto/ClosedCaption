# ClosedCaption
Lightweight CC project in python
Late Night Bizzo Barnicles 

# Local Closed Captions

A real-time, offline closed captioning application for Windows. This tool uses [Vosk](https://alphacephei.com/vosk/) for accurate, locally-processed speech recognition, making it perfect for privacy-conscious users or situations without internet access.

## Features

*   **Offline Speech Recognition**: Powered by the lightweight Vosk model, no data is sent to the cloud.
*   **Real-time Captioning**: Displays speech as text with low latency.
*   **Customizable UI**:
    *   Adjust font family, size, and text color.
    *   Toggle between "Floating", "Dock Top", and "Dock Bottom" modes.
    *   Full-screen mode available.
*   **Overlay Ready**: Designed to sit on top of other windows (Always on Top).
*   **Automatic Setup**: Automatically checks for and downloads the required language model on first run.

## Installation

1.  **Clone or Download** the repository.
2.  **Install Python 3.x** if not already installed.
3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *Note: On Windows, you might need to install [Microsoft C++ Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) if you encounter issues installing `vosk` or `numpy`.*

## Usage

1.  Run the application:
    ```bash
    python main.py
    ```
2.  **First Run**: The application will automatically download the English language model (`vosk-model-small-en-us-0.15`) into the `model/` directory. This may take a moment depending on your internet connection.
3.  **Controls**:
    *   Click the **⚙ Settings** button to configure the appearance and position.
    *   The window will stay on top of other applications, making it ideal for watching videos or meetings.

## Requirements

*   Python 3.7+
*   `vosk`
*   `sounddevice`
*   `numpy`
*   `tkinter` (usually included with Python)




