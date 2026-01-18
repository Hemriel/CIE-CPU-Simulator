
from time import sleep


def cpu_test(machine_code: list[int] | None = None):
    from cpu.cpu import CPU
    cpu = CPU()
    print("CPU initialized with components:")
    for name, component in cpu.components.items():
        print(f"{name}: {component}")
    if machine_code is None:
        with open("fibo.bin", "r") as f:
            program = [int(line.strip(), 16) for line in f.readlines()]
    else:
        program = machine_code
    cpu.load_program(program)
    print("Program loaded into RAM.")
    ram_contents = [cpu.ram.memory[addr] for addr in range(len(program))]
    print("RAM Contents:")
    for addr, word in enumerate(ram_contents):
        print(f"Address {addr:04X}: {word:04X}")
    print(cpu)
    while not cpu.step():
        print(cpu)
    print("Program execution finished.")
    print("fibonacci results:")
    for i in range(20):
        print(f"fib({i}) = {cpu.ram.memory.get(i+200)}")

def assembler_test():
    from assembler.assembler import assemble
    with open("fibo2.txt", "r") as f:
        source_code = f.read()
    machine_code = assemble(source_code.splitlines())
    with open("fibo2.bin", "w") as f:
        f.write("\n".join(f"{word:04X}" for word in machine_code))
    print("Assembled Machine Code:")
    for addr, word in enumerate(machine_code):
        print(f"Address {addr:04X}: {word:04X}")
    return machine_code

if __name__ == "__main__":
    machine_code = assembler_test()
    cpu_test(machine_code)