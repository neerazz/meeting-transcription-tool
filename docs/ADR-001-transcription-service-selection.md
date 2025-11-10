# ADR-001: Speech-to-Text Service Selection for Meeting Transcription Tool

## Status
Proposed

## Context
We need to select a speech-to-text (STT) service for our meeting transcription tool that provides:
- High transcription accuracy
- Speaker diarization capabilities
- Precise timestamp generation
- Cost-effectiveness
- Good API documentation and ease of integration
- Support for various audio formats and quality levels

## Decision Drivers
1. **Accuracy**: Word Error Rate (WER) and accuracy in noisy environments
2. **Speaker Diarization**: Quality of speaker identification and labeling
3. **Timestamp Precision**: Ability to generate precise word-level or phrase-level timestamps
4. **Cost**: Pricing per hour/minute of audio
5. **Integration Complexity**: API ease of use and documentation quality
6. **Processing Speed**: Real-time vs batch processing capabilities
7. **Language Support**: Multi-language capabilities (future consideration)

## Options Considered

### Option 1: AssemblyAI Universal-2
**Pros:**
- Industry-leading speaker diarization (2.9% speaker count error rate)
- 30% better performance in noisy environments
- Handles speaker segments as short as 250ms with 43% improved accuracy
- Word Accuracy Rate: 93.3% (WER: 6.7%)
- Speaker diarization included in base price ($0.15/hour)
- Excellent API documentation
- Support for 99 languages
- Built-in sentiment analysis and PII detection (add-on features)
- Good timestamp accuracy

**Cons:**
- Mid-range pricing at $0.15/hour ($0.0025/min)
- Advanced features cost extra (sentiment: $0.02/hour, PII: $0.08/hour)
- Not the fastest processing speed

**Total Cost for 100 hours/month**: $15/month (base transcription + diarization)

### Option 2: Deepgram Nova-3
**Pros:**
- Fastest STT model in the world
- 54.3% reduction in WER for streaming, 47.4% for batch
- Very competitive batch pricing: $0.0043/min ($0.26/hour)
- Per-second billing (more cost-effective for short audio files)
- Best for real-time streaming applications
- Low latency

**Cons:**
- Real-time streaming costs 79% more ($0.0077/min vs $0.0043/min)
- Speaker diarization is an add-on cost
- Word Accuracy Rate: 90.76% (WER: 9.24%) - lower than AssemblyAI
- Proper Nouns Error: 21.14% (vs 13.87% for AssemblyAI)

**Total Cost for 100 hours/month**: 
- Batch: $25.80/month
- Real-time: $46.20/month

### Option 3: OpenAI Whisper API
**Pros:**
- Gold-standard accuracy for clean and noisy speech
- Excellent handling of diverse accents and technical terminology
- Simple API: $0.006/min ($0.36/hour)
- Best raw transcription quality
- Open-source version available for self-hosting
- Multi-language support (680,000 hours of training data)
- Phrase-level timestamps included

**Cons:**
- NO built-in speaker diarization
- Requires separate diarization service (pyannote.audio, etc.)
- Slower processing speed compared to Deepgram
- Limited customization options
- Speaker diarization would require complex integration

**Total Cost for 100 hours/month**: $36/month (transcription only, diarization requires additional solution)

### Option 4: Google Cloud Speech-to-Text
**Pros:**
- Extensive language support
- Specialized telephony models
- Multi-cloud strategy support

**Cons:**
- Very slow processing speed
- Medium accuracy
- High cost
- Complex pricing structure
- Not competitive with modern alternatives

**Not recommended** based on 2025 benchmarks.

### Option 5: Microsoft Azure Speech Services
**Pros:**
- Good for Microsoft ecosystem integration
- Neural voices for TTS

**Cons:**
- Struggles with noisy speech
- Consistently ranks at bottom in benchmarks
- High cost
- Slower processing

**Not recommended** for this use case.

## Comparison Matrix

| Feature | AssemblyAI | Deepgram Nova-3 | OpenAI Whisper | Google Cloud | Azure |
|---------|-----------|----------------|----------------|--------------|-------|
| **WER (Lower is better)** | 6.7% | 9.24% | ~5-7% | ~12% | ~14% |
| **Speaker Diarization** | Excellent (Built-in) | Good (Add-on) | None | Basic | Basic |
| **Timestamp Accuracy** | Excellent | Excellent | Very Good | Good | Good |
| **Cost (per hour)** | $0.15 | $0.26 (batch) | $0.36 | $0.60+ | $0.60+ |
| **Processing Speed** | Medium | Fastest | Slow | Very Slow | Slow |
| **Noisy Audio** | Excellent (+30%) | Good | Excellent | Poor | Poor |
| **API Quality** | Excellent | Excellent | Very Good | Good | Good |
| **Language Support** | 99 languages | Good | Excellent | Best | Good |
| **Integration Complexity** | Low | Low | Low | Medium | Medium |

## Decision

**Selected: AssemblyAI Universal-2**

##Rationale

AssemblyAI provides the best balance of features for our meeting transcription use case:

### Primary Reasons:

1. **Built-in Speaker Diarization**: Industry-leading 2.9% speaker count error rate, which is critical for our MS Word-style output format requiring speaker labels. This is included in the base $0.15/hour price.

2. **Excellent Accuracy in Real-World Conditions**: 30% better performance in noisy environments and 43% improved accuracy on short segments (250ms). Meeting recordings often have background noise, cross-talk, and varying audio quality.

