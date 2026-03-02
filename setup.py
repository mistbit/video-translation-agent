from setuptools import setup, find_packages

setup(
    name="video-translation-agent",
    version="0.1.0",
    description="A video translation agent with OCR/ASR subtitle extraction and translation",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "paddleocr>=2.7",
        "paddlepaddle>=2.5",
        "faster-whisper>=0.10",
        "moviepy>=1.0.3",
        "opencv-python>=4.8",
        "pyyaml>=6.0",
        "typer>=0.9",
        "zhipuai>=2.0",
    ],
    entry_points={
        "console_scripts": [
            "vta=src.main:app",
        ],
    },
    python_requires=">=3.10",
)
