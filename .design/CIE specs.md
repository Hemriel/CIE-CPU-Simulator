# CIE Computer Science 9618 Specifications for CPU Simulator

This document captures the precise requirements from Cambridge International Examinations (CIE) Computer Science 9618 syllabus (2026 examination) and authorized revision materials. It serves as the single source of truth for implementation decisions.

---

## Part 1: CPU Registers and Data Paths

### 1.1 Special-Purpose Registers

The CPU must implement the following seven special-purpose registers as defined by CIE 9618:

| Register | Abbreviation | Size | Purpose |
|----------|--------------|------|---------|
| Program Counter | PC | 16-bit | Holds the memory address of the next instruction to fetch |
| Memory Address Register | MAR | 16-bit | Holds the memory address for any read or write operation |
| Memory Data Register | MDR | 16-bit | Holds data being transferred to/from memory |
| Current Instruction Register | CIR | 16-bit | Holds the fetched instruction (opcode + operand) |
| Accumulator | ACC | 16-bit | Main working register for ALU operations and temporary storage |
| Index Register | IX | 16-bit | Holds offset value for indexed addressing calculations |
| Status Register (Flags) | SR | 8-bit | Holds condition flags set by ALU operations |

#### Register Behaviors

**Program Counter (PC)**

- After each instruction fetch, PC is automatically incremented: `PC ← PC + 1`
- Unconditional branch/jump instructions directly update PC: `PC ← target_address`
- Conditional branches update PC only if their condition flags are set
- Initial value: 0 (or configurable start address)

**Memory Address Register (MAR)**

- Output drives the address bus to memory
- Contains the address for the next memory read or write operation
- Value can be set from: PC, instruction operand, indexed calculation (operand + IX), or indirect address resolution

**Memory Data Register (MDR)**

- Bidirectional connection to data bus
- On memory read: receives data from memory at address in MAR
- On memory write: sends ACC or other data to memory at address in MAR
- Acts as intermediary between CPU registers and external memory

**Current Instruction Register (CIR)**

- Holds the complete fetched instruction (opcode + operand)
- In decode phase: opcode bits sent to Control Unit; operand bits held for execute phase
- Does not participate in ALU operations or memory transfers
- Updated only when a new instruction is fetched

**Accumulator (ACC)**

- Receives ALU operation results
- Can be source or destination for data (load/store operations)
- Implicitly used in some instructions (e.g., arithmetic operations without explicit register name)
- Updated during execute phase for ALU and load operations

**Index Register (IX)**

- Holds an offset value used in indexed addressing calculations
- Added to a base address to calculate the effective address: `EA ← base_address + IX`
- Can be loaded with immediate value (e.g., `LDR #5` loads value 5 into IX)
- Not directly involved in ALU operations other than address calculation

**Status Register (SR) - Flag Register**

