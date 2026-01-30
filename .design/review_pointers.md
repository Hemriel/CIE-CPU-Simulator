# Code Review Guidelines for CPU_Sim

This document outlines review criteria specific to CPU_Sim. It complements the main [copilot-instructions.md](../../.github/copilot-instructions.md) with a focus on code review practices.

## Guiding Principle

All review decisions must prioritize **clarity and educational value for A-level students reading this codebase**. When in doubt, choose the more explicit, readable approach over cleverness or brevity.

**Examples:**

- Use explicit loops instead of `all()` or `any()` when checking conditions
- Prefer longer variable names that reflect CIE terminology over abbreviations
- Choose straightforward conditional logic over nested ternaries or comprehensions
- Break complex logic into multiple named helper functions rather than single monolithic operations

This does not mean avoiding all advanced Python features—rather, when they are used, they must be clearly explained with comments.

## Documentation Standards

### Module-Level Documentation

Every file must begin with a comprehensive docstring explaining:

1. **Responsibility**: What this module is responsible for (one clear sentence)
2. **Design choices**: Why the code is structured this way, what problems it solves
3. **Entry point(s)**: Which classes or functions form the public API
4. **Contained items**: List of major classes and functions, ordered from high-level to low-level

The file-level docstring should be written for students and should be self-contained enough that a reader understands the module's purpose without jumping to other files.

### Class and Function Documentation

- **Every public class and function** must have a docstring
- Docstrings should be addressed to students and avoid over-technical language
- Include inputs, outputs, and parameters with types (type hints strongly encouraged)
- Explain any non-obvious behavior or assumptions
- For complex algorithms, precede with a comment explaining *why* the approach was chosen

**Example structure:**

```python
def calculate_effective_address(base_address: int, offset: int) -> int:
    """
    Calculate the effective address for indexed addressing mode.
    
    In indexed addressing, the CPU adds an offset (typically held in IX) to a 
    base address to determine where to access memory. This is commonly used 
    when working with arrays or data structures.
    
    Args:
        base_address: The starting memory address
        offset: The index or offset value (e.g., from IX register)
        
    Returns:
        The calculated effective address
    """
```

### Comments Within Code

