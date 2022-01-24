from datetime import datetime
from math import sqrt
import os
import pyautogui as pt
import re
import sys
from time import sleep


'''
CROUCH_SPEED = 1.31 # blocks per second
WALK_SPEED = 4.317 # blocks per second
SPRINT_SPEED = 5.612 # blocks per second

DIAGONAL_CROUCH_SPEED = sqrt(pow(CROUCH_SPEED, 2) * 2)
DIAGONAL_WALK_SPEED = sqrt(pow(WALK_SPEED, 2) * 2)
DIAGONAL_SPRINT_SPEED = sqrt(pow(SPRINT_SPEED, 2) + pow(WALK_SPEED, 2)) # only sprints in one direction
'''

LOGIC_GATES = ['NOT', 'OR', 'NOR', 'AND', 'NAND', 'XOR', 'XNOR']
NATIVE_INSTRUCTIONS = LOGIC_GATES + ['INPUT', 'OUTPUT']


def find_by_condition(func, array):
    # Finds all indexes and values in array that pass func
    found = list(filter(lambda x: func(x[1]), enumerate(array)))
    return found


def get_key_index(key, dictionary):
    # Gets the index (number) of a key in a dictionary
    return list(dictionary).index(key)


def back_to_game():
    # Clicks on the back to game button
    position = pt.locateCenterOnScreen('images/back_to_game_normal.png') \
               or pt.locateCenterOnScreen('images/back_to_game_highlighted.png')

    if position is not None:
        pt.moveTo(int(position.x / 2), int(position.y / 2))
        pt.click()
    else:
        print('Back to game button was not found.')
        exit()


def send_chat_message(message, command=False):
    pt.press('/' if command else 't')
    pt.write(message + '\n')


def format_coordinates(x, y, z):
    # Format coordinates as minecraft relative coordinates
    return f'~{x if x != 0 else ""} ~{y if y != 0 else ""} ~{z if z != 0 else ""}'


def set_block(x, y, z, block, variant=0):
    send_chat_message(f'setblock {format_coordinates(x, y, z)} {block} {variant}', command=True)


def set_sign(x, y, z, direction, texts, wall_sign=False):
    sign_text_json = ''
    for i, text in enumerate(texts):
        if text != '':
            sign_text_json += f',Text{i + 1}:"{text}"'
    send_chat_message(f'setblock {format_coordinates(x, y, z)} {"wall_sign" if wall_sign else "standing_sign"} {direction} replace ' + '{' + f'id:"Sign"{sign_text_json}' + '}', command=True)


def fill(x1, y1, z1, x2, y2, z2, block, variant=0):
    send_chat_message(f'fill {format_coordinates(x1, y1, z1)} {format_coordinates(x2, y2, z2)} {block}{" " + variant if variant != 0 else ""}', command=True)


main_lines = {}
secondary_lines = {}

components = {}
custom_var_counter = 0

with open(sys.argv[1], 'r') as f:
    raw_code = re.sub(r'//.*$', '', f.read(), 0, re.MULTILINE) # removes comments

components_part, instructions_part = raw_code.split('-----')

# load pre-made components
for file_path in os.listdir('component_libs'):
    with open(os.path.join('component_libs', file_path), 'r') as f:
        components_part = f.read() + components_part

component_matches = re.finditer(r'^([A-Z0-9_]+)\s+{((?:.|\s)*?)}', components_part, re.MULTILINE)