- Contains condition flags set by ALU operations and compare instructions:
  - **Zero (Z)**: Set to 1 if ALU result = 0; otherwise 0
  - **Negative (N)**: Set to 1 if ALU result is negative (bit 15 = 1 in two's complement); otherwise 0
  - **Carry (C)**: Set to 1 if arithmetic operation produces carry/borrow; otherwise 0
  - **Overflow (V)**: Set to 1 if arithmetic operation causes signed overflow; otherwise 0
  - Other bits reserved for future use
- Flags are read by conditional branch instructions (e.g., `BRZ` checks Z flag)
- Flags are not directly modified by user code; only by ALU and compare operations

### 1.2 System Buses

Three buses carry data and control signals under Control Unit supervision:

**Address Bus**

- Carries memory addresses from MAR to memory
- Unidirectional: MAR → Memory
- Width: 16 bits (supports addresses 0–65535)

**Data Bus**

- Carries data bidirectionally between CPU registers and memory
- MDR ↔ Memory: for load and store operations
- ACC → ALU → ACC: for arithmetic/logic results
- Width: 16 bits

**Control Bus**

- Carries control signals from Control Unit to memory and peripherals
- Signals include: read, write, clock, reset
- Unidirectional: Control Unit → Memory/Peripherals

---

## Part 2: Fetch-Decode-Execute Cycle

The CPU executes instructions in a three-phase cycle controlled by the Control Unit:

### 2.1 Fetch Phase (Load Instruction)

**Sequence (RTN notation):**

```
1. MAR ← PC              (copy PC address to MAR)
2. MDR ← RAM[MAR]        (read instruction from memory into MDR)
3. PC ← PC + 1           (increment PC for next instruction)
4. CIR ← MDR             (move instruction to CIR)
```

**Timing:** 4 clock cycles (one register transfer per cycle)

**Key Points:**

- Steps 2 and 3 can overlap (simultaneous): memory read while PC increments
- Fetch phase is identical for all instructions
- After fetch, CIR contains complete instruction ready for decode

### 2.2 Decode Phase (Interpret Instruction)

**Action:**

- Control Unit examines opcode bits in CIR
- Opcode determines which operation to perform
- Operand bits extracted from CIR (held for execute phase)
- No register transfers during decode; CU logic only

**Timing:** 1 clock cycle (minimal propagation delay)

**Output:**

- Control signals prepared for execute phase
- Operand value extracted and held

### 2.3 Execute Phase (Perform Operation)

Execution varies by instruction type (see Part 3: Instruction Execution).

**General Pattern:**

1. Calculate effective address (if needed, based on addressing mode)
2. Access memory (if needed)
3. Perform ALU operation (if needed)
4. Update flags (if ALU operation performed)
5. Update destination register (ACC, PC, or memory)

---

## Part 3: Instruction Execution Patterns

All instructions follow one of these execution patterns. Each pattern uses RTN to specify register transfers.

### 3.1 Load Instructions (Direct Addressing)

**Example: `LDD 100` (Load Direct into Accumulator)**

**RTN Sequence:**

```
1. MAR ← operand         (operand = 100 is address)
2. MDR ← RAM[MAR]        (read data from memory)
3. ACC ← MDR             (store data in accumulator)
```

**Flags:** Z and N set based on loaded value; C and V unchanged

---

### 3.2 Store Instructions (Direct Addressing)

**Example: `STO 150` (Store Accumulator)**

**RTN Sequence:**

```
1. MAR ← operand         (operand = 150 is address)
2. MDR ← ACC             (copy ACC to MDR)
3. RAM[MAR] ← MDR        (write MDR to memory)
```

**Flags:** Unchanged (store does not affect flags).

---

### 3.3 Arithmetic Operations (Direct Addressing)

**Example: `ADD 20` (Add)**

**RTN Sequence:**

```
1. MAR ← operand         (operand = 20 is address)
2. MDR ← RAM[MAR]        (read operand from memory)
3. ACC ← ACC + MDR       (perform addition)
4. Update flags (Z, N, C, V) based on result
```

**Flags:**

- **Z**: Set if result = 0
- **N**: Set if result is negative (bit 15 = 1)
- **C**: Set if addition produces carry
- **V**: Set if signed overflow occurs

**Variants:**

- `SUB X`: Subtract (ACC ← ACC - MDR)
- `AND X`: Bitwise AND (ACC ← ACC AND MDR)
- `OR X`: Bitwise OR (ACC ← ACC OR MDR)
- `XOR X`: Bitwise XOR (ACC ← ACC XOR MDR)

---

### 3.4 Compare Instructions

**Example: `CMP 30` (Compare)**

**RTN Sequence:**

```
1. MAR ← operand         (operand = 30 is address)
2. MDR ← RAM[MAR]        (read value to compare)
3. Compute ACC - MDR     (perform subtraction, discard result)
4. Update flags (Z, N, C, V) based on comparison
```

**Flags:**

- **Z**: Set if ACC = MDR (equal)
- **N**: Set if ACC < MDR (ACC - MDR is negative)
- **C**: Set if borrow occurs
- **V**: Set if signed overflow occurs in subtraction
- ACC is **not** modified; flags only

**Note:** Used to set flags before conditional branch instructions.

---

### 3.5 Unconditional Branch Instructions

**Example: `JMP 50` (Jump)**

**RTN Sequence:**

```
1. PC ← operand          (operand = 50 is target address)
```

**Flags:** Unchanged.

**Behavior:**

- PC is directly set to target address
- Next fetch will retrieve instruction from target address
- Always jumps unconditionally

---

### 3.6 Conditional Branch Instructions (Compare-Dependent)

**Example A: `JPE 100` (Jump if Previous comparison was Equal/True)**

**RTN Sequence (if condition met):**

```
If Z flag = 1 (from prior CMP/CMI):
  PC ← operand           (operand = 100 is target address)
Otherwise:
  PC remains unchanged   (continue to next instruction)
```

**Flags:** Unchanged (branch does not modify flags; it only reads them).

**Behavior:**

- PC is set to target address if equality/true condition holds
- Must be preceded by `CMP` or `CMI` instruction
- Used to branch when operands are equal (Z flag set)

---

**Example B: `JPN 100` (Jump if Previous comparison was Not Equal/False)**

**RTN Sequence (if condition met):**

```
If Z flag = 0 (from prior CMP/CMI):
  PC ← operand           (operand = 100 is target address)
Otherwise:
  PC remains unchanged   (continue to next instruction)
```

**Flags:** Unchanged (branch does not modify flags; it only reads them).

**Behavior:**

- PC is set to target address if inequality/false condition holds
- Must be preceded by `CMP` or `CMI` instruction
- Used to branch when operands are not equal (Z flag clear)

---

### 3.7 Indexed Addressing Execution

**Example: `LDX 50` (Load with Indexed Addressing)**

**RTN Sequence:**

```
1. Calculate EA ← operand + IX  (effective address)
2. MAR ← EA                      (set MAR to effective address)
3. MDR ← RAM[MAR]                (read from memory)
4. ACC ← MDR                     (store in accumulator)
```

**Flags:** Z and N set based on loaded value.

**Key Point:** Index register (IX) is **added** to the base operand to calculate effective address. This enables array access and iteration.

**Variants:**

- Other instructions (store, arithmetic) can use indexed mode with same EA calculation

---

### 3.8 Indirect Addressing Execution

**Example: `LDI 200` (Load with Indirect Addressing)**

**RTN Sequence:**

```
1. MAR ← operand                 (operand = 200 is pointer address)
2. MDR ← RAM[MAR]                (read pointer value from memory)
3. MAR ← MDR                     (use pointer value as new address)
4. MDR ← RAM[MAR]                (read actual data from target address)
5. ACC ← MDR                     (store in accumulator)
```

**Flags:** Z and N set based on loaded value.

**Key Point:** Two memory accesses required:

- First access fetches the pointer (address stored in memory)
- Second access fetches the actual data using the pointer

**Variants:**

- `STI X`: Indirect store (reverse pointer-fetch, then store ACC)
- Other instruction types may support indirect mode

---

### 3.9 Immediate Addressing Execution

**Example: `LDM #5` (Load Immediate)**

**RTN Sequence:**

```
1. ACC ← operand                 (operand value = 5 is literal)
```

**Flags:** Z and N set based on loaded value.

**Key Point:**

- Operand is a literal value embedded in instruction
- No memory access required
- Only one clock cycle in execute phase

**Variants:**

- `LDR #n`: Load Immediate into Index Register (IX ← operand)
- `ADD #n`: Add immediate value to ACC
- `SUB #n`: Subtract immediate value from ACC
- `AND #n`: Bitwise AND with immediate value
- `OR #n`: Bitwise OR with immediate value
- `XOR #n`: Bitwise XOR with immediate value
- `CMP #n`: Compare ACC with immediate value

---

### 3.10 Register Transfer Instructions

**Example: `MOV IX` (Move ACC to Index Register)**

**RTN Sequence:**

```
1. IX ← ACC                      (copy accumulator to index register)
```

**Flags:** Unchanged (move does not affect flags).

**Key Point:**

- Copies ACC to specified register (currently IX supported)
- No memory access; register-to-register transfer
- Single clock cycle in execute phase

---

### 3.11 Increment/Decrement Instructions

**Example A: `INC ACC` (Increment Accumulator)**

**RTN Sequence:**

```
1. ACC ← ACC + 1                 (add 1 to accumulator)
2. Update flags (Z, N, C, V) based on result
```

**Flags:** Z, N, C, V set based on result.

**Variants:**

- `INC IX`: Increment Index Register

---

**Example B: `DEC ACC` (Decrement Accumulator)**

**RTN Sequence:**

```
1. ACC ← ACC - 1                 (subtract 1 from accumulator)
2. Update flags (Z, N, C, V) based on result
```

**Flags:** Z, N, C, V set based on result.

**Variants:**

- `DEC IX`: Decrement Index Register

---

### 3.12 Logical Shift Instructions

**Example A: `LSL #3` (Logical Shift Left)**

**RTN Sequence:**

```
1. ACC ← ACC << n                (shift ACC left by n places)
2. Zeros introduced on right end
3. Update flags (Z, N, C) based on result
```

**Flags:** Z and N set based on result; C set to value of last shifted-out bit.

**Key Point:**

- Shifts all bits in ACC left by n positions
- Right-side bits filled with zeros
- Effectively multiplies ACC by 2^n (if no overflow)

---

**Example B: `LSR #2` (Logical Shift Right)**

**RTN Sequence:**

```
1. ACC ← ACC >> n                (shift ACC right by n places)
2. Zeros introduced on left end
3. Update flags (Z, N, C) based on result
```

**Flags:** Z and N set based on result; C set to value of last shifted-out bit.

**Key Point:**

- Shifts all bits in ACC right by n positions
- Left-side bits filled with zeros
- Effectively divides ACC by 2^n

---

### 3.13 Indirect Compare Instruction

**Example: `CMI 200` (Compare with Indirect Addressing)**

**RTN Sequence:**

```
1. MAR ← operand                 (operand = 200 is pointer address)
2. MDR ← RAM[MAR]                (read pointer value from memory)
3. MAR ← MDR                     (use pointer value as new address)
4. MDR ← RAM[MAR]                (read actual data from target address)
5. Compute ACC - MDR             (perform comparison, discard result)
6. Update flags (Z, N, C, V) based on comparison
```

**Flags:**

- **Z**: Set if ACC = data at target address (equal)
- **N**: Set if ACC < data (ACC - value is negative)
- **C**: Set if borrow occurs
- **V**: Set if signed overflow occurs
- ACC is **not** modified; flags only

**Key Point:** Two memory accesses required (fetch pointer, then fetch data), followed by comparison.

---

### 3.14 Input/Output Instructions

**Example A: `IN` (Input Character)**

**RTN Sequence:**

```
1. Read character from input device
2. ACC ← ASCII value of character
3. Update flags (Z, N) based on value
```

**Flags:** Z and N set based on loaded ASCII value.

**Behavior:**

- Waits for user to input a character
- Stores ASCII value in ACC
- Blocks execution until input received

---

**Example B: `OUT` (Output Character)**

**RTN Sequence:**

```
1. character ← ACC (lower 8 bits)
2. Output character to screen
```

**Flags:** Unchanged.

**Behavior:**

- Outputs the character corresponding to ASCII value in ACC
- No flags set; purely output operation

---

### 3.15 Program Termination

**Example: `END` (End Program)**

**RTN Sequence:**

```
1. Halt execution
2. Return control to operating system
```

**Flags:** Unchanged.

**Behavior:**

- Terminates program execution
- CPU enters HALT state
- Control returns to OS or command prompt
- Execution cannot resume from this point

---

## Part 4: Complete Instruction Set Reference

### 4.1 Instruction Set Table

| Mnemonic | Operand | Description |
|----------|---------|-------------|
| LDM | #n | Immediate addressing. Load the number n to ACC |
| LDD | `<address>` | Direct addressing. Load the contents of the location at the given address to ACC |
| LDI | `<address>` | Indirect addressing. The address to be used is at the given address. Load the contents of this second address to ACC |
| LDX | `<address>` | Indexed addressing. Form the address from `<address>` + the contents of the index register. Copy the contents of this calculated address to ACC |
| LDR | #n | Immediate addressing. Load the number n to IX |
| MOV | `<register>` | Move the contents of the accumulator to the given register (IX) |
| STO | `<address>` | Store the contents of ACC at the given address |
| ADD | `<address>` | Add the contents of the given address to the ACC |
| ADD | #n/Bn/&n | Add the number n to the ACC |
| SUB | `<address>` | Subtract the contents of the given address from the ACC |
| SUB | #n/Bn/&n | Subtract the number n from the ACC |
| INC | `<register>` | Add 1 to the contents of the register (ACC or IX) |
| DEC | `<register>` | Subtract 1 from the contents of the register (ACC or IX) |
| JMP | `<address>` | Jump to the given address |
| CMP | `<address>` | Compare the contents of ACC with the contents of `<address>` |
| CMP | #n | Compare the contents of ACC with number n |
| CMI | `<address>` | Indirect addressing. The address to be used is at the given address. Compare the contents of ACC with the contents of this second address |
| JPE | `<address>` | Following a compare instruction, jump to `<address>` if the compare was True |
| JPN | `<address>` | Following a compare instruction, jump to `<address>` if the compare was False |
| IN | (none) | Key in a character and store its ASCII value in ACC |
| OUT | (none) | Output to the screen the character whose ASCII value is stored in ACC |
| END | (none) | Return control to the operating system |
| AND | #n/Bn/&n | Bitwise AND operation of the contents of ACC with the operand |
| AND | `<address>` | Bitwise AND operation of the contents of ACC with the contents of `<address>` |
| XOR | #n/Bn/&n | Bitwise XOR operation of the contents of ACC with the operand |
| XOR | `<address>` | Bitwise XOR operation of the contents of ACC with the contents of `<address>` |
| OR | #n/Bn/&n | Bitwise OR operation of the contents of ACC with the operand |
| OR | `<address>` | Bitwise OR operation of the contents of ACC with the contents of `<address>` |
| LSL | #n | Bits in ACC are shifted logically n places to the left. Zeros are introduced on the right hand end |
| LSR | #n | Bits in ACC are shifted logically n places to the right. Zeros are introduced on the left hand end |

`<address>` can be an absolute or symbolic address\
`#` denotes a denary number, e.g. #123\
`B` denotes a binary number, e.g. B01001010\
`&` denotes a hexadecimal number, e.g. &4A

### 4.2 Labeling Syntax

| Syntax | Purpose |
|--------|---------|
| `<label>: <opcode> <operand>` | Labels an instruction |
| `<label>: - <data>` | Gives a symbolic address `<label>` to the memory location with contents `<data>` |

---

## Part 4: Addressing Mode Summary

The simulator must handle four distinct addressing modes with precise effective address calculations:

| Mode | Effective Address | Memory Accesses | Use Case |
|------|-------------------|-----------------|----------|
| **Immediate** | operand (literal) | 0 | Load constants directly |
| **Direct** | operand | 1 | Direct memory access |
| **Indirect** | RAM[operand] | 2 | Pointer/dynamic addressing |
| **Indexed** | operand + IX | 1 | Array iteration, offset access |

---

## Part 5: Implementation Requirements

### 5.1 Memory Model

- **Size:** Configurable; typical range 0–65535 (64K) addresses
- **Addressability:** 16-bit word-addressed (each address holds a 16-bit value)
- **Initial State:** All locations initialized to 0
- **Access:** Read/write via MAR/MDR only (no direct CPU register-to-register memory moves)
- **Protection:** Simulate read-only regions if applicable to curriculum (advanced feature)

### 5.2 Data Representation

- **Integer Size:** 16-bit signed two's complement
- **Range:** –32768 to +32767
- **Flags:** Condition flags (Z, N, C, V) in SR as single bits

### 5.3 Instruction Format

- **Size:** 16 bits total
  - **Bits 15–11:** Opcode (5 bits; up to 32 distinct opcodes)
  - **Bits 10–0:** Operand/Address (11 bits; allows 2048 distinct addresses or values)
- **Addressing Mode Indicators:** Not needed, opcodes carry indirect/indexed information, not operand.

### 5.4 Assembler (Two-Pass)

#### Pass 1: Symbol Table Generation

- Scan assembly code
- Identify labels and their corresponding instruction addresses
- Build symbol table mapping label names → memory addresses
- Detect undefined labels (error) and duplicate labels (error)

#### Pass 2: Machine Code Generation

- Scan assembly code again
- For each instruction, resolve labels to addresses using symbol table
- Generate machine code (opcode + operand bits)
- Output machine code to memory

### 5.5 Control Unit State Machine

The Control Unit must explicitly implement these states:

1. **FETCH:** Execute fetch phase (MAR ← PC; MDR ← RAM[MAR]; PC ← PC+1; CIR ← MDR)
2. **DECODE:** Extract opcode and operand; determine operation
3. **EXECUTE:** Perform operation based on opcode and addressing mode
4. **HALT:** Stop execution (reached explicit END instruction or error)

Each state transition is driven by clock pulse; visualization should show current state.

---

## Part 6: Educational Visualization Requirements

The UI must display (in real-time, updating each clock cycle):

1. **Register Values** (updated after execute phase)
   - PC, MAR, MDR, CIR, ACC, IX, SR (with individual flag bits visible)
   - Display as hexadecimal, decimal, or binary (user-switchable)

2. **Memory View** (show code and data regions)
   - Auto-scroll to relevant part of the RAM
   - Address column (hexadecimal)
   - Instruction/data column (hexadecimal, decimal, or binary)
   - Current fetch address highlighted (MAR)
   - Modified locations highlighted (after stores)

3. **Bus State** (show data flow in current cycle, color coded for esay visualization)
   - Address bus: show MAR → address
   - Data bus: show MDR ⇔ memory (external) and ACC ⇔ ALU ⇔ IX (internal)
   - Control signals: show read/write/clock

4. **Control Unit State** (show current phase)
   - Display: FETCH, DECODE, EXECUTE, or HALT
   - Display: opcode, operand split
   - During decode: Mnemonics for the given opcode
   - Clarify which sub-steps are active (e.g., "Fetch: Step 2/4")

5. **Execution Timeline** (optional but valuable)
   - Show sequence of RTN steps for current instruction
   - Highlight completed steps and pending steps

---

## Part 7: Alignment with CIE Exam Material

All implementation decisions must be validated against:

1. **CIE 9618 Syllabus** (Cambridge International, 2026)
   - Official specification of registers, buses, instruction set
   - Expected learning outcomes and assessment objectives

2. **CIE Past Papers & Mark Schemes**
   - Contains worked examples of fetch-decode-execute
   - Shows expected register traces and memory states
   - Clarifies edge cases (e.g., how flags behave in edge cases)

3. **SaveMyExams Revision Notes (CIE Computer Science)**
   - Student-friendly summaries of CPU architecture
   - Reinforces terminology and concepts
   - Provides formative assessment examples

4. **Cambridge Marking Standards**
   - Acceptable answers to common questions (e.g., "describe how SUB instruction is executed")
   - Ensures simulator behavior matches examiner expectations

---

## Sources & References

- Cambridge International AS & A Level 9618 Computer Science syllabus for examination in 2026  
  <https://www.cambridgeinternational.org/Images/697372-2026-syllabus.pdf>

- Computer Science (9618) CAIE AS Level complete notes  
  <https://media.studylast.com/2023/12/Computer-Science-9618-CAIE-AS-Level-complete-notes-p.pdf>

- Fetch-Execute Cycle | CIE A Level Computer Science Revision Notes  
  <https://www.savemyexams.com/a-level/computer-science/cie/19/revision-notes/4-processor-fundamentals-/central-processing-unit-cpu-architecture/fetch-execute-cycle-/>

- Assembly Language Basics | CIE A Level Computer Science Revision  
  <https://www.savemyexams.com/a-level/computer-science/cie/19/revision-notes/4-processor-fundamentals-/assembly-language-/assembly-language-basics/>

---

**Document Status:** First Draft (January 2026)  
**Audience:** Developers, educators, students  
**Last Updated:** January 13, 2026
