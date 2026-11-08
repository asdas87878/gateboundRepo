"""The bridge house's numbers, studs: shared by its timber (bridgehouse_kit.py) and its stone (bridgehouse_stone.py). The street runs along z, under the arch."""
R = 4.6  # half the passage, and the arch's inner radius
SPRING = 5.0
RING = 1.3
Y0 = SPRING + R + RING + 0.65  # the floor: its beam clears the keystone
PIER_W = 5.0
XO = R + PIER_W  # the piers' outer face
ZS = 5.6  # half the stone's depth
STAIR_W = 3.2
STEP_H, STEP_Z = 0.8, 0.85
LANDING_Z = 0.6
BACK = -6.65  # the landing's back edge
STEPS = int(round(Y0 / STEP_H))
Z_END = LANDING_Z + STEPS * STEP_Z
