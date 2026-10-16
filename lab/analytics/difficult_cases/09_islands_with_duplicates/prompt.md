# Case 09: Longest streak of consecutive trading days per site

SYNTHETIC fixture. Candidate-facing: this file and fixture.sql only.

`activity(site, day)` lists days on which a site had at least one order; one row PER ORDER, so a day can appear several times. Report each site's longest run of consecutive days, with its first day. If two runs tie, report the earlier one. Output: `site, streak_days, streak_start`, ordered by site.