3. **Best Cost-to-Feature Ratio**: At $0.15/hour with speaker diarization included, it's more cost-effective than:
   - Whisper ($0.36/hour) + separate diarization solution (additional cost + complexity)
   - Deepgram ($0.26/hour batch) + diarization add-on

4. **Timestamp Precision**: Provides precise word-level and phrase-level timestamps integrated with speaker labels, perfect for our required output format: `[00:00:00 - 00:00:05] Speaker 1: Text`

5. **Single API Solution**: No need to orchestrate multiple services for transcription + diarization, reducing integration complexity and maintenance overhead.

6. **Excellent Documentation**: Well-documented API with Python SDKs, making development faster and reducing potential for errors.

7. **Future Flexibility**: Additional features like sentiment analysis, PII detection, and summarization available as add-ons if needed.

### Why Not Deepgram?
- Higher WER (9.24% vs 6.7%)
- Speaker diarization is additional cost
- Lower proper noun accuracy (21.14% vs 13.87%)
- Speed advantage not critical for our use case (batch processing is acceptable)

### Why Not Whisper?
- Lack of built-in speaker diarization is a deal-breaker
- Would require integrating pyannote.audio or similar, adding complexity
- Increased development time and maintenance burden
- Total solution cost would be higher when factoring in diarization

## Consequences

### Positive:
- Single vendor for transcription and diarization simplifies architecture
- High accuracy reduces need for manual corrections
- Excellent noise handling works well with real-world meeting recordings
- Easy to implement and test quickly
- Predictable, transparent pricing
- Good documentation reduces development time
- Can easily add advanced features (sentiment, PII) later if needed

### Negative:
- Not the absolute cheapest option per hour
- Not the fastest processing (but acceptable for batch use case)
- Vendor lock-in to AssemblyAI's API
- Need to monitor API rate limits and quotas

### Mitigation Strategies:
- Design abstraction layer for transcription service to allow future switching if needed
- Implement caching for processed audio to avoid redundant API calls
- Monitor usage and costs closely
- Set up error handling and retry logic for API failures
- Keep Whisper as backup option for critical use cases

## Implementation Notes

1. **API Key Management**: Store API keys securely in environment variables
2. **Audio Upload**: Use AssemblyAI's upload endpoint for audio files
3. **Polling**: Implement polling mechanism to check transcription status
4. **Webhook Option**: Consider webhook integration for production for async processing
5. **Error Handling**: Implement comprehensive error handling for API failures
6. **Rate Limiting**: Respect API rate limits (5 concurrent requests on free tier)
7. **Testing**: Use sample meeting audio to validate accuracy and diarization quality

## Sample Code Structure

```python
import requests
import time

class AssemblyAITranscriber:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.assemblyai.com/v2"
        self.headers = {"authorization": api_key}
    
    def upload_file(self, audio_file_path):
        """Upload audio file to AssemblyAI"""
        with open(audio_file_path, 'rb') as f:
            response = requests.post(
                f"{self.base_url}/upload",
                headers=self.headers,
                data=f
            )
        return response.json()['upload_url']
    
    def transcribe(self, audio_url, num_speakers=None):
        """Start transcription with speaker diarization"""
        data = {
            "audio_url": audio_url,
            "speaker_labels": True
        }
        if num_speakers:
            data["speakers_expected"] = num_speakers
        
        response = requests.post(
            f"{self.base_url}/transcript",
            json=data,
            headers=self.headers
        )
        return response.json()['id']
    
    def get_transcript(self, transcript_id):
        """Poll for transcription result"""
        polling_endpoint = f"{self.base_url}/transcript/{transcript_id}"
        
        while True:
            response = requests.get(polling_endpoint, headers=self.headers)
            result = response.json()
            
            if result['status'] == 'completed':
                return result
            elif result['status'] == 'error':
                raise Exception(f"Transcription failed: {result['error']}")
            
            time.sleep(3)
    
    def format_output(self, transcript_result):
        """Format output in MS Word style"""
        output = []
        for utterance in transcript_result['utterances']:
            start_time = self.ms_to_timestamp(utterance['start'])
            end_time = self.ms_to_timestamp(utterance['end'])
            speaker = utterance['speaker']
            text = utterance['text']
            
            output.append(f"[{start_time} - {end_time}] Speaker {speaker}: {text}")
        
        return "\n\n".join(output)
    
    @staticmethod
    def ms_to_timestamp(ms):
        """Convert milliseconds to HH:MM:SS format"""
        seconds = ms // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
```

## Review Date
This decision should be reviewed in 6 months (May 2026) or if:
- AssemblyAI pricing increases significantly
- A new service offers substantially better accuracy or pricing
- Our usage patterns change (e.g., requiring real-time streaming)
- Speaker diarization quality becomes insufficient

## References
- AssemblyAI Pricing: https://www.assemblyai.com/pricing
- 2025 STT Benchmarks: Multiple sources including Deepgram, Voice Writer, AssemblyAI
- Speaker Diarization Comparison: AssemblyAI Blog (2025)
- Deepgram Nova-3 Announcement: April 2025
- OpenAI Whisper Documentation

## Approvers
- Technical Lead: [Pending]
- Product Manager: [Pending]
- Engineering Manager: [Pending]

---

**Document Created**: November 10, 2025  
**Last Updated**: November 10, 2025  
**Author**: Neeraj Kumar Singh B  
**Version**: 1.0