- Explain **why** code does something, not just **what** it does
- When using unfamiliar Python constructs (e.g., decorators, context managers, metaclasses), add a comment explaining how it works
- For CIE-specific operations, reference the specification (e.g., "CIE 9618 §1.1: PC is incremented after fetch")
- Avoid meta-commentary about the documentation itself (e.g., don't write "this comment explains for students")

## CIE Terminology and Naming Conventions

All code must use CIE terminology consistently. Refer to the [Glossary in copilot-instructions.md](../../.github/copilot-instructions.md#glossary-of-cie-terms-for-consistency) for standard abbreviations and terms.

**Standards:**

- Use full CIE terminology in variable and function names: `program_counter`, `memory_address_register`, `accumulator`, not `pc`, `mar`, `acc`
- Exception: When referring to CIE specifications directly, use the official abbreviations in comments (e.g., "As per CIE 9618, PC is incremented")
- Class names should reflect hardware concepts clearly: `Registers`, `ALU`, `ControlUnit`, `Memory`
- Function names should use verbs describing what happens: `fetch_instruction`, `execute_instruction`, `calculate_flags`

## Code Organization Within Files

Code must be ordered from **high-level to low-level**:

1. Module docstring and imports
2. Constants and type definitions
3. Public classes (with public methods first, helper methods after)
4. Private helper functions and classes
5. End-of-file utility functions

Within each class:

1. `__init__` and public interface methods
2. High-level operation methods (e.g., `execute_instruction`)
3. Intermediate helper methods (e.g., `_load_operand`)
4. Low-level utility methods (e.g., `_update_flags`)

This ordering allows readers to understand the module's purpose by reading from top to bottom without jumping around.

## Type Hints

Type hints should be used throughout the codebase for clarity:

- Function parameters and return types should have type hints
- Class attributes should have type hints (preferably in `__init__`)
- Use descriptive types: prefer `int` over vague types; use custom types or TypedDict for structured data
- Type hints serve as documentation and help students understand expected data flows

**Example:**

```python
def fetch_instruction(self) -> int:
    """Fetch the instruction at the current PC address."""
```

## Function Design and Complexity

- **Keep functions short**: Complex operations should be under 50 lines. Break them into named helper functions with their own docstrings.
- **Single responsibility**: Each function should do one thing well. If a function performs multiple distinct operations, split it into helpers.
- **Readability over cleverness**: Avoid one-liners or overly compact code at the expense of clarity. A three-line explicit loop is better than a nested list comprehension.

**Example of good breakdown:**

```python
def execute_load_instruction(self, operand: int) -> None:
    """Execute a LDR (load) instruction."""
    effective_address = self._calculate_effective_address(operand)
    self._fetch_data_from_memory(effective_address)
    self._store_in_accumulator()

def _calculate_effective_address(self, operand: int) -> int:
    """Calculate effective address based on addressing mode."""
    # Implementation details

def _fetch_data_from_memory(self, address: int) -> None:
    """Load data from memory at the given address."""
    # Implementation details
```

## Avoiding Repetition (Without Sacrificing Clarity)

Although code should avoid unnecessary repetition, **clarity takes priority**:

- Light repetition across different modules is acceptable if it allows students to read each module independently without juggling files
- Repetition of documentation (explaining the same concept multiple times) is acceptable and often beneficial
- Use abstraction and helper functions to reduce implementation repetition, but don't over-engineer shared code if it obscures purpose

**Example:** A detailed explanation of how indexed addressing works in both the assembler and CPU modules is better than a single shared function that confuses both contexts.

## CIE Specification Alignment

Every significant feature must be traceable back to [.design/CIE specs.md](CIE%20specs.md):

- Variable and function names should use CIE terminology
- Algorithms (fetch-decode-execute, two-pass assembly, addressing modes) must match CIE specifications exactly
- Comments should reference relevant sections of the CIE 9618 syllabus where applicable
- Register behavior, instruction set, and memory model must follow CIE definitions

**Example comment:**

```python
# CIE 9618 §1.1: PC is incremented after instruction fetch
self.program_counter += 1
```

## Design Patterns and Architecture

Code should implement the design patterns specified in the project documentation:

- **Instruction as Data for Control**: Instruction metadata should describe control signals, not encapsulate behavior
- **Register Transfer Notation (RTN)**: CPU operations should be modeled as explicit register transfers (e.g., `MAR ← PC`)
- **Strategy Pattern for Addressing Modes**: Different addressing modes should be pluggable and independently tested
- **State Machine for Fetch-Decode-Execute**: CPU execution should have explicit states (fetch → decode → execute)

When implementing these patterns, include comments explaining which pattern is being used and why.

## Testing and Validation

Code reviews should verify:

- **Specification compliance**: Does behavior match CIE 9618 specifications?
- **Real world equivalence**: When CIE specifications don't specify behavior, match real world behavior as much as possbile.
- **Mark scheme alignment**: For complex operations, verify against published CIE mark schemes
- **Test coverage**: Complex logic should have corresponding tests with documented expected behavior
- **Student-friendly test cases**: Test names and assertions should be understandable to A-level learners

## UI/Visual Consistency

For interface code:

- ASCII-art elements (buses, tables, diagrams) should be consistent in style across the UI
- Color usage should follow a consistent scheme (document the palette if using colors)
- Panel layouts should follow the hierarchy: assembly editor → register/memory state → bus visualization → execution controls
- Visual animations should clearly correspond to RTN steps in the CPU cycle

---

**Last Updated**: January 2026  
**Audience**: Code reviewers, contributors  
**Scope**: Code review practices for CPU_Sim
