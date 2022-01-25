# Documentation

## Setting up minecraft

In order to use this tool, you must be in minecraft 1.8.9, in creative mode, with access to vanilla commands.

Move to where you want to build the redstone build in the world, then enter the pause screen and start the program.

## Running

You must be using python3.

Install the required dependencies:

```py
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Run your code:

```py
python3 main.py /path/to/your/circuit.txt
```

Example:

```py
python3 main.py circuits/xor.py
```

## Syntax

Each program is in two sections:
- First the components section
- Then the instructions section

The sections must be separated by `-----` (5 hyphens), even if one of the sections is empty.

Comments can be made using `//`.

### Components

In order to create a component in the components section, use this syntax:

```
COMPONENT_NAME {
  // instructions here
  // in order to access the inputs, use $ then the index (starting at 0)
  // in order to return a value into the ouput, use $$
}
```

Example:

```
// this component is in the standard library (no need to make it)
XOR {
  AND $0:$1 c
  NOR $0:$1 d
  NOR c:d $$  // this returns it into the provided output variable
}
```

The components are then used in the instructions section.

#### Standard library

Components in the standard library are:
- XOR
- XNOR

The standard library can be found in the `component_libs/` folder.

### Instructions

Each instruction must start with its name, followed by a list of inputs separated by `:` (colons).

Some instructions may also require an output.

In order to use components, call them the same way.

Native instructions are:
- INPUT
- OUTPUT (work in progress)
- NOT 
- OR
- NOR
- AND
- NAND

Example:

```
INPUT a     // this creates a user input line
INPUT b

NOT a a*    // this puts NOT a into the new variable a*
AND a*:b c  // this puts (a* AND b) into the new variable c

XOR c:a d   // this calls the XOR component from the standard library and puts (a XOR c) into the new variable d
```
