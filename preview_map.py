"""Playable Pac-Man map preview with HUD, player movement, and roaming ghosts.

Current behavior:
- Renders the custom maze, pellets, score bar, and lives icons.
- Allows Pac-Man movement with arrow keys (only while a key is held).
- Spawns four ghosts in the starting box.
- After 3 seconds, all ghosts exit the box and roam randomly.
- Once roaming, ghosts cannot re-enter the starting box.
"""

from __future__ import annotations

from dataclasses import dataclass
import random
import sys

import pygame

from map_layout import MAZE_LAYOUT, MAP_HEIGHT, MAP_WIDTH, TILE_SIZE, draw_map, tile_center

# Layout constants
HUD_TOP = 56
HUD_BOTTOM = 56
SCREEN_WIDTH = MAP_WIDTH
SCREEN_HEIGHT = HUD_TOP + MAP_HEIGHT + HUD_BOTTOM

# Colors
BG_COLOR = (0, 0, 0)
TEXT_COLOR = (245, 245, 245)
YELLOW = (255, 220, 0)

# Speeds and timing
PACMAN_SPEED = 3
GHOST_SPEED = 2
GHOST_RELEASE_DELAY_SEC = 3.0

# Movement vectors
DIR_NONE = pygame.Vector2(0, 0)
DIR_LEFT = pygame.Vector2(-1, 0)
DIR_RIGHT = pygame.Vector2(1, 0)
DIR_UP = pygame.Vector2(0, -1)
DIR_DOWN = pygame.Vector2(0, 1)
ALL_DIRS = [DIR_LEFT, DIR_RIGHT, DIR_UP, DIR_DOWN]

# Tile legend values used by movement checks
WALL_TILE = "1"
GHOST_BOX_TILE = "2"


@dataclass
class Ghost:
    """Simple ghost state used by the roaming AI."""

    position: pygame.Vector2
    color: tuple[int, int, int]
    direction: pygame.Vector2
    state: str  # in_box, exiting, roaming


def draw_pacman(
    surface: pygame.Surface,
    center: tuple[int, int],
    radius: int,
    mouth_angle_deg: float = 35,
    direction: float = 0,
) -> None:
    """Draw Pac-Man as a circle with a triangular mouth cutout."""
    pygame.draw.circle(surface, YELLOW, center, radius)

    mouth_half_angle = mouth_angle_deg / 2
    angle1 = direction + mouth_half_angle
    angle2 = direction - mouth_half_angle
    base = pygame.math.Vector2(1, 0)

    p1 = center
    p2 = (
        center[0] + int(radius * base.rotate(angle1).x),
        center[1] - int(radius * base.rotate(angle1).y),
    )
    p3 = (
        center[0] + int(radius * base.rotate(angle2).x),
        center[1] - int(radius * base.rotate(angle2).y),
    )
    pygame.draw.polygon(surface, BG_COLOR, [p1, p2, p3])


