# Pac-Man Pygame Prototype

Received from Phase1 from https://github.com/CodingGenius14/15-113-Week-8.
> ## How To Run
>
> 1. Open a terminal in this project folder.
> 2. Install dependencies:
>
> ```bash
> pip install pygame
> ```
>
> 3. Run the program:
>
> ```bash
> py preview_map.py # or python3 preview_map.py
> ```
>
> ## What The Program Currently Does
>
> - Draws a Pac-Man style maze map with pellets.
> - Draws a top HUD with score and high score text.
> - Draws a bottom HUD with lives shown as Pac-Man icons.
> - Lets the Pac-Man sprite move with arrow keys.
> - Prevents Pac-Man from moving through walls.
> - Spawns enemy sprites in the starting box.
> - Keeps all enemy sprites in the starting box for 3 seconds.
> - After 3 seconds, all enemy sprites exit the box and roam the maze randomly at a constant speed.
> - Prevents enemy sprites from re-entering the starting box while roaming.
>
> ## Next Steps
>
> - Allow the Pac-Man sprite to get points as it moves and collects the white dots.
> - As Pac-Man collects white dots, those dots should disappear and the points should increase.
> - If an enemy sprite hits Pac-Man, Pac-Man loses 1 life.
> - If Pac-Man runs out of 3 lives, the game is over.
> - If Pac-Man captures the big circles, then for 8 seconds Pac-Man should be able to kill enemy sprites for extra points.
> - When an enemy sprite is killed in that state, it should return to the starting box and then exit again after 3 seconds.
> - When Pac-Man gets a big circle, enemy sprites should turn blue.
>
> ——————————————————————————end of received from Phase1
Start from Phase 2: 
## Improvement Roadmap (Append-Only)

This section extends the current `Next Steps` with priority, implementation hints, and testable outcomes.

### P0 - Core Playable Loop

1. Pellet collection and scoring
   - Implementation hint:
     - Keep a mutable pellet state (for example a `set[(row, col)]`) built from `MAZE_LAYOUT`.
     - On each frame, map Pac-Man center to tile coordinates and remove pellet tile when entered.
     - Increase score for normal pellets and power pellets separately.
   - Acceptance:
     - Entering a pellet tile removes that pellet visually.
     - Score value in HUD increases immediately.

2. Ghost collision and life loss
   - Implementation hint:
     - Check Pac-Man vs ghost distance each frame.
     - In normal state, collision consumes one life and triggers a short reset (Pac-Man and ghosts return to spawn).
   - Acceptance:
     - Colliding with any ghost removes exactly 1 life.
     - Player and ghosts reset to start positions after hit.

3. Game over state
   - Implementation hint:
     - Add a game state enum/string (`playing`, `life_lost`, `game_over`).
     - Stop movement updates when `game_over` and display restart prompt.
   - Acceptance:
     - At 0 lives, gameplay freezes and game-over text is shown.
     - Restart key creates a clean new run.

### P1 - Classic Pac-Man Mechanics

1. Power mode (8 seconds) and frightened ghosts
   - Implementation hint:
     - Track `power_mode_until` timestamp.
     - While active, ghosts switch to frightened color and become vulnerable.
   - Acceptance:
     - Eating a power pellet turns ghosts blue for about 8 seconds.
     - After timeout, ghosts return to normal behavior and color.

2. Ghost eaten behavior and box return
   - Implementation hint:
     - Add ghost states such as `frightened`, `eaten_returning`, `in_box`, `exiting`, `roaming`.
     - On collision during power mode, mark ghost as eaten, route it back to box, then release again after delay.
   - Acceptance:
     - During power mode, Pac-Man can eat ghosts for bonus points.
     - Eaten ghosts return to ghost house and rejoin roaming after release.

3. Combo ghost scoring during one power window
   - Implementation hint:
     - Use a per-power-cycle multiplier sequence (200, 400, 800, 1600).
     - Reset combo index when power mode ends.
   - Acceptance:
     - Consecutive ghost eats in one power window award increasing points.

### P2 - Game Feel and Reliability

1. Round clear condition
   - Implementation hint:
     - Track total remaining pellets and transition to `round_clear` when zero.
   - Acceptance:
     - Clearing all pellets shows a round-clear message or advances to next round.

2. Better controls and flow
   - Implementation hint:
     - Buffer next intended direction so turns happen automatically when path opens.
     - Add pause (`P`) and restart (`R`) controls.
   - Acceptance:
     - Inputs feel responsive at intersections.
     - Pause and restart are always available.

3. Difficulty scaling
   - Implementation hint:
     - Increase ghost speed and reduce frightened duration gradually per round.
   - Acceptance:
     - Later rounds feel harder without breaking collision logic.

### Known Technical Enhancements

- Split `preview_map.py` into focused modules:
  - `entities.py` (Pac-Man and ghost state)
  - `systems.py` (movement, collision, scoring, state transitions)
  - `render.py` (HUD and sprite drawing)
  - `game.py` (main loop and high-level orchestration)
