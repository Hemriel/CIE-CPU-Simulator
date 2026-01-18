# CPU Interface Layout — Detailed Spatial Description

## Overall Structure

The interface is organized into five vertical zones, arranged from left to right:

1. Control & Execution Unit (CU + ALU block)
2. Internal System Bus
3. CPU Registers
4. Outer buses: Address and data
5. Main Memory (RAM)

All zones extend vertically to exploit available space.
All components have borders with their name labeled on the top-left corner of the border.
All number displays can toggle between denary, binary, or hex, except for the address labels inside the RAM data block.

### 1. Control & Execution Unit (Leftmost Zone)

**Position**

Far left of the interface.

**Internal Structure**

This zone is divided vertically into two stacked sub-blocks:

#### 1.1 Control Unit (CU) — Top-left

**Relative position**

Located in the top corner of the zone.

Inside it, a highlighted sub-area shows the current step (fetch/decode/execute).

**Two sub-components**

- A display of the current instruction in mnemonics plus hex.
- The RTN step currently executed.

#### 1.2 ALU Block — Bottom-left

**Relative position**

Directly below the CU, sharing the same width and matching or exceeding the CU height.

**Four sub-components**

- Two sub-displays for the operands.
- A label “mode” beneath the ALU bars.
- A “flag” indicator at the bottom (with a circled bit).

### 2. Internal System Bus (Central Vertical Spine)

**Position**

A narrow vertical column with no borders that stretches the full height, labeled “data bus” at the top.
It sits between the CU/ALU block and the registers.

**Function**

Represents the internal data bus.
Conceptually connects:

- Registers ↔ ALU
- Registers ↔ CU

It is not the external address/data bus to RAM (those are shown separately).

**Visual importance**

Serves as a central animation path.
Data movement can be animated along this column to show:

### 3. CPU Registers (Center Zone)

**Position**

Immediately to the right of the internal bus, with registers stacked vertically in a column.

**Order (Top → Bottom)**

The registers are arranged top to bottom as follows:

- `MAR (Memory Address Register)`
- `MDR (Memory Data Register)`
  - small spacer
- `PC (Program Counter)`
- `CIR (Current Instruction Register)`
  - small spacer
- `ACC (Accumulator)`
- `IX (Index Register)`

Investigate later how to highlight activity and differentiate read/write

### 4. Outer Buses

Two borderless vertical buses separated by a thin horizontal gap:

- Top ~15%: a thin bus labeled “address bus” linking `MAR` to the RAM address block.
- Bottom ~85%: a bus labeled “data bus” at the bottom, connecting `MDR` to the currently read data in the RAM data section.

### 5. Main Memory (RAM) — Rightmost Zone

**Position**

Far right of the interface.

**Shape**

Tall vertical rectangle labeled clearly “RAM.”

**Subsections**

- Address block at the top displays the address currently under focus.
- Scrollable data block stretches the full height, auto-scrolling and highlighting the current address. Each RAM line is shown as `<address> : data`, where `address` is always hexadecimal and `data` follows the user-selected display mode.

## Interface Widgets

Each widget receives a reference to the backend CPU component it represents and exposes an `_update_display()` callback that the UI driver can pass in to trigger redraws. The widgets know the internal state required to render their data and may import directly from the backend component classes, but the CPU components themselves remain agnostic and only publish the protocol defined in their own files.

### Control Unit Display

- Hooks into the Control Unit component to read the current instruction mnemonic, and the operand for it (by name if register, or decimal value if shift, or "long" if current instruction has long operand), and the RTN step that is active.
- Highlights the current fetch/decode/execute step in a dedicated sub-area and renders the mnemonic alongside the opcode for student clarity.
- Exposes `_update_display()` that reads the Control Unit state and refreshes the mnemonic, operand, and RTN step whenever the CPU calls for it.

### ALU Display

- Reads the operands, current mode, and flag bits directly from the ALU component to paint the two operand bars, the mode label, and the circled flag indicator.
- The mode label reflects the active operation (add, sub, AND, OR, etc.) and updates whenever the ALU transitions to a new execution micro-step.

### Internal Bus Display

- Listens to the data bus model to visualize moving tokens between CU, registers, and ALU along the central spine.
- `_update_display()` inspects the last bus transaction (source, destination, value) and triggers a short animation or highlight so the lane matches the underlying transfer (e.g., `ACC → ALU`).

### Register Displays (one per register)

Each register widget owns a single register (MAR, MDR, PC, CIR, ACC, IX) and is responsible for rendering its current value in the selected radix:

- The widget queries the register component for its value.
- `_update_display()` refreshes the numeric value, toggles the denary/binary/hex view, and applies any activity highlight if the register was part of the last bus transfer.

### Address Bus Display

- Displays a path from MAR to the RAM's address block. Is greyed out when unused. When used, displays the direction of transfert (always the same for this bus).

### Data Bus Display (outer)

- Connects MDR to the RAM data visualization. Same behavior as address bus, except direction of transfert can vary.

### DAta Bus display (inner)

- Connect registers, CU, and ALU together. Greyed out when usnused, should connect currently used components when in use. doesn't display direction of tranfert for ease of implementation.

### RAM Address Block Display

- Watches the RAM component’s current focus and renders that address at the top of the RAM zone, in the format chosen by user.
- `_update_display()` is invoked whenever the CPU requests a memory transfer so the focused address matches what MAR is pointing at.

### RAM Data Block Display

- Scrolls through the RAM contents, showing lines as `<address> : data` with data rendered in the user-selected mode and address always in hexadecimal.
- Highlights the line currently being accessed and auto-scrolls to keep it visible; `_update_display()` reads both the focused address and the raw data payload from RAM.

Each widget keeps its responsibilities separate and simple rather than sharing a generic sub-component (e.g generic number display), so students can follow how each CPU part exposes its own state and behavior.
