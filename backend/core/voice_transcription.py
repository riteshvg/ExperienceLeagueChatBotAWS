"""
Voice-input transcription for Interviewer Mode — batch (not realtime) Amazon
Transcribe jobs. The recorded audio has to pass through S3 for Transcribe's
batch API to read it, but both the input audio object and the output
transcript object are deleted immediately after the transcript is read back —
nothing is retained beyond the lifetime of a single request.
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid

import boto3

from config.settings import get_settings

_S3_PREFIX = "interview-voice-tmp"
_POLL_INTERVAL_SECONDS = 2
_MAX_POLL_SECONDS = 90
_SUPPORTED_FORMATS = {"mp3", "mp4", "wav", "flac", "amr", "ogg", "webm"}


class TranscriptionError(Exception):
    pass


def _clients():
    settings = get_settings()
    region = settings.aws_default_region or "us-east-1"
    s3 = boto3.client("s3", region_name=region)
    transcribe = boto3.client("transcribe", region_name=region)
    return s3, transcribe, settings.aws_s3_bucket


def _media_format(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "webm"
    return ext if ext in _SUPPORTED_FORMATS else "webm"


def _transcribe_sync(audio_bytes: bytes, filename: str) -> str:
    s3, transcribe, bucket = _clients()
    if not bucket:
        raise TranscriptionError("Voice transcription is not configured (missing S3 bucket).")

    job_name = f"interview-voice-{uuid.uuid4().hex}"
    input_key = f"{_S3_PREFIX}/{job_name}-{filename}"
    output_key = f"{_S3_PREFIX}/{job_name}.json"

    s3.put_object(Bucket=bucket, Key=input_key, Body=audio_bytes)
    try:
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={"MediaFileUri": f"s3://{bucket}/{input_key}"},
            MediaFormat=_media_format(filename),
            LanguageCode="en-US",
            OutputBucketName=bucket,
            OutputKey=output_key,
        )

        deadline = time.monotonic() + _MAX_POLL_SECONDS
        while time.monotonic() < deadline:
            resp = transcribe.get_transcription_job(TranscriptionJobName=job_name)
            job = resp["TranscriptionJob"]
            status = job["TranscriptionJobStatus"]

            if status == "COMPLETED":
                obj = s3.get_object(Bucket=bucket, Key=output_key)
                payload = json.loads(obj["Body"].read())
                transcripts = payload.get("results", {}).get("transcripts", [])
                text = transcripts[0]["transcript"] if transcripts else ""
                s3.delete_object(Bucket=bucket, Key=output_key)
                return text.strip()

            if status == "FAILED":
                raise TranscriptionError(job.get("FailureReason", "Transcription job failed."))

            time.sleep(_POLL_INTERVAL_SECONDS)

        raise TranscriptionError("Transcription timed out.")
    finally:
        s3.delete_object(Bucket=bucket, Key=input_key)
        try:
            transcribe.delete_transcription_job(TranscriptionJobName=job_name)
        except Exception:
            pass


async def transcribe_audio(audio_bytes: bytes, filename: str = "answer.webm") -> str:
    return await asyncio.to_thread(_transcribe_sync, audio_bytes, filename)
