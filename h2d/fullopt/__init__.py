"""Full-optimization line (no X-Morph): whole-body interaction retargeting, spec docs/spec/fullopt/v0.2_zh.md.

hoi       the only input: a human-object interaction clip (world joint positions, object mesh and poses, spec §2.1)
signals   human-side gait signals: foot contacts, touchdowns, stand / shuffle / walk segments (spec §6.1)
gait      the dog's natural rhythm from dynamic similarity, B2 leg geometry (spec §6.2-6.3)
tasks     the tasks it solves (the same as the learned line's)
task      task targets from the clip alone: contact, approach, tool pose, gate (spec §2, learned spec §5)
robot     a robot read from its description: kinematics, Jacobians, limits, collision groups (spec §7.4)
relation  the relation term, exchangeable representations: (a) vertex substitution (spec §5)
solver    the per-frame SQP (spec §7)
evaluate  reach, penetration, limits and relations with the learned line's definitions (spec §8.1)
"""