- Add a lightweight testable logic layer (pure functions for tile checks, scoring, collisions) so core rules can be validated without rendering.
- Keep rendering and gameplay state updates decoupled to avoid regressions when adding new behaviors.

## Movement Bug Fix Notes (Append-Only)

Observed issue:
- Pac-Man could occasionally clip into wall corners and appear stuck when turning near intersections.

What changed:
- Added buffered input for Pac-Man direction, so turn intent is remembered briefly.
- Added tile-center snapping and axis alignment during movement to keep Pac-Man centered in corridors.
- Added a movement update routine that prioritizes valid buffered turns at tile centers and allows safe reverse turns.

Why this fixes the problem:
- The previous movement could leave Pac-Man slightly off-center, which increases corner collision risk.
- The new movement keeps Pac-Man aligned to grid lanes, so path checks stay consistent and wall clipping is avoided.

Player-visible result:
- Pac-Man now turns more reliably at intersections.
- Pac-Man can traverse full tiles/corridors without randomly getting stuck in walls.

## Movement Fix Follow-Up (Append-Only)

Additional bug found:
- A too-large center-snap threshold could snap Pac-Man back toward tile center every frame, making movement look stuck.

Follow-up adjustment:
- Reduced the snap threshold to a tight value so snapping only happens when truly near center.
- Kept buffered turning and lane alignment, but removed the repeated pull-back effect.

Result:
- Pac-Man can move continuously through corridors again.
- Turning assistance remains active without freezing movement.

## Gameplay Completion Update (Append-Only)

This section documents the newly completed game-loop features without changing prior content.

### Completed in `preview_map.py`

- Pellet state is now mutable during play:
  - Pellets are initialized from `MAZE_LAYOUT` once per run.
  - When Pac-Man enters a pellet tile, that pellet is removed and no longer drawn.
- Scoring is now active:
  - Normal pellet (`0`) = +10 points
  - Power pellet (`3`) = +50 points
  - Eating a ghost during power mode = +200 points
  - Getting hit by a ghost in normal mode = -200 points (not below 0)
- Life and collision rules are now active:
  - Pac-Man starts with 3 lives.
  - Collision with a ghost (outside power mode) costs 1 life and resets positions.
  - At 0 lives, the game enters `GAME OVER`.
- Power pellet mode is implemented:
  - Eating a power pellet enables an 8-second power window.
  - During this time ghosts turn blue and can be eaten by Pac-Man.
  - Eaten ghosts are sent back to the ghost box and released again after 3 seconds.
- Round clear condition is implemented:
  - When all pellets are consumed, the game shows a `YOU WIN!` message.
- Restart flow is implemented:
  - Press `R` to restart from a clean state (score/lives/pellets/positions reset).

### Map Rendering Support Added in `map_layout.py`

- Added a mutable pellet builder utility (`build_pellet_tiles`) to generate pellet tile sets from layout data.
- Extended `draw_map(...)` to accept an optional pellet-tile set so consumed pellets disappear visually during gameplay.

## Power Pellet Score Fix (Append-Only)

- Fixed power-pellet scoring so large pellets always award more points than normal pellets.
- Updated scoring values:
  - Normal pellet (`0`) = +10 points
  - Power pellet (`3`) = +100 points
- Implementation detail:
  - Added dedicated power-pellet tile tracking in gameplay state.
  - Pellet consumption now checks this dedicated set directly, ensuring power pellets never fall back to normal score.

## Info Button and Pause Popup (Append-Only)

- Added an `INFO` button at the top HUD area.
- Clicking `INFO` toggles an in-game help popup.
- When the popup is open, gameplay updates are paused (Pac-Man and ghosts stop advancing).
- Popup content includes:
  - Key bindings and operation guide
  - Basic objective and power-pellet behavior
  - Author credit text:
    - `Vikram Oberai and Jack Yu. Made with help of AI.`
- Additional controls:
  - `I` toggles popup open/close
  - `ESC` closes popup when open

## Info Popup Layout and Continue Button (Append-Only)

- Improved info popup text layout to prevent long guide lines from overflowing the panel.
- Added a visible `CONTINUE` button inside the popup:
  - Click `CONTINUE` to close the popup and resume gameplay.
- Added keyboard shortcut:
  - Press `C` (when popup is open) to continue gameplay.

## Future Feature Suggestions (Append-Only)

- Add classic tunnel wrap-around on left/right map edges for authentic Pac-Man movement.
- Add ghost personality behaviors (chase/scatter targets per ghost) for deeper gameplay.
- Add level progression with increasing ghost speed and shorter power duration each round.
- Add combo scoring for consecutive ghost captures within one power-pellet window.
- Add start menu, pause menu, and settings (volume, key rebinding, difficulty presets).
- Add sound effects/music and simple animation polish (waka timing, ghost eyes direction, death animation).
- Add persistent high-score save/load to local file.
- Split game logic into modules (`entities`, `systems`, `ui`, `main`) to improve maintainability.
- Add lightweight automated tests for collision, scoring, and state transitions.
