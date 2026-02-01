# CPU_Sim

An educational CPU simulator and assembler designed to support CIE IGCSE, AS, and A-Level Computer Science teaching. This tool provides real-time visualization of the two-pass assembly process and CPU execution cycles, bringing abstract concepts from the CIE 9618 syllabus to life.

---

## ⚠️ Important Disclaimers

**This is an educational tool, not an official CIE resource:**

- CPU_Sim is **not affiliated with or endorsed by Cambridge International Examinations**
- There is **no guarantee** that all implementation details perfectly match CIE specifications
- The simulated CPU **does not reflect any real-world CPU architecture**—it is a simplified model designed for teaching purposes
- The tool adheres to available reference documentation published by Cambridge International and CIE-accredited workbooks, but interpretations may vary

**About code quality:**

- This codebase uses "fairly" simple Python code and is heavily documented to allow students to explore and learn from it
- While it demonstrates good practices in many areas (modular design, type hints, docstrings), it **does not claim to be a reference for professional software engineering**
- Many improvements could be made—this is intentional to keep the code accessible to A-level students

---

## 🎯 Project Goals

### Primary Goal: Real-Time Visualization

CPU_Sim provides an **interactive, step-by-step visualization** of:

1. **Two-Pass Assembly Process:**
   - Watch the assembler trim comments and blank lines
   - See Pass 1 build label tables line-by-line
   - Observe Pass 2 emit machine code into RAM in real time

2. **CPU Execution Cycle:**
   - Step through the fetch-decode-execute cycle one micro-operation at a time
   - Watch Register Transfer Notation (RTN) steps execute (e.g., `MAR ← PC`, `ACC ← MDR`)
   - Visualize data flowing through buses, registers, ALU, and memory

Students can **see theory become practice** as abstract concepts from the syllabus (like "the control unit coordinates data movement via buses") appear on screen as animated RTN sequences.

### Secondary Goal: Readable Python Codebase

The source code is designed to be **student-readable**:

- **Comprehensive documentation**: Every module, class, and function has docstrings explaining what it does and why
- **Educational comments**: Complex logic includes comments explaining the reasoning, not just the mechanics
- **CIE terminology**: Variable names use full CIE terms (e.g., `program_counter`, `memory_address_register`)
- **Design patterns**: Code demonstrates clean architecture (state machines, strategy pattern, dispatcher pattern) with explanations

Students curious about "how does an assembler work?" or "how is a CPU simulated?" can read the source and follow along.

---

## 🖥️ Features

### Assembler

- **Two-pass assembler** with progressive visualization:
  - **Trim phase**: Remove comments and blank lines
  - **Pass 1**: Scan source code to build instruction and variable label tables
  - **Pass 2**: Generate machine code and write to RAM
- **Real-time updates**: Editor shows trimmed code; tables highlight new labels as they're discovered
- **Addressing modes**: Immediate (`#n`), direct (`<address>`), indirect (`(<address>)`), indexed (`<address>,IX`)
- **Error detection**: Clear error messages for undefined labels, invalid syntax, and out-of-range operands

### CPU Simulator

- **CIE 9618 register set**: PC, MAR, MDR, CIR, ACC, IX, comparison flag
- **Fetch-Decode-Execute cycle**: Explicit phases with RTN step sequences
- **Instruction set**: ADD, SUB, AND, OR, XOR, LSL, LSR, LDR, STR, JMP, CMP, JPE/JPN, IN, OUT, END
- **ALU operations**: Arithmetic (add, subtract) and logic (AND, OR, XOR) with result visualization
- **Memory model**: 64K addressable 16-bit words
- **I/O support**: Character-based IN/OUT instructions with visual queues

### User Interface (Textual-based)

- **ASCII-art visualization**: Buses, registers, and memory displayed in a terminal-friendly layout
- **Interactive stepping**: Advance one RTN step at a time or run continuously
- **Component highlighting**: Active components are visually highlighted during each step
- **Live assembly editor**: Write, edit, and compile assembly code in-app
- **Label tables**: Watch instruction and variable labels populate during Pass 1
- **RAM viewer**: See memory contents update as code executes

---

## 📚 Curriculum Alignment

CPU_Sim illustrates key topics from the CIE 9618 syllabus:

- **4.1 Central Processing Unit Architecture**: Von Neumann model, registers, ALU, Control Unit, buses
- **4.2 Assembly Language**: Two-pass assembly, addressing modes, instruction execution
- **4.3 Bit Manipulation**: Logical shifts, bitwise operations
- **5.2 Language Translators**: Need for assemblers, translation process
- **9.1 Computational Thinking**: Abstraction, decomposition, pattern recognition

Detailed curriculum references are embedded in code comments and module docstrings.

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- Textual library for terminal UI

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/Hemriel/CIE-CPU-Simulator.git
   cd CPU_Sim
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

### Running the Simulator

Launch the interactive interface:

```bash
python CIE_CPU_Sim.py
```

**Controls:**

- `Ctrl+S`: Compile the assembly code in the editor (starts the interactive assembly process)
- `T`: Tick (advance one step)
- `Q`: Quit

### Example Program

Try this simple Fibonacci program:

```assembly
      LDR #0
      STR VAR1
      LDR #1
      STR VAR2
LOOP: LDR VAR1
      OUT
      ADD VAR2
      STR VAR3
      LDR VAR2
      STR VAR1
      LDR VAR3
      STR VAR2
      JMP LOOP
VAR1: #0
VAR2: #1
VAR3: #0
```

Press `Ctrl+S` to compile, then press `T` repeatedly to step through assembly and execution.

---

## 📁 Project Structure

