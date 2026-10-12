# References

- [Jane Street protocol emulator competition](https://blog.janestreet.com/protocol-emulator-asic-competition/): open-source submission, CMOS5L, current 6×4 allocation, January 18, 2027 deadline. The final submission form was not published when checked on 2026-10-12.
- [Official CMOS5L template](https://github.com/TinyTapeout/ttihp-verilog-template/tree/cmos5l): integration interface, license and flow conventions.
- [CMOS5L tile definitions](https://github.com/TinyTapeout/tt-support-tools/blob/ihp-sg13cmos5l/tech/ihp-sg13cmos5l/tile_sizes.yaml): 6×4 is supported by the flow.
- [NXP UM10204, revision 7.0](https://cache.nxp.com/docs/en/user-guide/UM10204.pdf): I²C behavior and timing.
- [RP2040 datasheet](https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf): programmable I/O background.
- [Pinned IHP CMOS5L cell models](https://github.com/IHP-GmbH/IHP-Open-PDK/tree/2bbec755dc67ca3db0261c3d6163e15735d66710/ihp-sg13cmos5l/libs.ref/sg13cmos5l_stdcell/verilog): attributed cell and primitive models used for functional gate simulation.

The initial 50 MHz core-clock target is an internal comparison point. The
competition announcement does not specify it as a mandatory clock frequency.
Apache-2.0 is used for the project and matches the official template license.
