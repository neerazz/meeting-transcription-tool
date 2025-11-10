from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import List, Optional, Dict, Any

from .audio_processor import ms_to_hhmmss, ms_to_srt_timestamp

try:
	from docx import Document  # type: ignore
	has_docx = True
except Exception:
	has_docx = False


@dataclass
class TranscriptSegment:
	start_ms: int
	end_ms: int
	text: str
	speaker: str = "Speaker 1"


def ensure_dir(path: str) -> None:
	if not os.path.exists(path):
		os.makedirs(path, exist_ok=True)


def export_txt(segments: List[TranscriptSegment], out_dir: str, base_name: str) -> str:
	ensure_dir(out_dir)
	out_path = os.path.join(out_dir, f"{base_name}.txt")
	with open(out_path, "w", encoding="utf-8") as f:
		for seg in segments:
			start = ms_to_hhmmss(seg.start_ms)
			end = ms_to_hhmmss(seg.end_ms)
			f.write(f"[{start} - {end}] {seg.speaker}: {seg.text}\n")
	return out_path


def export_json(segments: List[TranscriptSegment], out_dir: str, base_name: str, metadata: Optional[Dict[str, Any]] = None) -> str:
	ensure_dir(out_dir)
	out_path = os.path.join(out_dir, f"{base_name}.json")
	payload = {
		"metadata": metadata or {},
		"segments": [
			{
				"start_ms": s.start_ms,
				"end_ms": s.end_ms,
				"start": ms_to_hhmmss(s.start_ms),
				"end": ms_to_hhmmss(s.end_ms),
				"speaker": s.speaker,
				"text": s.text,
			}
			for s in segments
		],
	}
	with open(out_path, "w", encoding="utf-8") as f:
		json.dump(payload, f, ensure_ascii=False, indent=2)
	return out_path


def export_srt(segments: List[TranscriptSegment], out_dir: str, base_name: str) -> str:
	ensure_dir(out_dir)
	out_path = os.path.join(out_dir, f"{base_name}.srt")
	with open(out_path, "w", encoding="utf-8") as f:
		for idx, seg in enumerate(segments, start=1):
			start = ms_to_srt_timestamp(seg.start_ms)
			end = ms_to_srt_timestamp(seg.end_ms)
			text = f"{seg.speaker}: {seg.text}".strip()
			f.write(f"{idx}\n{start} --> {end}\n{text}\n\n")
	return out_path


def export_docx(segments: List[TranscriptSegment], out_dir: str, base_name: str) -> str:
	if not has_docx:
		raise RuntimeError("python-docx is not installed. Please install 'python-docx' to export DOCX.")
	ensure_dir(out_dir)
	out_path = os.path.join(out_dir, f"{base_name}.docx")
	doc = Document()
	doc.add_heading("Meeting Transcript", level=1)
	for seg in segments:
		start = ms_to_hhmmss(seg.start_ms)
		end = ms_to_hhmmss(seg.end_ms)
		doc.add_paragraph(f"[{start} - {end}] {seg.speaker}: {seg.text}")
	doc.save(out_path)
	return out_path


