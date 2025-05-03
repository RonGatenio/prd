# Bug list from PMRace

## Based on Table 2 from the article *Efficiently Detecting Concurrency Bugs in Persistent Memory Programs*

### RECIPE - P-CLHT
| type  | write             | read              | pmrace | cprd |
| ----- | ----------------- | ----------------- | ------ | ---- |
| Inter | clht_lb_res.c:785 | clht_lb_res.c:417 | V      | V    |
| Intra | clht_lb_res.c:789 | clht_gc.c:190     | V      | V    |
| Other | clht_lb_res.c:321 | clht_lb_res.c:616 | V      |      |

The 2nd bug is inter in my logs - must confirm! (but why not intra as well?)

### CCEH
| type  | write      | read         | pmrace | cprd |
| ----- | ---------- | ------------ | ------ | ---- |
| Intra | CCEH.h:165 | CCEH.cpp:171 | V      | V - read at 185 because a different ctor was used in the test |

### Fast Fair
| type  | write       | read        | pmrace | cprd |
| ----- | ----------- | ----------- | ------ | ---- |
| Inter | btree.h:560 | btree.h:876 | V      | V    |

