# Patch the PC attachment loop to act as if the PC always attaches
# right after the first cmd0B "hello" packet is sent out.

# This location is in the cmd0B send/propagate loop, right after
# either the send or propagate happens. This overwrites the
# invocation of serial1_poll, instead setting the pc-attached
# flag to 1 same as if a cmd0B reply were processed.

0x800cc46
b 16
"wa mov r0, #1; strb r0, [r4]"
#pd

