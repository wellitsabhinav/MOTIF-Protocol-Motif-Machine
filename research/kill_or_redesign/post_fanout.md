# post implementation fanout

Clock nets and constant ties are excluded. Pin count includes multiple pins on one cell. `cone` is the combinational predecessor cone, stopped at registers/inputs. Raw net names may lack unique RTL attribution.

| Rank | Net | Fanout pins | Driver | Buffer sinks | Cone cells | Named source examples |
|---|---|---:|---|---:|---:|---|
| 1 | net858 | 13 | ['fanout858', 'X'] | 0 | 2527 | active, control[0], control[1], control[2] |
| 2 | net894 | 13 | ['fanout894', 'X'] | 0 | 2526 | active, control[0], control[1], control[2] |
| 3 | net905 | 13 | ['fanout905', 'X'] | 0 | 1250 | active, control[0], control[1], control[2] |
| 4 | net1144 | 13 | ['fanout1144', 'X'] | 2 | 27 | address[0], address[1], address[2], address[3] |
| 5 | net2051 | 13 | ['fanout2051', 'X'] | 1 | 1 | address[2] |
| 6 | core.exchange.program_i[288] | 12 | ['_27669_', 'Q'] | 0 | 0 | core.exchange.program_i[288] |
| 7 | net755 | 12 | ['fanout755', 'X'] | 0 | 2633 | active, control[0], control[1], control[2] |
| 8 | core.exchange.first_word[1] | 12 | ['_27382_', 'Q'] | 0 | 0 | core.exchange.first_word[1] |
| 9 | net348 | 12 | ['fanout348', 'X'] | 0 | 6434 | active, control[0], control[1], control[2] |
| 10 | net1992 | 11 | ['fanout1992', 'X'] | 4 | 1 | core.host_tx_data_i[6] |
| 11 | net4045 | 11 | ['rebuffer4045', 'X'] | 1 | 1 | core.exchange.pc_o[3] |
| 12 | core.exchange.program_i[302] | 11 | ['_27683_', 'Q'] | 0 | 0 | core.exchange.program_i[302] |
| 13 | net646 | 11 | ['fanout646', 'X'] | 1 | 2630 | active, control[0], control[1], control[2] |
| 14 | net1903 | 11 | ['fanout1903', 'X'] | 0 | 1 | core.exchange.program_i[386] |
| 15 | net2049 | 11 | ['fanout2049', 'X'] | 1 | 1 | address[3] |
| 16 | core.exchange.program_i[366] | 11 | ['_27747_', 'Q'] | 0 | 0 | core.exchange.program_i[366] |
| 17 | core.exchange.program_i[493] | 11 | ['_27874_', 'Q'] | 0 | 0 | core.exchange.program_i[493] |
| 18 | _10222_ | 10 | ['_18791_', 'Y'] | 0 | 4835 | active, control[0], control[1], control[2] |
| 19 | _03001_ | 10 | ['_23541_', 'Y'] | 0 | 46 | address[0], address[1], address[2], address[3] |
| 20 | core.exchange.program_i[567] | 10 | ['_27948_', 'Q'] | 0 | 0 | core.exchange.program_i[567] |
