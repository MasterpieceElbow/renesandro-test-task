# Media Processing REST API

## Overview

This project implements a **REST API service** for generating media combinations. The service receives JSON input containing **video blocks**, **audio blocks**, and **text-to-speech instructions**, then generates **all possible combinations of videos** with randomized audio and TTS overlays. The final media outputs are stored in **Google Drive**

---

## Features

- **POST `/process_media`** endpoint:
  - Accepts JSON payload with video blocks, audio blocks, and text-to-speech instructions
  - Queues tasks asynchronously; does not block new requests while processing
  - Logs the execution time of each process, at the end logs the total time and the number of successful/unsuccessful executions of all processes
- Generates **all possible combinations of videos** across blocks
- Randomly applies:
  - Background audio (looped and volume normalized)
  - Text-to-speech voice overlays (using [ElevenLabs.io](https://elevenlabs.io/))
- Saves generated `.mp4` files in a folder named after `task_name` in GCS/Google Drive
- Structured logging for observability
- Validation of input using **Pydantic**
- Metrics include:
  - Time to generate each video
  - Total task execution time

---

## Prerequisites and Installation

### Prerequisites

- Docker
- Google Drive Client credentials
- ElevenLabs API key (for text-to-speech)

### Installation

1. Clone repository: `git clone https://github.com/MasterpieceElbow/renesandro-test-task.git`
2. Install virual environment (Python3.11 should be already installed on your machine): `python3.11 -m venv venv`
3. Activate virtual environment (for MacOS/Linux): `source venv/bin/activate`
4. Install requirements: `pip3.11 install -r requirements.txt`
5. Copy `.env.example` into `.env` and fill it with your parameters
6. Build docker image: `docker-compose build`
7. Run docker-compose services: `docker-compose up`
8. Access Swagger: `http://127.0.0.1:8000/docs`

## API Usage

Endpoint: POST /process_media

Request Body Example:

```JSON
{
  "task_name": "test_task_2blocks_with_audio",
  "video_blocks": {
    "block1": ["https://storage.googleapis.com/video1.mp4", "https://storage.googleapis.com/video2.mp4"],
    "block2": ["https://storage.googleapis.com/video3.mp4", "https://storage.googleapis.com/video4.mp4"]
  },
  "audio_blocks": {
    "audio1": ["https://storage.googleapis.com/audio1.mp3", "https://storage.googleapis.com/audio2.mp3"]
  },
  "text_to_speach": [
    {"text": "Hello world", "voice": "Sarah"}
  ]
}
```

Behavior:

- Generates all combinations of videos across blocks

- Randomly adds background audio and TTS overlay

- Create Celery task for each video combination and execute them across all Celery workers

- Saves results in task_name/ folder in Google Drive

## Tools & Technologies

Python 3.11

FastAPI

Celery + Redis (for task queue)

Moviepy (video/audio processing)

Pydantic (data validation)

Docker & Docker Compose

Google Drive API

ElevenLabs API (text-to-speech)

Logging & metrics (structured logging)

## Lessons Learned / New Tools

ElevenLabs TTS API – integrated programmatically for dynamic voice overlays

Moviepy Python integration – automated complex video/audio processing pipelines

Async Task Queues (Celery) – learned best practices for queueing and monitoring long-running tasks

Docker-compose orchestration – configured multi-container architecture for API + queue + dependencies

## Bottlenecks

- The number of videos processed in parallel depends on the number of celery workers. Celery workers can be scaled horizontally to process multiple tasks concurrently
- Video download & encoding (Moviepy CPU intensive). Optimization: Parallel downloading, caching, or using faster storage
- TTS generation (network latency with ElevenLabs API). Optimization: Batch requests where possible

## Future Improvements

- Implement caching for downloaded video/audio to reduce redundant downloads
- implement caching for TTS from ElevenLabs since some voiceovers are used multiple times across video combinations. This will reduce token usage
- Add retry mechanism for failed TTS or media processing
- Expose task status endpoint for progress tracking
- Add more metrics to monitor queue performance and worker utilization
- Сurrently this only works for videos of the same format and resolution. Add processing of different formats: .mp4 + .mov and resolutions
- Consider another tools for video processing. Probably, plain FFmpeg may give better performance.

## Author

Oleksii Proshchenko - Python Engineer
