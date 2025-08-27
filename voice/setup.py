#!/usr/bin/env python3
"""
Setup script for Voice Agent package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_path = Path(__file__).parent / "README.md"
long_description = readme_path.read_text() if readme_path.exists() else ""

# Read requirements
requirements_path = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_path.exists():
    requirements = requirements_path.read_text().strip().split('\n')
    requirements = [req.strip() for req in requirements if req.strip() and not req.startswith('#')]

setup(
    name="voice-agent",
    version="1.0.0",
    description="Production-ready voice agent built with Pipecat AI framework",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Voice Agent Team",
    author_email="team@voiceagent.ai",
    url="https://github.com/voice-agent/voice-agent",
    packages=find_packages(),
    include_package_data=True,
    install_requires=requirements,
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Multimedia :: Sound/Audio :: Speech",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    entry_points={
        "console_scripts": [
            "voice-agent=voice_agent.cli:cli_main",
        ],
    },
    keywords="voice agent ai speech recognition speech-to-speech llm pipecat",
)