# for each component function
for component_match in component_matches:
    component_name = component_match.group(1)

    component_instructions = map(lambda x: x.strip(), component_match.group(2).strip().split('\n'))
    component_instructions = map(lambda x: x.split(' '), component_instructions)
    component_instructions = map(lambda x: x[:1] + [x[1].split(':')] + x[2:], component_instructions)
    component_instructions = list(component_instructions)

    # find each call to the component function in the main code
    component_instruction_matches = re.finditer(rf'^[ \t]*{component_name}\s+(.+?)\s+(.+?)$', instructions_part, re.MULTILINE)
    for component_instruction_match in component_instruction_matches:
        input_names = component_instruction_match.group(1).split(':')
        output_name = component_instruction_match.group(2)

        # and replace it with the function
        # TODO: make it so all variables are unique throughout the code, otherwise it can create problems
        component_vars = {}
        new_instructions = ''
        for component_instruction in component_instructions:
            # create the new instruction, replacing variable names
            new_instructions += component_instruction[0]
            
            # input vars
            new_inputs = []
            for component_var in component_instruction[1]:
                if component_var == '$$':
                    new_inputs.append(output_name)
                elif component_var[0] == '$':
                    new_inputs.append(input_names[int(component_var[1:])])
                else: # it's a local component function variable
                    if component_var not in component_vars:
                        component_vars[component_var] = f'{component_var}#{custom_var_counter}'
                        custom_var_counter += 1
                    new_inputs.append(component_vars[component_var])

            new_instructions += ' ' + ':'.join(new_inputs) + ' '

            # output vars
            if len(component_instruction) == 3:
                component_var = component_instruction[2]
                # TODO: make this DRY
                if component_var == '$$':
                    new_instructions += output_name
                elif component_var[0] == '$':
                    new_instructions += input_names[int(component_var[1:])]
                else: # it's a local component function variable
                    if component_var not in component_vars:
                        component_vars[component_var] = f'{component_var}#{custom_var_counter}'
                        custom_var_counter += 1
                    new_instructions += component_vars[component_var]
            
            new_instructions += '\n'

        instructions_part = re.sub(component_instruction_match.group(0), new_instructions, instructions_part, 0, re.MULTILINE)

# turn instructions into a list
instructions = list(filter(lambda line: line != '', instructions_part.split('\n')))

for instruction in instructions:
    # add a redstone line for every output
    args = instruction.split()
    
    main_lines[args[-1]] = {
        'name': args[-1],
        #'inputs': args[1].split(':') if args[0] in LOGIC_GATES else None,
        'type': 'input' if args[0] == 'INPUT' else 'gate_output' if args[0] in LOGIC_GATES else 'display_output' if args[0] == 'OUTPUT' else None,
        # unknown start and end
        'start': 0,
        'end': 0
    }

    if args[0] in LOGIC_GATES:
        secondary_lines[args[-1]] = {
            'name': args[-1],
            'gate': args[0],
            'inputs': args[1].split(':'), # can't be None
            # unknown start and end
            'start': 0,
            'end': 0
        }

# make the secondary lines
for instruction in instructions:
    # TODO: fit secondary lines one after another

    args = instruction.split()
    instruction_name = args[0]
    output_name = args[-1]

    if instruction_name in LOGIC_GATES:
        inputs = secondary_lines[output_name]['inputs']

        #for i, _ in enumerate(inputs):
            # 2 blocks for each gate
        #    main_lines[i]['end'] += 2

        possible_main_line_indexes = []
        for inp in inputs + [output_name]:
            found_index = find_by_condition(lambda m: m == inp, main_lines)[0][0]
            possible_main_line_indexes.append(found_index)

        # create a secondary line connecting all the inputs and the output main line
        secondary_lines[output_name]['start'] = min(possible_main_line_indexes)
        secondary_lines[output_name]['end'] = max(possible_main_line_indexes)

# make the main lines connect all of the secondary lines
for m in main_lines:
    possible_secondary_lines = find_by_condition(lambda s: m == s or m in secondary_lines[s]['inputs'], secondary_lines)
    if len(possible_secondary_lines) > 0:
        main_lines[m]['start'] = min(possible_secondary_lines)[0]
        main_lines[m]['end'] = max(possible_secondary_lines)[0]

sleep(3)

back_to_game()

pt.keyUp('command') # reset the command key just in case
pt.keyUp('shift') # reset the shift key just in case

