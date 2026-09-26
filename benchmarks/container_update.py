"""Array construction, indexed updates and checksum benchmark equivalent."""


SIZE = 4000
ROUNDS = 6


values = []
i = 0
while i < SIZE:
    values.append((i * 17 + 3) % 1000)
    i = i + 1

round_number = 0
while round_number < ROUNDS:
    i = 0
    while i < SIZE:
        values[i] = (values[i] + round_number + i) % 1000
        i = i + 1
    round_number = round_number + 1

checksum = 0
i = 0
while i < SIZE:
    checksum = checksum + values[i]
    i = i + 1
print("container:", checksum, len(values), values[0], values[SIZE - 1])