```
CPU_Sim/
├── .design/
│   ├── CIE_specs.md              # Detailed CIE specification notes
│   ├── references.md             # list of curriculum points illustrated
│   ├── review_pointers.md        # Code review guidelines
│   └── review.md                 # Code review results
├── assembler/
│   └── assembler.py              # Two-pass assembler with stepper
├── common/
│   ├── constants.py              # Shared enums and constants
│   └── instructions.py           # Instruction metadata and RTN sequences
├── cpu/
│   ├── ALU.py                    # Arithmetic Logic Unit
│   ├── buses.py                  # Address and data bus models
│   ├── component.py              # Base component protocol
│   ├── cpu_io.py                 # I/O components (IN/OUT)
│   ├── cpu.py                    # Top-level CPU class
│   ├── CU.py                     # Control Unit (fetch-decode-execute)
│   ├── RAM.py                    # Memory model
│   └── register.py               # Register implementation
├── interface/
│   ├── alu_display.py            # ALU visualization
│   ├── bus_ascii.py              # ASCII-art bus visualization
│   ├── control_unit_display.py   # Control Unit visualization
│   ├── CPUDisplayer.py           # Main CPU display layout
│   ├── instruction_label_display.py # Instruction and variable label tables
│   ├── internal_bus_display.py   # Internal bus visualization
│   ├── IO_display.py             # I/O queue visualization
│   ├── outer_bus_display.py      # External bus visualization
│   ├── ram_display.py            # Memory display widget
│   ├── register_display.py       # Register display widget
│   ├── styles.tcss               # Textual styles
│   ├── TickerController.py       # Stepper control logic
│   ├── variable_label_display.py # Variable label table
│   └── vspacer.py                # vertical spacer widget
├── examples/
│   ├── fibo.txt                  # Example Fibonacci program
│   └── fibo2.txt                 # Additional example
├── tests/
│   └── TODO
├── CIE_CPU_Sim.py                # Application entry point
├── requirements.txt              # Project dependencies
├── LICENSE                       # MIT License
└── README.md                     # This file
```

---

## 🧑‍💻 For Students: Exploring the Code

If you're curious about **how this works under the hood**, the codebase is designed to be readable:

1. **Start with [`assembler/assembler.py`](assembler/assembler.py)**:
   - See how a two-pass assembler resolves labels and generates machine code
   - Notice the stepper pattern: each `step()` call performs one small operation
   - Read the docstrings to understand *why* two passes are needed

2. **Explore [`cpu/CU.py`](cpu/CU.py) (Control Unit)**:
   - Watch how fetch-decode-execute is implemented as a state machine
   - See RTN steps as data (not code)—each step describes *what* should happen
   - Understand the dispatcher pattern: RTN step types → handler methods

3. **Check out [`common/instructions.py`](common/instructions.py)**:
   - Instructions are defined as metadata (opcode, addressing mode, RTN sequence)
   - The Control Unit *interprets* this metadata, just like real hardware

4. **Look at [`cpu/register.py`](cpu/register.py) or [`cpu/ALU.py`](cpu/ALU.py)**:
   - Simple, focused components with clear responsibilities
   - Dataclasses reduce boilerplate while keeping code readable

**Educational notes** throughout the code explain advanced Python features (protocols, decorators, bitwise operations) so you can learn as you go.

---

## 🧪 Testing

TODO

---

## 🛠️ Roadmap (ordered by priority)

- [ ] Add missing documentation(display modules not documented yet)
- [ ] Fix second pass display not highlighting source code lines
- [ ] Fix hotkeys not displaying in footer
- [ ] Allow user to switch between numbering systems
- [ ] Add autorun mode with speed control
- [ ] Allow user to edit Input queue contents
- [ ] Block execution when waiting for IN and Input queue is empty
- [ ] Implement test suite with coverage reports
- [ ] Save/load assembly programs from files

---

## 🤝 Contributing

Contributions are welcome, especially:

- **Bug reports**: If behavior doesn't match CIE specifications
- **Documentation improvements**: Clarifications, examples, or CIE references
- **Test coverage**: Help validate correctness
- **UI enhancements**: Better visualizations or alternative display modes

**Before contributing:**

1. Review [`.design/review_pointers.md`](.design/review_pointers.md) for code review guidelines
2. Ensure changes align with the **educational mission** (clarity over cleverness)
3. Follow the CIE terminology and RTN notation established in existing code

---

## 📖 References

CPU_Sim is based on:

- **Cambridge International AS & A Level 9618 Computer Science syllabus** (2026 examination)
- **SaveMyExams CIE A Level Computer Science Revision Notes**
- **CIE-accredited workbooks and teaching materials**

See [`.design/CIE_specs.md`](.design/CIE_specs.md) for detailed specification notes.

---

## 📜 License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE.txt) for details.

**In summary:** You can use, modify, and distribute this code freely (even commercially) as long as you include the original copyright notice and license.

---

## 🛠️ AI use

This project has utilized AI tools (GitHub Copilot) to assist with code generation and documentation. All AI-generated content has been reviewed and modified by human contributors to ensure accuracy, clarity, and alignment with educational goals.

---

## 🙏 Acknowledgments

- **Cambridge International Examinations** for the excellent syllabus and teaching resources
- **SaveMyExams** for clear, student-friendly explanations of CPU architecture
- **The Python community** for Textual and other open-source libraries that made this possible

---

## ⚡ Quick Start Summary

1. Install Python 3.10+ and dependencies (`pip install -r requirements.txt`)
2. Run `python CIE_CPU_Sim.py`
3. Write or load assembly code in the editor
4. Press `Ctrl+S` to compile, then `T` to step through execution
5. Watch the magic happen! ✨

For questions, issues, or suggestions, please open an issue on GitHub.

---

**Happy learning! 🚀**
