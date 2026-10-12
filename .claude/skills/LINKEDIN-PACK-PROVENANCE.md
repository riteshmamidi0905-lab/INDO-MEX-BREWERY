# LinkedIn pack provenance

- Upstream: https://github.com/Jakeschincariol/linkedin-agent-skill (MIT, Jake Schincariol)
- Commit reviewed and installed: `add2c23882fe79180737d242ff80a5da205eda6a`
- Installed: 11 skills `li-*`, copied verbatim except one patch below.
- Security review: no `allowed-tools` grants (normal permission prompts still apply), no network/subprocess/eval code in the two Python scripts (stdlib only), no hidden Unicode in skill text, regexes tested for ReDoS, skills explicitly forbid auto-posting and browser scraping.

## Local patch (only one)
`li-human/slop.json`: removed 7 lexicon entries that corrupt technical writing in AI engineering:
`harness` (-> "use": "evaluation harness" became "evaluation use"), `ecosystem`, `paradigm`, `landscape`, `curate`, `curated`, `robust` ("robust statistics").

## Upstream checksums (sha256, before patch)
```
bdb5b12c699ca5d512b785f7168f8e494e020a1ff1195aaa9a58cd5b193c1bf2  skills/li-audit/SKILL.md
fa1a8801e661ed83e55eb5c44e0810a773b490eac930bd3200d783d4bbd23094  skills/li-carousel/SKILL.md
05bfb1fb28976d6ee5d50b31ec7c8d7fc13fba9db71257dc1dad2a0ffd21e071  skills/li-comment/SKILL.md
14b0ee4cffedc2d3eb1d9f8dd6d6cce7bc04c95e221ea1e68809fb5aad525747  skills/li-dm/SKILL.md
2ebda9ff1b63f0d567cd8e30b6fc1465e05c46e166809ea0569cba3591d73d90  skills/li-human/SKILL.md
d8cf740741968f25ce49ec6cc65538f53e97f28f6f2ce21b7f21864475fe2075  skills/li-human/detect.py
8627c813e461459604c5019d28052fbde11a544af86a1c4652b1aff3b38d8757  skills/li-human/humanize.py
2d227835a80ca20259c8d255501cb752cdc4232468c12bb9223fccf5acc724bb  skills/li-human/slop.json
816c1088fdac6a58295b9868267031b210eb57fd325bf837226fb764bce94c77  skills/li-inbox/SKILL.md
5799665246d1c47ab6b37840bd4f4f94700f24ff54ae4d3a1fbaf49b1cd71f9b  skills/li-plan/SKILL.md
acfc8eadc47fee812f2dbaf8c97a93c313661d46963291bcbf8f154b065abee0  skills/li-post/SKILL.md
08988c9afae234199f51323c42baf2507101a4be2ba832384cf20f940972d712  skills/li-post/hooks.json
4f0ebdcf8a3ef035d70aae89838ff916fc8a33a4a12b333e58bb2bc41727d11e  skills/li-profile/SKILL.md
d1add490dad3cc32aab4826c3d5a40bd1552d26a92424deaad9ee2e3c7c05d14  skills/li-profile/rubric.json
26f95e55f384ca2ec1b692d3f95d08d33796fea404db8740387aca15b1248751  skills/li-reply/SKILL.md
9524d3958f153d8be3d679a372c8cb5065e30653ed2a7bf4596e921b2baa39df  skills/li-repurpose/SKILL.md
```
