def get_current_duck() -> str:
    with open('./db/last_duck.txt') as f:
        current_duck = f'{int(f.read()) + 1}'
    with open('./db/last_duck.txt', 'w') as f:
        f.write(current_duck)
    return current_duck


def get_current_dft_number() -> str:
    with open('./db/last_dft.txt') as f:
        current_dft = f'{int(f.read()) + 1}'
    with open('./db/last_dft.txt', 'w') as f:
        f.write(current_dft)
    return current_dft
