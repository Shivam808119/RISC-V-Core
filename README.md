# RISC-V-Core



# Understanding RISC-V Cores: From Concept to Silicon

A beginner-friendly guide to how a RISC-V core goes from an idea to a real, working chip.

---

## Table of Contents

1. [What is RISC-V?](#1-what-is-risc-v)
2. [What is a Core?](#2-what-is-a-core)
3. [Writing the Core](#3-writing-the-core)
4. [Simulation](#4-simulation)
5. [Synthesis](#5-synthesis)
6. [Two Paths: FPGA or Fabrication](#6-two-paths-fpga-or-fabrication)
7. [The Full Journey at a Glance](#7-the-full-journey-at-a-glance)



---

## 1. What is RISC-V?

RISC-V is an **open-source instruction set architecture (ISA)**. Think of it as a **rulebook** that defines how a processor should behave: which instructions exist, how registers work, and what each instruction does.

- It is **not** a chip.
- It is **not** a piece of code.
- Anyone can implement it **without paying licensing fees**, unlike proprietary architectures such as ARM or x86.

## 2. What is a Core?

A **core** is an actual **implementation** of the RISC-V rulebook. It is a real hardware design, written in a hardware description language, that follows the rules RISC-V lays out.

| Core | Purpose | Characteristics |
|------|---------|-----------------|
| **PicoRV32** | Embedded and low-power use | Small, size-optimized, simple |
| **Rocket Chip** | General-purpose computing | Pipelined, full-featured, more complex |

> **Rulebook (ISA) -> Core (implementation) -> Chip (physical hardware)**

## 3. Writing the Core

Cores are written in a **Hardware Description Language (HDL)** such as:

- **Verilog**
- **TL-Verilog**
- **Chisel**

Unlike Python or C, an HDL does not describe a list of steps to run. It describes **circuits**: wires, registers, logic gates, and how data flows between them.

| Software (e.g. Python) | Hardware (e.g. Verilog) |
|------------------------|-------------------------|
| Runs on a processor that already exists | Describes the processor itself |
| Sequential instructions | Parallel circuits |
| Output is a printed result | Output is working hardware (or its simulation) |

## 4. Simulation

Once the core is written, it is **simulated** to prove it works before any hardware is built. Tools like **Makerchip** let you write TL-Verilog in the browser and instantly see:

- **The circuit diagram**, showing the structure of the design
- **Waveforms**, showing signals changing over time as the core runs

Simulation answers one question: *does this design behave like a real processor should?*

## 5. Synthesis

After simulation confirms the logic is correct, **synthesis** tools convert the hardware description into a **gate-level netlist**: a detailed list of logic gates and how they connect. This netlist can then be turned into a physical layout.

## 6. Two Paths: FPGA or Fabrication

### Path A: FPGA (Field Programmable Gate Array)
- Reconfigurable hardware that can be loaded with a **bitstream** to behave like your processor
- No custom manufacturing needed
- The most common way hobbyists and students test cores on real hardware

### Path B: Full Fabrication
- The finalized design is sent to a **silicon foundry** such as TSMC
- Requires specialized tools and very high cost
- Typically done by companies, not individuals

## 7. The Full Journey at a Glance

```
  RISC-V Specification (the rulebook)
              |
              v
  Write the core in Verilog / TL-Verilog / Chisel
              |
              v
  Simulate and verify (Makerchip, Icarus Verilog, ...)
              |
              v
  Synthesis -> gate-level netlist
              |
        +-----+------+
        |            |
        v            v
      FPGA       Fabrication
   (bitstream)    (foundry)
        |            |
        +-----+------+
              |
              v
   Real, working processor
```

## 8. getting-started

- **Zero installation:** open [Makerchip](https://www.makerchip.com/) in your browser and follow its built-in RISC-V tutorials.
- **Run a real core locally:** clone [PicoRV32](https://github.com/YosysHQ/picorv32) and run the simple testbench (requires Icarus Verilog):

  ```bash
  git clone https://github.com/YosysHQ/picorv32.git
  cd picorv32
  make test_ez
  ```

  This simulates the core and prints each instruction fetch, read, and write as it executes.



---