def draw_ghost(
    surface: pygame.Surface,
    center: tuple[int, int],
    color: tuple[int, int, int],
    radius: int,
) -> None:
    """Draw a basic ghost body with eyes."""
    body_width = radius * 2
    body_height = int(radius * 2.2)
    left = center[0] - radius
    top = center[1] - radius

    pygame.draw.circle(surface, color, (center[0], top + radius), radius)
    pygame.draw.rect(surface, color, (left, top + radius, body_width, body_height - radius))

    foot_r = max(2, radius // 3)
    for i in range(4):
        foot_x = left + foot_r + i * (body_width // 3)
        foot_y = top + body_height
        pygame.draw.circle(surface, BG_COLOR, (foot_x, foot_y), foot_r)

    eye_r = max(2, radius // 4)
    pupil_r = max(1, eye_r // 2)
    eye_y = top + radius
    left_eye_x = center[0] - radius // 3
    right_eye_x = center[0] + radius // 3
    pygame.draw.circle(surface, (255, 255, 255), (left_eye_x, eye_y), eye_r)
    pygame.draw.circle(surface, (255, 255, 255), (right_eye_x, eye_y), eye_r)
    pygame.draw.circle(surface, (0, 90, 255), (left_eye_x + 1, eye_y), pupil_r)
    pygame.draw.circle(surface, (0, 90, 255), (right_eye_x + 1, eye_y), pupil_r)


def draw_hud(surface: pygame.Surface, score: int, high_score: int, lives: int) -> None:
    """Draw top score bar and bottom lives bar."""
    font = pygame.font.SysFont("consolas", 28, bold=True)
    small_font = pygame.font.SysFont("consolas", 24, bold=True)

    score_text = font.render(f"SCORE {score:05d}", True, TEXT_COLOR)
    high_text = font.render(f"HIGH SCORE {high_score:05d}", True, TEXT_COLOR)
    surface.blit(score_text, (20, 12))
    surface.blit(high_text, (SCREEN_WIDTH - high_text.get_width() - 20, 12))

    bottom_y = HUD_TOP + MAP_HEIGHT + 14
    lives_text = small_font.render("LIVES", True, TEXT_COLOR)
    surface.blit(lives_text, (20, bottom_y + 2))

    for life_index in range(lives):
        icon_center = (110 + life_index * 34, bottom_y + 16)
        draw_pacman(surface, icon_center, 11, mouth_angle_deg=35, direction=0)


def create_ghosts() -> list[Ghost]:
    """Create ghost entities in the starting box."""
    ghost_specs = [
        ((13, 14), (255, 0, 0)),
        ((14, 14), (255, 184, 255)),
        ((12, 15), (0, 255, 255)),
        ((15, 15), (255, 184, 82)),
    ]

    ghosts: list[Ghost] = []
    for (col, row), color in ghost_specs:
        ghosts.append(
            Ghost(
                position=pygame.Vector2(tile_center(col, row, 0, HUD_TOP)),
                color=color,
                direction=random.choice([DIR_LEFT, DIR_RIGHT]),
                state="in_box",
            )
        )
    return ghosts


def draw_ghosts(surface: pygame.Surface, ghosts: list[Ghost], ghost_radius: int) -> None:
    """Render all ghost entities at their current positions."""
    for ghost in ghosts:
        draw_ghost(
            surface,
            (int(ghost.position.x), int(ghost.position.y)),
            ghost.color,
            ghost_radius,
        )


def pacman_direction_from_keys(keys: pygame.key.ScancodeWrapper) -> pygame.Vector2:
    """Return a direction only while an arrow key is actively pressed."""
    if keys[pygame.K_LEFT]:
        return DIR_LEFT
    if keys[pygame.K_RIGHT]:
        return DIR_RIGHT
    if keys[pygame.K_UP]:
        return DIR_UP
    if keys[pygame.K_DOWN]:
        return DIR_DOWN
    return DIR_NONE


def map_cell_from_position(position: pygame.Vector2) -> tuple[int, int]:
    """Convert world position to maze (row, col)."""
    col = int(position.x) // TILE_SIZE
    row = (int(position.y) - HUD_TOP) // TILE_SIZE
    return row, col


def tile_value_at(row: int, col: int) -> str | None:
    """Return map tile value or None when outside map bounds."""
    if row < 0 or row >= len(MAZE_LAYOUT):
        return None
    if col < 0 or col >= len(MAZE_LAYOUT[0]):
        return None
    return MAZE_LAYOUT[row][col]


def can_move_to(center: pygame.Vector2, radius: int, allow_ghost_box: bool = False) -> bool:
    """Check if a circular sprite can occupy the candidate center position."""
    sample_points = [
        (center.x - radius, center.y),
        (center.x + radius, center.y),
        (center.x, center.y - radius),
        (center.x, center.y + radius),
    ]

    for px, py in sample_points:
        if px < 0 or py < HUD_TOP:
            return False

        map_x = int(px)
        map_y = int(py) - HUD_TOP
        col = map_x // TILE_SIZE
        row = map_y // TILE_SIZE
        tile = tile_value_at(row, col)
        if tile is None:
            return False
        if tile == WALL_TILE:
            return False
        if not allow_ghost_box and tile == GHOST_BOX_TILE:
            return False

    return True


def direction_to_mouth_angle(direction: pygame.Vector2) -> float:
    """Map movement direction to Pac-Man mouth angle."""
    if direction == DIR_LEFT:
        return 180
    if direction == DIR_UP:
        return 90
    if direction == DIR_DOWN:
        return -90
    return 0


def reverse_direction(direction: pygame.Vector2) -> pygame.Vector2:
    """Return the opposite direction vector."""
    return pygame.Vector2(-direction.x, -direction.y)


def is_near_tile_center(position: pygame.Vector2, threshold: float = 2.0) -> bool:
    """Check if entity is close enough to grid center to allow random turns."""
    row, col = map_cell_from_position(position)
    tile = tile_value_at(row, col)
    if tile is None:
        return False

    center_x, center_y = tile_center(col, row, 0, HUD_TOP)
    return abs(position.x - center_x) <= threshold and abs(position.y - center_y) <= threshold


def available_directions(
    position: pygame.Vector2,
    radius: int,
    speed: float,
    allow_ghost_box: bool,
) -> list[pygame.Vector2]:
    """Return passable movement directions from current position."""
    choices: list[pygame.Vector2] = []
    for direction in ALL_DIRS:
        if can_move_to(position + direction * speed, radius, allow_ghost_box=allow_ghost_box):
            choices.append(direction)
    return choices


def update_ghosts(
    ghosts: list[Ghost],
    elapsed_sec: float,
    ghost_radius: int,
) -> None:
    """Update ghost states and random roaming behavior.

    Rules:
    - All ghosts stay in-box for the first 3 seconds.
    - After 3 seconds, all ghosts exit upward.
    - After exiting, ghosts roam randomly and cannot re-enter box tiles.
    """
    if elapsed_sec >= GHOST_RELEASE_DELAY_SEC:
        for ghost in ghosts:
            if ghost.state == "in_box":
                ghost.state = "exiting"
                ghost.direction = DIR_UP

    exit_x = tile_center(14, 14, 0, HUD_TOP)[0]
    exit_target_y = tile_center(14, 11, 0, HUD_TOP)[1]

    for ghost in ghosts:
        if ghost.state == "in_box":
            continue

        if ghost.state == "exiting":
            # Step 1: move horizontally inside the box to align with the doorway.
            if abs(ghost.position.x - exit_x) > GHOST_SPEED:
                horizontal_dir = DIR_RIGHT if ghost.position.x < exit_x else DIR_LEFT
                candidate = ghost.position + horizontal_dir * GHOST_SPEED
                if can_move_to(candidate, ghost_radius, allow_ghost_box=True):
                    ghost.position = candidate
                continue

            # Snap to doorway column before moving upward.
            ghost.position.x = exit_x

            # Step 2: move upward out of the box.
            candidate = ghost.position + DIR_UP * GHOST_SPEED
            if can_move_to(candidate, ghost_radius, allow_ghost_box=True):
                ghost.position = candidate

            if ghost.position.y <= exit_target_y:
                ghost.state = "roaming"
                roam_options = available_directions(
                    ghost.position,
                    ghost_radius,
                    GHOST_SPEED,
                    allow_ghost_box=False,
                )
                if roam_options:
                    ghost.direction = random.choice(roam_options)
            continue

        options = available_directions(
            ghost.position,
            ghost_radius,
            GHOST_SPEED,
            allow_ghost_box=False,
        )
        if not options:
            continue

        # If blocked, choose a new random non-reverse direction when possible.
        blocked = not can_move_to(
            ghost.position + ghost.direction * GHOST_SPEED,
            ghost_radius,
            allow_ghost_box=False,
        )
        if blocked:
            non_reverse = [d for d in options if d != reverse_direction(ghost.direction)]
            ghost.direction = random.choice(non_reverse or options)

        # Randomly turn at intersections to keep roaming behavior unpredictable.
        if is_near_tile_center(ghost.position):
            non_reverse = [d for d in options if d != reverse_direction(ghost.direction)]
            turn_pool = non_reverse or options
            if len(turn_pool) > 1 and random.random() < 0.35:
                ghost.direction = random.choice(turn_pool)

        candidate = ghost.position + ghost.direction * GHOST_SPEED
        if can_move_to(candidate, ghost_radius, allow_ghost_box=False):
            ghost.position = candidate


def main() -> None:
    """Run the pygame loop for map preview and movement prototype."""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Pac-Man Map with HUD")
    clock = pygame.time.Clock()

    score = 0
    high_score = 12000
    lives = 3

    pacman_radius = max(10, TILE_SIZE // 2 - 4)
    ghost_radius = pacman_radius + 2

    pacman_position = pygame.Vector2(tile_center(14, 23, 0, HUD_TOP))
    last_facing = DIR_RIGHT

    ghosts = create_ghosts()
    elapsed_sec = 0.0

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        elapsed_sec += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        pressed = pygame.key.get_pressed()
        movement_dir = pacman_direction_from_keys(pressed)
        if movement_dir != DIR_NONE:
            next_position = pacman_position + movement_dir * PACMAN_SPEED
            if can_move_to(next_position, pacman_radius, allow_ghost_box=False):
                pacman_position = next_position
            last_facing = movement_dir

        update_ghosts(ghosts, elapsed_sec, ghost_radius)

        screen.fill(BG_COLOR)
        draw_hud(screen, score, high_score, lives)
        draw_map(screen, 0, HUD_TOP)
        draw_ghosts(screen, ghosts, ghost_radius)
        draw_pacman(
            screen,
            (int(pacman_position.x), int(pacman_position.y)),
            pacman_radius,
            mouth_angle_deg=35,
            direction=direction_to_mouth_angle(last_facing),
        )
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
