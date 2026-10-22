# Creative, voice and integration tooling: what is actually available (checked 2026-10-22)

## Discovery results (this cloud session)
| Wanted | Found | Verdict |
|---|---|---|
| Runway (generative image/video) | No tool or connector in the session. The connector registry's "Runway" entry is **runway.team**, a mobile-app release-management product, NOT the generative-video service. Not installed. | NOT AVAILABLE. Do not connect the wrong product. |
| Wispr Flow (dictation) | Registry entry "Wispr Flow" exposes meetings, notes, tasks and calendar context (tools such as get_meeting, add_task), not a dictation API. Not installed, not connected. | Not needed for dictation; see workflow below. |
| Text-to-speech for narration | Registry lists ElevenLabs (voice-agent platform) and Speko (can narrate text, transcribe, phone calls). Neither installed or connected. | Candidates only; need your authorization and a licence check. |
| Connected connectors | `ListConnectors` for runway/wispr/voice/video/speech/audio returned none. | Nothing connected. |
| Image/PDF/document tools | Adobe and Figma connectors exist in the session (not used; no authorization requested). | Optional. |
| Local rendering | Headless Chromium and Pillow are available. | Used for the procedural concept art. |

No account was connected, no credit was spent, no external generation was run, and nothing was uploaded.

## What was done instead
Original concept art is drawn by code (`visuals/tools/concept_art.py`) and validated by `visuals/tools/validate_assets.py`. It is a real, repeatable pipeline but it is vector illustration, not photoreal generation. It is honestly labelled as a concept visualization.

## Practical supported workflows (need your action)
1. **Runway or another generator (your account).** You run the prompts from the creative briefs in Runway's own web app or API and approve any credits. Save outputs under `visuals/external/<tool>/<date>-<slug>/original/` (untouched originals) and put an `asset.json` next to each using `visuals/external/PROVENANCE-TEMPLATE.json` (tool, model/version, exact prompt, seed if any, date, plan/licence terms, who approved). Website derivatives go in a separate `web/` folder. Claude can then run the validator, review and optimize. Nothing is published without your approval. No generated image is described as a photograph of a real product.
2. **Wispr Flow as dictation.** Treat it as ordinary speech-to-text running on your own computer (its own product description; not verified in this session): speak into the terminal or a text file, then use the explanation checker (`lab/learning/explain.py`). It does not provide narration.
3. **Narration for the brand film.** Choose a licensed synthetic voice from a provider whose terms allow commercial use (ElevenLabs or Speko are the options the registry showed; verify terms yourself). No cloning or imitation of your or anyone's voice without written consent.

## Voice-driven engineering practice (built)
Voice explanation -> transcription (your tool) -> `python -m learning.explain check <topic> transcript.txt` (concept-coverage report and follow-up questions; topics: rag_pipeline, tool_governance, idempotent_retries) -> discussion of accuracy with Claude -> independent coding challenge. The tool never assigns a skill level; mastery is only recorded from work you do unaided.

## Authorization needed before any of this goes further
Connecting any generation or voice account; spending credits; installing any connector. Say which, and Claude will request only that.
