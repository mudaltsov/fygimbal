# Jump over the entire pitch follow control loop,
# so the PC can write to param03 without contention

0x800b2b0
b 8
wa b.w 0x800b416
pd