send_chat_message(f'Started at {datetime.now()}')
send_chat_message('gamemode sp', command=True)
send_chat_message('gamerule doTileDrops false', command=True) # make it not drop the items when editing the lines

# Make the main lines
for i, m in enumerate(main_lines):
    fill(i * 2, 0, main_lines[m]['start'] * 2 - 1, i * 2, 0, main_lines[m]['end'] * 2 + 2, 'wool')
    fill(i * 2, 1, main_lines[m]['start'] * 2 - 1, i * 2, 1, main_lines[m]['end'] * 2 + 2, 'redstone_wire')
    set_sign(i * 2, 0, main_lines[m]['start'] * 2 - 2, 2, ['', m, '', ''], wall_sign=True) # adds the sign

    if main_lines[m]['type'] == 'input':
        set_block(i * 2, 2, main_lines[m]['start'] * 2 - 1, 'redstone_lamp')
        set_block(i * 2, 2, main_lines[m]['start'] * 2 - 2, 'lever', 4)
    elif main_lines[m]['type'] == 'display_output':
        set_block(i * 2, 1, main_lines[m]['end'] * 2 + 2, 'redstone_lamp')
    elif main_lines[m]['type'] == 'gate_output':
        pass


# Make the secondary lines
for i, s in enumerate(secondary_lines):
    fill(secondary_lines[s]['start'] * 2, -2, i * 2, secondary_lines[s]['end'] * 2, -2, i * 2, 'wool', '14')
    fill(secondary_lines[s]['start'] * 2, -1, i * 2, secondary_lines[s]['end'] * 2, -1, i * 2, 'redstone_wire')

    output_main_line_index = get_key_index(s, main_lines)

    # Make the ending (output) from secondary line to main line
    if secondary_lines[s]['gate'] in ['NOT', 'OR', 'NAND']:
        # Put a repeater into the output line
        set_block(output_main_line_index * 2 - 1, -1, i * 2, 'unpowered_repeater', '1')
        set_block(output_main_line_index * 2, -1, i * 2, 'wool')
        set_block(output_main_line_index * 2, 0, i * 2, 'redstone_wire')

    elif secondary_lines[s]['gate'] in ['AND', 'NOR']:
        set_block(output_main_line_index * 2, -1, i * 2, 'wool', '14')
        set_block(output_main_line_index * 2, 0, i * 2, 'redstone_torch')
        set_block(output_main_line_index * 2, 1, i * 2, 'wool')
        set_block(output_main_line_index * 2, 2, i * 2, 'redstone_wire')

    # Make the inputs from main lines to secondary line
    if secondary_lines[s]['gate'] in ['NOT', 'AND', 'NAND']:
        # Put a torch over the secondary line
        for input_main_line in secondary_lines[s]['inputs']:
            input_main_line_index = get_key_index(input_main_line, main_lines)
            set_block(input_main_line_index * 2 + 1, 0, i * 2, 'redstone_torch', '1')

    elif secondary_lines[s]['gate'] in ['OR', 'NOR']:
        # Put repeater into the secondary line
        # TODO: fix when two are next to each other
        for input_main_line in secondary_lines[s]['inputs']:
            input_main_line_index = get_key_index(input_main_line, main_lines)
            set_block(input_main_line_index * 2, -1, i * 2 + 1, 'wool')
            set_block(input_main_line_index * 2, 0, i * 2 + 1, 'unpowered_repeater')
            fill(input_main_line_index * 2, 1, i * 2,
                 input_main_line_index * 2, 1, i * 2 + 1,
                 'wool')
            fill(input_main_line_index * 2, 2, i * 2,
                 input_main_line_index * 2, 2, i * 2 + 1,
                 'redstone_wire')

    # TODO: add the gate-specific endings of the line
        # find the index of the main line of the output
        # connect to it

send_chat_message('gamerule doTileDrops true', command=True)
send_chat_message(f'Ended at {datetime.now()}')
send_chat_message('gamemode c', command=True)

