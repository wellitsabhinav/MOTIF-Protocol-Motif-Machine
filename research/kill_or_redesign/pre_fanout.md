# pre implementation fanout

Clock nets and constant ties are excluded. Pin count includes multiple pins on one cell. `cone` is the combinational predecessor cone, stopped at registers/inputs. Raw net names may lack unique RTL attribution.

| Rank | Net | Fanout pins | Driver | Buffer sinks | Cone cells | Named source examples |
|---|---|---:|---|---:|---:|---|
| 1 | _06437_ | 922 | ['_14990_', 'Y'] | 0 | 1 | rst_n |
| 2 | _01711_ | 474 | ['_21686_', 'Y'] | 0 | 9 | address[0], address[1], address[2], address[3] |
| 3 | _02216_ | 473 | ['_22356_', 'Y'] | 0 | 9 | address[0], address[1], address[2], address[3] |
| 4 | rst_n | 306 | None | 0 | 0 | rst_n |
| 5 | _01764_ | 272 | ['_21752_', 'Y'] | 0 | 1 | address[0], address[1] |
| 6 | _01792_ | 265 | ['_21788_', 'X'] | 0 | 1 | address[0], address[1] |
| 7 | _01699_ | 259 | ['_21674_', 'Y'] | 0 | 1 | address[0], address[1] |
| 8 | _01743_ | 258 | ['_21723_', 'Y'] | 0 | 1 | address[0], address[1] |
| 9 | _07360_ | 197 | ['_15929_', 'Y'] | 0 | 1 | core.exchange.pc_o[0], core.exchange.pc_o[1] |
| 10 | _07364_ | 194 | ['_15933_', 'Y'] | 0 | 1 | core.exchange.pc_o[0], core.exchange.pc_o[1] |
| 11 | _08570_ | 188 | ['_17139_', 'Y'] | 0 | 2173 | active, control[0], control[1], control[2] |
| 12 | _08562_ | 183 | ['_17131_', 'Y'] | 0 | 2173 | active, control[0], control[1], control[2] |
| 13 | _11250_ | 179 | ['_19819_', 'Y'] | 0 | 5248 | active, control[0], control[1], control[2] |
| 14 | _11256_ | 178 | ['_19825_', 'Y'] | 0 | 5248 | active, control[0], control[1], control[2] |
| 15 | _11254_ | 177 | ['_19823_', 'Y'] | 0 | 5248 | active, control[0], control[1], control[2] |
| 16 | _07362_ | 173 | ['_15931_', 'Y'] | 0 | 1 | core.exchange.pc_o[0], core.exchange.pc_o[1] |
| 17 | _07358_ | 173 | ['_15927_', 'X'] | 0 | 1 | core.exchange.pc_o[0], core.exchange.pc_o[1] |
| 18 | _08565_ | 172 | ['_17134_', 'Y'] | 0 | 2173 | active, control[0], control[1], control[2] |
| 19 | _11252_ | 169 | ['_19821_', 'Y'] | 0 | 5248 | active, control[0], control[1], control[2] |
| 20 | _08568_ | 168 | ['_17137_', 'Y'] | 0 | 2173 | active, control[0], control[1], control[2] |
