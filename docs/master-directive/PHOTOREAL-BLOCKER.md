# Photorealistic asset status (2026-10-22)

**Generated and saved: 0 photorealistic images.** None are claimed.

| Tool checked | Result |
|---|---|
| Hugging Face Spaces connector | Search works; invoking Spaces is disabled in this session (`gradio=none`). |
| Figma `generate_image` | Needs a Figma file and consumes paid Figma AI credits — not authorized. |
| Figma Weave | Account not linked. |
| Adobe MCP | Editing tools only (no text-to-image product photography). |
| Runway (runwayml.com) | No connector or credentials in this session. |

## Authorization needed from Ritesh (one of)
- Approve Figma AI image credits on a named Figma file, with a spend cap; or
- Connect a Runway account/API key (with a spend cap); or
- Name another authorized generator.

## Plan once authorized
Generate blank bottles/cans, hoodie, and architecture plates; composite the verified vector
labels/logos (never model-rendered text); record provenance in an asset manifest
(name, product, direction, method, sources, rights, review, approval, usage);
QA at full size and web sizes; label all as AI-generated concept imagery.

## Update 2026-10-22 (free-generator verification, per the "no charges, no new subscription" authorization)
Checked from this Claude Code sandbox:

| Candidate | Result |
|---|---|
| Pollinations (free, no-account image endpoint) | Outbound request refused by the session proxy (HTTP 403 on CONNECT). |
| Hugging Face Inference API / hosted Space URLs | Refused by the proxy (403). The HF connector can search but not invoke Spaces. |
| Local diffusion model | None installed (no torch/diffusers; 4 CPU cores, no GPU). Weights could not be fetched through the proxy either. |
| Account/usage rights | Nothing to verify: no generator is reachable, so no terms were accepted and no image was produced. |

Outcome: **no suitable free generator is accessible from Claude Code in this environment. 0 generated images exist.**
Options that stay within "no charges": (a) Ritesh generates images himself with a free tier he already holds and drops the files in; I composite the vector branding and run QA/provenance; (b) the environment network policy is widened to allow a named free service (needs his decision and its terms checked first; see `read_documentation` topic environment.network).
