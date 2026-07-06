"""Backend logic for the Video Captioning Studio.

Video/frame processing and rule-based (mock) caption generation. Kept
separate from the Streamlit UI so it can be tested and reused on its own.

Modules:
    frame_extractor   — pull key frames from a video with OpenCV
    video_utils       — read clip metadata + build an honest video context
    caption_generator — turn that context into four styled captions
    style_rules       — the definitions of the four caption voices
"""
