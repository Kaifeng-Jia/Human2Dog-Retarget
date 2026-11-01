# HOI clips for the full-optimization line (fullopt spec v0.2 §2.1, §8.5)

Run `R026_fullopt_hoi` · code `v0.3.1-1-g8877af2` (dirty=False) · dev 10 · held-out 4 · 0 errors · **FAIL**

| split | id | dataset | task (run) | object | subject | frames | fps | hand contact labels | problems |
|---|---|---|---|---|---|---|---|---|---|
| dev | sub6_largetable_033_3 | omomo_new | c01_sub6_largetable_033 (R022_tasks) | largetable | sub6 | 186 | 30 | True |  |
| dev | sub12_largebox_000_0 | omomo_new | c02_sub12_largebox_000 (R022_tasks) | largebox | sub12 | 258 | 30 | True | head above the ankles 0.77 m: not metres, or not a standing person |
| dev | sub5_largetable_030_17 | omomo_new | c03_sub5_largetable_030 (R022_tasks) | largetable | sub5 | 159 | 30 | True |  |
| dev | sub12_largebox_065_23 | omomo_new | c04_sub12_largebox_065 (R022_tasks) | largebox | sub12 | 192 | 30 | True |  |
| dev | sub1_suitcase_008_5 | omomo_new | c06_sub1_suitcase_008 (R022_tasks) | suitcase | sub1 | 129 | 30 | True |  |
| dev | sub3_largebox_032_80 | omomo_new | c07_sub3_largebox_032 (R022_tasks) | largebox | sub3 | 181 | 30 | True |  |
| dev | sub3_largebox_031_80 | omomo_new | c08_sub3_largebox_031 (R022_tasks) | largebox | sub3 | 178 | 30 | True |  |
| dev | sub12_largebox_089_16 | omomo_new | c09_sub12_largebox_089 (R022_tasks) | largebox | sub12 | 245 | 30 | True |  |
| dev | sub1_largetable_074_5 | omomo_new | c10_sub1_largetable_074 (R022_tasks) | largetable | sub1 | 210 | 30 | True |  |
| dev | sub1_largetable_073_6 | omomo_new | c12_sub1_largetable_073 (R022_tasks) | largetable | sub1 | 203 | 30 | True |  |
| heldout | sub6_trashcan_003_24 | omomo_new | trashcan_side (R022_tasks) | trashcan | sub6 | 192 | 30 | True | not z-up: head, pelvis and ankles are not above one another; head above the ankles 0.70 m: not metres, or not a standing person |
| heldout | sub7_smallbox_041_41 | omomo_new | smallbox_top (R022_tasks) | smallbox | sub7 | 173 | 30 | True |  |
| heldout | sub7_largebox_041_35 | omomo_new | largebox_top (R022_tasks) | largebox | sub7 | 165 | 30 | True |  |
| heldout | 0630_61-2_472 | force | c11_0630_61-2 (R022_tasks) | backpack | session0630 | 712 | 30 | True |  |
