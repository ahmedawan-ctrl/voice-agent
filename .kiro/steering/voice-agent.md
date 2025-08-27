📌 Requirements Specification

Always-On Server:

Resolve idle timeout.

Server must remain up 24/7 and only shut down manually.

Behave like a production service, always expecting text or audio input from multiple clients.

Pipelines:

Maintain two separate pipelines:

Text → Audio (LLM → TTS → Moshika voice)

Audio → Audio (STT → LLM → TTS → Moshika voice)

System should auto-detect input type (text vs. audio) and select the correct pipeline.

Service Validation:

STT Service: Must correctly process user mic audio → text for LLM.

Text Input: If text input is given, bypass STT and directly send text to LLM.

TTS Service: Must reliably convert LLM text output → audio response.

Moshika Voice: Final audio output should be spoken in the configured voice.

⚠️ Note: Text → Audio response was already working correctly before — do not break or revalidate unnecessarily.

🔗 Major Integrations

STT Integration: Enable mic input → text.

Moshika Voice: Configure and serve real audio responses.

Audio Playback Testing: Ensure generated speech files are playable.

Real-Time Conversation: Build full-duplex interaction (parallel listen + respond).

Performance Optimization: Fine-tune streaming to minimize latency.

🛠 Operational Guidelines

Always use tmux to manage sessions.

For documentation and examples, refer to:

context7 mcp server → Latest docs on Pipecat pipeline.

Repos inside voice-agent/:

pipecat/ → Pipeline examples.

delayed-streams-modeling/ → Kyutai STT & TTS models.

moshi/ → Server configs + full-duplex speech-text foundation model.

✅ Key Reminders

Server must stay always-on unless manually stopped.

Pipelines must auto-switch depending on text vs. audio input.

Do separate health checks for STT and TTS.

Never regress already working functionality (e.g., text → audio).