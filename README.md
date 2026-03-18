# Pac-Man Pygame Prototype

## How To Run

1. Open a terminal in this project folder.
2. Install dependencies:

```bash
pip install pygame
```

3. Run the program:

```bash
py preview_map.py
```

## What The Program Currently Does

- Draws a Pac-Man style maze map with pellets.
- Draws a top HUD with score and high score text.
- Draws a bottom HUD with lives shown as Pac-Man icons.
- Lets the Pac-Man sprite move with arrow keys.
- Prevents Pac-Man from moving through walls.
- Spawns enemy sprites in the starting box.
- Keeps all enemy sprites in the starting box for 3 seconds.
- After 3 seconds, all enemy sprites exit the box and roam the maze randomly at a constant speed.
- Prevents enemy sprites from re-entering the starting box while roaming.

## Next Steps

- Allow the Pac-Man sprite to get points as it moves and collects the white dots.
- As Pac-Man collects white dots, those dots should disappear and the points should increase.
- If an enemy sprite hits Pac-Man, Pac-Man loses 1 life.
- If Pac-Man runs out of 3 lives, the game is over.
- If Pac-Man captures the big circles, then for 8 seconds Pac-Man should be able to kill enemy sprites for extra points.
- When an enemy sprite is killed in that state, it should return to the starting box and then exit again after 3 seconds.
- When Pac-Man gets a big circle, enemy sprites should turn blue.

