"""Entry point for the Video Captioning Studio frontend.

Run with:
    pip install -r requirements.txt
    streamlit run main.py

The UI lives in ``components/app.py``; this file just launches it.
"""

from components.app import main

if __name__ == "__main__":
    main()
