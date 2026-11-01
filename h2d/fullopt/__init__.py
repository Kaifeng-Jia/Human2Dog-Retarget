"""Full-optimization line (no X-Morph): whole-body interaction retargeting, spec docs/spec/fullopt/v0.2_zh.md.

hoi      the only input: a human-object interaction clip (world joint positions, object mesh and poses, spec §2.1)
signals  human-side gait signals: foot contacts, touchdowns, stand / shuffle / walk segments (spec §6.1)
gait     the dog's natural rhythm from dynamic similarity, B2 leg geometry (spec §6.2-6.3)
tasks    the tasks it solves (the same as the learned line's)
"""
