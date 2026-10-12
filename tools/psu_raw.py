from instruments.spd3303c import *
import sys


with SPD3303C() as psu:

    print(psu.identify())

    while True:
        command = input("SCPI> ").strip()

        if not command:
            continue

        if command.lower() in ("exit", "quit"):
            break

        try:
            if "?" in command:
                print(repr(psu.query(command)))
            else:
                psu.write(command)
                print("OK")

        except Exception as e:
            print(f"ERROR: {e}")
