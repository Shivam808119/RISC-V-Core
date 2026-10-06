# Single-Cycle RISC-V Core in Verilog (RV32I + M extension)

A small, readable **32-bit RISC-V CPU core written in Verilog**. Every instruction finishes in **one clock cycle**, and the core can do all the basic arithmetic: **add, subtract, multiply, divide and remainder**, plus logic, shifts, comparisons, branches, jumps and word loads/stores.

It is meant for learning: the whole CPU is about 270 lines in a single file, with a testbench and a ready-to-run test program.

![Datapath](docs/images/datapath.svg)

---

## Table of contents

1. [Features](#features)
2. [Repository layout](#repository-layout)
3. [How a CPU core works (quick idea)](#how-a-cpu-core-works-quick-idea)
4. [Architecture](#architecture)
5. [The modules in detail](#the-modules-in-detail)
6. [Instruction formats and decoding](#instruction-formats-and-decoding)
7. [Supported instructions](#supported-instructions)
8. [Control signals](#control-signals)
9. [Next-PC logic (branches and jumps)](#next-pc-logic-branches-and-jumps)
10. [The test program](#the-test-program)
11. [How to run the simulation](#how-to-run-the-simulation)
12. [Writing your own program](#writing-your-own-program)
13. [Limitations](#limitations)
14. [Ideas for improvement](#ideas-for-improvement)
15. [License](#license)

---

## Features

| Area | What is implemented |
|---|---|
| Base ISA | **RV32I** integer instructions: add, sub, logic, shifts, compare, immediates, `lui`, `auipc` |
| Extension | **M extension**: `mul`, `mulh`, `mulhsu`, `mulhu`, `div`, `divu`, `rem`, `remu` |
| Control flow | `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu`, `jal`, `jalr` |
| Memory | `lw` and `sw` (word access), separate instruction and data memory (Harvard style) |
| Timing | **Single cycle**: fetch, decode, execute, memory and write-back all happen in one clock |
| Registers | 32 x 32-bit register file, `x0` hardwired to zero |
| Verification | Self-checking testbench that prints PASS / FAIL per register |

**39 instructions** in total. Division follows the RISC-V rules for divide-by-zero and overflow.

---

## Repository layout

```
.
├── riscv_core.v            # All hardware: alu, regfile, imem, dmem, riscv_core (top)
├── tb_riscv_core.v         # Self-checking testbench
├── program.hex             # Test program in machine code (one 32-bit word per line)
├── ref_model.py            # Tiny Python model that runs program.hex to cross-check expected values
├── docs/
│   ├── gen_images.py       # Script that generates the diagrams below
│   └── images/             # SVG diagrams used in this README
└── README.md
```

---

## How a CPU core works (quick idea)

A processor repeats the same loop forever:

1. Look at the **program counter (PC)**. It holds the address of the next instruction.
2. **Fetch** the 32-bit instruction stored at that address.
3. **Decode** it. Which operation is it? Which registers does it use?
4. **Execute** it using the ALU (the calculator).
5. Read or write **memory** if needed.
6. **Write the result** into a register.
7. Update the PC (usually PC + 4, or somewhere else for a branch or jump) and repeat.

In this core, steps 1 to 6 all happen **combinationally inside one clock cycle**. On the next rising clock edge, the PC and the register file / data memory are updated together.

![One clock cycle](docs/images/cycle-flow.svg)

---

## Architecture

The core is made of four small building blocks and one top module that wires them together.

![Module hierarchy](docs/images/modules.svg)

| Module | Job | Size |
|---|---|---|
| `alu` | The calculator: arithmetic, logic, shifts, comparisons | combinational |
| `regfile` | 32 fast storage slots, 2 read ports and 1 write port | 32 x 32 bit |
| `imem` | Holds the program, loaded from `program.hex` | 256 words (1 KB) |
| `dmem` | Holds data for `lw` / `sw` | 256 words (1 KB) |
| `riscv_core` | Top: PC, decoder, control unit, immediate generator, branch comparator, next-PC logic | - |

The datapath diagram at the top shows how data flows between them. Solid lines carry data. Dashed purple lines are **control signals** that the decoder produces to tell the other blocks what to do for the current instruction.

---

## The modules in detail

### `alu`: the calculator

Inputs: operands `a` and `b`, a 5-bit operation code `op`. Output: result `y`.

![ALU operations](docs/images/alu-ops.svg)

Key points:

* **Add / subtract** use the plain `+` and `-` operators.
* **Multiply** computes the full 64-bit product. `MUL` returns the low 32 bits. `MULH`, `MULHSU` and `MULHU` return the high 32 bits for signed x signed, signed x unsigned and unsigned x unsigned operands.
* **Divide / remainder** have signed and unsigned versions. The RISC-V specification defines what happens in two special cases, and the ALU implements them:

  | Case | `div` result | `rem` result |
  |---|---|---|
  | Divide by zero | `-1` (all ones) | the dividend `x` |
  | `INT_MIN / -1` (overflow) | `INT_MIN` | `0` |

* **M extension encoding trick:** for multiply/divide the ALU code is `10 + funct3`, so `funct3 = 000..111` maps to `MUL, MULH, MULHSU, MULHU, DIV, DIVU, REM, REMU` (codes 10 to 17).

### `regfile`: the registers

![Register file](docs/images/register-file.svg)

* Two **read ports** are combinational, so the operands are available immediately.
* One **write port** updates on the rising clock edge when `we` is high.
* Register **`x0` always reads as 0** and ignores writes, as the RISC-V spec requires. This gives programs a free constant zero.

### `imem` and `dmem`: the memories

* `imem` is read-only. At start-up it runs `$readmemh("program.hex", mem)` to load the program. Unused words are filled with `NOP` (`addi x0, x0, 0`).
* `dmem` reads combinationally and writes on the clock edge.
* Both use address bits `[9:2]`, so each has 256 words and addresses wrap around after 1 KB.

### `riscv_core`: the top module

It contains the **PC register**, the **instruction decoder**, the **control unit**, the **immediate generator**, the **branch comparator** and the **next-PC logic**, and it instantiates the four modules above. The sections below explain each piece.

---

## Instruction formats and decoding

Every RISC-V instruction is exactly 32 bits. The same bit positions are reused for the same purpose across formats, which keeps the decoder small.

![Instruction formats](docs/images/instruction-formats.svg)

The decoder slices fields straight out of the instruction word:

```verilog
wire [6:0] opcode = instr[6:0];
wire [4:0] rd     = instr[11:7];
wire [2:0] funct3 = instr[14:12];
wire [4:0] rs1    = instr[19:15];
wire [4:0] rs2    = instr[24:20];
wire [6:0] funct7 = instr[31:25];
```

### Immediate generator

Constants inside instructions are stored in scattered bit positions, depending on the format. The immediate generator reassembles them and **sign-extends** to 32 bits:

```verilog
wire [31:0] imm_i = {{20{instr[31]}}, instr[31:20]};
wire [31:0] imm_s = {{20{instr[31]}}, instr[31:25], instr[11:7]};
wire [31:0] imm_b = {{19{instr[31]}}, instr[31], instr[7], instr[30:25], instr[11:8], 1'b0};
wire [31:0] imm_u = {instr[31:12], 12'b0};
wire [31:0] imm_j = {{11{instr[31]}}, instr[31], instr[19:12], instr[20], instr[30:21], 1'b0};
```

### Opcodes recognised

| Opcode (binary) | Format | Instructions |
|---|---|---|
| `0110011` | R | add, sub, sll, slt, sltu, xor, srl, sra, or, and, **mul, mulh, mulhsu, mulhu, div, divu, rem, remu** |
| `0010011` | I | addi, slti, sltiu, xori, ori, andi, slli, srli, srai |
| `0000011` | I | lw |
| `0100011` | S | sw |
| `1100011` | B | beq, bne, blt, bge, bltu, bgeu |
| `1101111` | J | jal |
| `1100111` | I | jalr |
| `0110111` | U | lui |
| `0010111` | U | auipc |

An R-type instruction with `funct7 = 0000001` is an **M-extension** instruction (multiply / divide). Otherwise `funct3` and bit 30 of `funct7` select the base operation (for example `funct7[5]` distinguishes `sub` from `add`, and `sra` from `srl`).

---

## Supported instructions

| Group | Instructions | What they do |
|---|---|---|
| Add / subtract | `add`, `sub`, `addi` | `rd = rs1 + rs2`, `rd = rs1 - rs2`, `rd = rs1 + imm` |
| Multiply | `mul`, `mulh`, `mulhsu`, `mulhu` | low or high 32 bits of the 64-bit product |
| Divide | `div`, `divu`, `rem`, `remu` | signed / unsigned quotient and remainder |
| Logic | `and`, `or`, `xor`, `andi`, `ori`, `xori` | bitwise operations |
| Shift | `sll`, `srl`, `sra`, `slli`, `srli`, `srai` | shift left, logical right, arithmetic right |
| Compare | `slt`, `sltu`, `slti`, `sltiu` | `rd = 1` if less than, else `0` |
| Memory | `lw`, `sw` | load / store one 32-bit word |
| Branch | `beq`, `bne`, `blt`, `bge`, `bltu`, `bgeu` | jump to `PC + imm` if the condition is true |
| Jump | `jal`, `jalr` | jump and save the return address (`PC + 4`) in `rd` |
| Upper immediate | `lui`, `auipc` | load `imm << 12`, or add it to the PC |

---

## Control signals

The control unit is one big `case (opcode)` that sets these signals for the current instruction:

| Signal | Meaning |
|---|---|
| `reg_we` | Write the result into register `rd` |
| `mem_we` | Write `rs2` into data memory (stores) |
| `use_imm` | ALU second operand is the immediate instead of `rs2` |
| `alu_op` | Which ALU operation to perform |
| `wb_sel` | Write-back source: `0` ALU result, `1` loaded data, `2` PC + 4, `3` immediate / `auipc` value |
| `is_branch`, `is_jal`, `is_jalr` | Tell the next-PC logic which kind of control-flow instruction this is |

| Opcode | `reg_we` | `mem_we` | `use_imm` | `wb_sel` | Notes |
|---|:-:|:-:|:-:|:-:|---|
| R-type | 1 | 0 | 0 | 0 | ALU on `rs1`, `rs2` |
| I-type ALU | 1 | 0 | 1 | 0 | ALU on `rs1`, immediate |
| `lw` | 1 | 0 | 1 | 1 | address = `rs1 + imm` |
| `sw` | 0 | 1 | 1 | - | address = `rs1 + imm`, data = `rs2` |
| branch | 0 | 0 | 0 | - | compare `rs1`, `rs2` |
| `jal` | 1 | 0 | 0 | 2 | `rd = PC + 4` |
| `jalr` | 1 | 0 | 1 | 2 | `rd = PC + 4` |
| `lui` / `auipc` | 1 | 0 | 0 | 3 | `imm`, or `PC + imm` |

---

## Next-PC logic (branches and jumps)

At the clock edge the PC loads `next_pc`, chosen by priority:

```verilog
wire [31:0] next_pc =
    is_jalr                    ? ((rd1 + imm) & 32'hFFFFFFFE) :  // jump to register + imm
    is_jal                     ? (pc + imm) :                    // jump to PC + imm
    (is_branch && take_branch) ? (pc + imm) :                    // taken branch
                                 pc + 4;                         // normal: next instruction
```

`take_branch` comes from a comparator that uses `funct3`:

| `funct3` | Instruction | Condition |
|---|---|---|
| `000` | `beq` | `rs1 == rs2` |
| `001` | `bne` | `rs1 != rs2` |
| `100` | `blt` | `rs1 < rs2` (signed) |
| `101` | `bge` | `rs1 >= rs2` (signed) |
| `110` | `bltu` | `rs1 < rs2` (unsigned) |
| `111` | `bgeu` | `rs1 >= rs2` (unsigned) |

---

## The test program

`program.hex` holds 12 instructions. The testbench lets them run, then checks registers `x1` to `x10`.

![Test program trace](docs/images/program-trace.svg)

The expected values were also cross-checked with `ref_model.py`, a small independent Python model of the same instructions:

```
python3 ref_model.py
```

---

## How to run the simulation

### 1. Install the free tools

| OS | Command |
|---|---|
| Ubuntu / Debian | `sudo apt install iverilog gtkwave` |
| macOS (Homebrew) | `brew install icarus-verilog gtkwave` |
| Windows | Install Icarus Verilog and GTKWave from their installers, or use WSL with the Ubuntu command |

### 2. Compile and run

Run these from the repository folder (the program is loaded from `program.hex` in the current directory):

```bash
iverilog -g2012 -o sim riscv_core.v tb_riscv_core.v
vvp sim
```

### 3. Expected output

```
PASS: x1 = 20
PASS: x2 = 6
PASS: x3 = 26
PASS: x4 = 14
PASS: x5 = 120
PASS: x6 = 3
PASS: x7 = 2
PASS: x8 = 26
PASS: x9 = 28
PASS: x10 = -1

ALL TESTS PASSED
```

### 4. View the waveforms (optional)

The testbench writes `core.vcd`:

```bash
gtkwave core.vcd
```

Useful signals to add: `dut.pc`, `dut.instr`, `dut.alu_y`, `dut.reg_we`, `dut.wb_data`. Watching `pc` step by 4 each clock and `x1` to `x10` fill in is a good way to see the single-cycle behaviour.

---

## Writing your own program

`program.hex` is plain text: **one 32-bit instruction in hexadecimal per line**, starting at address 0. You can write one by hand, or assemble it with the RISC-V GNU toolchain:

```asm
# prog.s
    addi x1, x0, 100
    addi x2, x0, 7
    mul  x3, x1, x2      # 700
    div  x4, x3, x2      # 100
done:
    j done               # stop here
```

```bash
riscv64-unknown-elf-as -march=rv32im -mabi=ilp32 -o prog.o prog.s
riscv64-unknown-elf-ld -m elf32lriscv -Ttext=0 -o prog.elf prog.o
riscv64-unknown-elf-objcopy -O binary prog.elf prog.bin
od -An -v -tx4 -w4 prog.bin | tr -d ' ' > program.hex
```

Then update the checks in `tb_riscv_core.v` to match your program. Always end a program with an infinite loop (`j .`), otherwise the PC runs on into the `NOP`s that fill the rest of instruction memory.

---

## Limitations

This core is intentionally simple.

* **Word-only memory access.** Only `lw` and `sw` are implemented. Byte and halfword instructions (`lb`, `lbu`, `lh`, `lhu`, `sb`, `sh`) are not, and if used they would behave as word accesses. Address bits `[1:0]` are ignored.
* **No system instructions:** no `ecall`, `ebreak`, `fence`, CSRs, interrupts or exceptions. Unknown opcodes act as a no-op.
* **Small memories:** 1 KB each for instructions and data, and addresses wrap around.
* **Slow clock in real hardware.** In a single-cycle design the clock period must fit the slowest instruction. The `*`, `/` and `%` operators create long combinational paths, so this design is great for simulation and learning but would run slowly on an FPGA. Real cores use pipelines and multi-cycle dividers.
* **Memory style.** Memories are read combinationally, so synthesis tools will build them from logic or distributed RAM rather than block RAM.
* **Writes during reset.** The register file and data memory are not gated by `reset`, only the PC is.

---

## Ideas for improvement

* Add byte and halfword loads and stores (`lb`, `lh`, `sb`, `sh`).
* Replace `/` and `%` with a multi-cycle divider (for example shift-and-subtract) and add a stall signal.
* Turn it into a 5-stage pipeline (fetch, decode, execute, memory, write-back) with hazard detection and forwarding.
* Add a UART or LED output register so the core can run on an FPGA board (with a constraints file).
* Add the CSR / `ecall` instructions and a simple trap mechanism.
* Run the official `riscv-tests` suite for deeper verification.

---

## License

No license has been chosen yet. Before publishing, add a `LICENSE` file (for example MIT) so others know how they may use the code.
