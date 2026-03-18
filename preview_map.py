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

from map_layout import (
    MAZE_LAYOUT,
    MAP_HEIGHT,
    MAP_WIDTH,
    NORMAL_PELLET_TILE,
    POWER_PELLET_TILE,
    TILE_SIZE,
    build_pellet_tiles,
    draw_map,
    tile_center,
)

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
POWER_MODE_DURATION_SEC = 8.0

# Scoring
NORMAL_PELLET_POINTS = 10
POWER_PELLET_POINTS = 100
GHOST_EAT_POINTS = 200
HIT_PENALTY_POINTS = 200
START_LIVES = 3

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
    spawn_position: pygame.Vector2
    base_color: tuple[int, int, int]
    direction: pygame.Vector2
    state: str  # in_box, exiting, roaming
    release_time: float


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


def info_button_rect() -> pygame.Rect:
    """Return the clickable INFO button rectangle in the top HUD."""
    return pygame.Rect(SCREEN_WIDTH // 2 - 52, 10, 104, 36)


def info_overlay_panel_rect() -> pygame.Rect:
    """Return panel rectangle used by the info popup."""
    panel_width = 680
    panel_height = 440
    panel_left = (SCREEN_WIDTH - panel_width) // 2
    panel_top = HUD_TOP + (MAP_HEIGHT - panel_height) // 2
    return pygame.Rect(panel_left, panel_top, panel_width, panel_height)


def continue_button_rect() -> pygame.Rect:
    """Return continue button rectangle inside the info popup."""
    panel_rect = info_overlay_panel_rect()
    button_width = 210
    button_height = 46
    return pygame.Rect(
        panel_rect.centerx - button_width // 2,
        panel_rect.bottom - 96,
        button_width,
        button_height,
    )


def draw_info_button(surface: pygame.Surface, active: bool) -> None:
    """Draw a top HUD INFO button that toggles the help popup."""
    rect = info_button_rect()
    fill = (40, 40, 40) if not active else (70, 90, 170)
    border = (230, 230, 230)
    text_color = (255, 255, 255)

    pygame.draw.rect(surface, fill, rect, border_radius=8)
    pygame.draw.rect(surface, border, rect, width=2, border_radius=8)

    font = pygame.font.SysFont("consolas", 22, bold=True)
    text = font.render("INFO", True, text_color)
    surface.blit(text, (rect.centerx - text.get_width() // 2, rect.centery - text.get_height() // 2))


def draw_info_overlay(surface: pygame.Surface) -> None:
    """Draw pause/help popup with controls and credits."""
    shade = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    shade.fill((0, 0, 0, 165))
    surface.blit(shade, (0, 0))

    panel_rect = info_overlay_panel_rect()
    panel_left = panel_rect.left
    panel_top = panel_rect.top

    pygame.draw.rect(surface, (18, 18, 24), panel_rect, border_radius=14)
    pygame.draw.rect(surface, (235, 235, 235), panel_rect, width=2, border_radius=14)

    title_font = pygame.font.SysFont("consolas", 36, bold=True)
    body_font = pygame.font.SysFont("consolas", 23, bold=True)
    foot_font = pygame.font.SysFont("consolas", 20, bold=True)

    title = title_font.render("HOW TO PLAY (PAUSED)", True, (255, 228, 110))
    surface.blit(title, (panel_rect.centerx - title.get_width() // 2, panel_top + 24))

    guide_lines = [
        "Arrow Keys: Move Pac-Man",
        "R: Restart the game",
        "I or ESC: Close this info panel",
        "Goal: Eat all pellets",
        "Avoid ghosts unless power mode is active",
        "Power Pellet: Turns ghosts blue for 8 seconds",
    ]
    line_y = panel_top + 96
    for line in guide_lines:
        text = body_font.render(line, True, TEXT_COLOR)
        surface.blit(text, (panel_left + 34, line_y))
        line_y += 40

    continue_rect = continue_button_rect()
    pygame.draw.rect(surface, (72, 145, 94), continue_rect, border_radius=9)
    pygame.draw.rect(surface, (230, 230, 230), continue_rect, width=2, border_radius=9)
    continue_font = pygame.font.SysFont("consolas", 24, bold=True)
    continue_text = continue_font.render("CONTINUE", True, (255, 255, 255))
    surface.blit(
        continue_text,
        (
            continue_rect.centerx - continue_text.get_width() // 2,
            continue_rect.centery - continue_text.get_height() // 2,
        ),
    )

    credit = foot_font.render(
        "Vikram Oberai and Jack Yu. Made with help of AI.",
        True,
        (210, 210, 210),
    )
    surface.blit(
        credit,
        (panel_rect.centerx - credit.get_width() // 2, panel_rect.bottom - 38),
    )


def create_ghosts(initial_release_time: float) -> list[Ghost]:
    """Create ghost entities in the starting box."""
    ghost_specs = [
        ((13, 14), (255, 0, 0)),
        ((14, 14), (255, 184, 255)),
        ((12, 15), (0, 255, 255)),
        ((15, 15), (255, 184, 82)),
    ]

    ghosts: list[Ghost] = []
    for (col, row), color in ghost_specs:
        spawn_center = tile_center(col, row, 0, HUD_TOP)
        ghosts.append(
            Ghost(
                position=pygame.Vector2(spawn_center),
                spawn_position=pygame.Vector2(spawn_center),
                base_color=color,
                direction=random.choice([DIR_LEFT, DIR_RIGHT]),
                state="in_box",
                release_time=initial_release_time,
            )
        )
    return ghosts


def draw_ghosts(
    surface: pygame.Surface,
    ghosts: list[Ghost],
    ghost_radius: int,
    power_mode_active: bool,
) -> None:
    """Render all ghost entities at their current positions."""
    for ghost in ghosts:
        color = (40, 90, 255) if power_mode_active and ghost.state != "in_box" else ghost.base_color
        draw_ghost(
            surface,
            (int(ghost.position.x), int(ghost.position.y)),
            color,
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


def snap_to_tile_center(position: pygame.Vector2) -> pygame.Vector2:
    """Return a copy of position snapped to the current tile center."""
    row, col = map_cell_from_position(position)
    center_x, center_y = tile_center(col, row, 0, HUD_TOP)
    return pygame.Vector2(center_x, center_y)


def align_position_to_direction_axis(
    position: pygame.Vector2,
    direction: pygame.Vector2,
) -> pygame.Vector2:
    """Align position to tile center on the axis perpendicular to movement."""
    aligned = pygame.Vector2(position)
    row, col = map_cell_from_position(aligned)
    center_x, center_y = tile_center(col, row, 0, HUD_TOP)
    if direction.x != 0:
        aligned.y = center_y
    elif direction.y != 0:
        aligned.x = center_x
    return aligned


def update_pacman_position(
    position: pygame.Vector2,
    current_direction: pygame.Vector2,
    buffered_direction: pygame.Vector2,
    radius: int,
    speed: float,
) -> tuple[pygame.Vector2, pygame.Vector2]:
    """Move Pac-Man with turn buffering and tile-center alignment.

    This prevents corner clipping that can make Pac-Man appear stuck in walls.
    """
    new_position = pygame.Vector2(position)
    # Use a tight threshold; a wide snap window causes visible stutter
    # and can pin movement to a single step.
    near_center = is_near_tile_center(new_position, threshold=1.0)
    if near_center:
        new_position = snap_to_tile_center(new_position)

    if buffered_direction != DIR_NONE:
        # Evaluate the buffered direction on an aligned lane so starts and turns
        # are responsive while still preventing corner clipping.
        aligned_for_turn = align_position_to_direction_axis(new_position, buffered_direction)
        if can_move_to(aligned_for_turn + buffered_direction * speed, radius):
            new_position = aligned_for_turn
            current_direction = buffered_direction

    if current_direction != DIR_NONE:
        axis_aligned = align_position_to_direction_axis(new_position, current_direction)
        candidate = axis_aligned + current_direction * speed
        if can_move_to(candidate, radius):
            new_position = candidate
        else:
            new_position = axis_aligned
            current_direction = DIR_NONE

    return new_position, current_direction


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
    exit_x = tile_center(14, 14, 0, HUD_TOP)[0]
    exit_target_y = tile_center(14, 11, 0, HUD_TOP)[1]

    for ghost in ghosts:
        if ghost.state == "in_box":
            if elapsed_sec >= ghost.release_time:
                ghost.state = "exiting"
                ghost.direction = DIR_UP
            else:
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


def consume_pellet(
    pacman_position: pygame.Vector2,
    pellet_tiles: set[tuple[int, int]],
    power_pellet_tiles: set[tuple[int, int]],
) -> tuple[int, bool]:
    """Consume pellet on Pac-Man's current tile and return (points, is_power_pellet)."""
    row, col = map_cell_from_position(pacman_position)
    tile_pos = (row, col)
    if tile_pos not in pellet_tiles:
        return 0, False

    pellet_tiles.remove(tile_pos)
    if tile_pos in power_pellet_tiles:
        power_pellet_tiles.remove(tile_pos)
        return POWER_PELLET_POINTS, True
    return NORMAL_PELLET_POINTS, False


def send_ghost_back_to_box(ghost: Ghost, now_sec: float) -> None:
    """Reset an eaten ghost to the box and delay its next release."""
    ghost.position = pygame.Vector2(ghost.spawn_position)
    ghost.direction = random.choice([DIR_LEFT, DIR_RIGHT])
    ghost.state = "in_box"
    ghost.release_time = now_sec + GHOST_RELEASE_DELAY_SEC


def draw_center_message(surface: pygame.Surface, title: str, subtitle: str) -> None:
    """Draw a centered message panel over gameplay area."""
    title_font = pygame.font.SysFont("consolas", 42, bold=True)
    subtitle_font = pygame.font.SysFont("consolas", 24, bold=True)

    panel_width = 640
    panel_height = 140
    panel_left = (SCREEN_WIDTH - panel_width) // 2
    panel_top = HUD_TOP + (MAP_HEIGHT - panel_height) // 2
    panel_rect = pygame.Rect(panel_left, panel_top, panel_width, panel_height)

    pygame.draw.rect(surface, (10, 10, 10), panel_rect, border_radius=12)
    pygame.draw.rect(surface, (255, 255, 255), panel_rect, width=2, border_radius=12)

    title_text = title_font.render(title, True, (255, 230, 80))
    subtitle_text = subtitle_font.render(subtitle, True, TEXT_COLOR)
    surface.blit(title_text, (panel_rect.centerx - title_text.get_width() // 2, panel_top + 22))
    surface.blit(
        subtitle_text,
        (panel_rect.centerx - subtitle_text.get_width() // 2, panel_top + 82),
    )


def main() -> None:
    """Run the pygame loop for map preview and movement prototype."""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Pac-Man Map with HUD")
    clock = pygame.time.Clock()

    score = 0
    high_score = 12000
    lives = START_LIVES

    pacman_radius = max(10, TILE_SIZE // 2 - 4)
    ghost_radius = pacman_radius + 2

    pacman_position = pygame.Vector2(tile_center(14, 23, 0, HUD_TOP))
    pacman_direction = DIR_NONE
    buffered_direction = DIR_NONE
    last_facing = DIR_RIGHT

    ghosts = create_ghosts(GHOST_RELEASE_DELAY_SEC)
    pellet_tiles = build_pellet_tiles()
    power_pellet_tiles = {
        (row_index, col_index)
        for row_index, row in enumerate(MAZE_LAYOUT)
        for col_index, tile in enumerate(row)
        if tile == POWER_PELLET_TILE
    }
    elapsed_sec = 0.0
    power_mode_until = 0.0
    is_game_over = False
    is_round_clear = False
    show_info_overlay = False

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        elapsed_sec += dt

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_i:
                show_info_overlay = not show_info_overlay
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE and show_info_overlay:
                show_info_overlay = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_c and show_info_overlay:
                show_info_overlay = False
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and info_button_rect().collidepoint(event.pos)
            ):
                show_info_overlay = not show_info_overlay
            if (
                event.type == pygame.MOUSEBUTTONDOWN
                and event.button == 1
                and show_info_overlay
                and continue_button_rect().collidepoint(event.pos)
            ):
                show_info_overlay = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                score = 0
                lives = START_LIVES
                pacman_position = pygame.Vector2(tile_center(14, 23, 0, HUD_TOP))
                pacman_direction = DIR_NONE
                buffered_direction = DIR_NONE
                last_facing = DIR_RIGHT
                ghosts = create_ghosts(elapsed_sec + GHOST_RELEASE_DELAY_SEC)
                pellet_tiles = build_pellet_tiles()
                power_pellet_tiles = {
                    (row_index, col_index)
                    for row_index, row in enumerate(MAZE_LAYOUT)
                    for col_index, tile in enumerate(row)
                    if tile == POWER_PELLET_TILE
                }
                power_mode_until = 0.0
                is_game_over = False
                is_round_clear = False
                show_info_overlay = False

        if not is_game_over and not is_round_clear and not show_info_overlay:
            pressed = pygame.key.get_pressed()
            input_direction = pacman_direction_from_keys(pressed)
            if input_direction != DIR_NONE:
                buffered_direction = input_direction

            pacman_position, pacman_direction = update_pacman_position(
                pacman_position,
                pacman_direction,
                buffered_direction,
                pacman_radius,
                PACMAN_SPEED,
            )
            if pacman_direction != DIR_NONE:
                last_facing = pacman_direction

            gained_points, got_power_pellet = consume_pellet(
                pacman_position,
                pellet_tiles,
                power_pellet_tiles,
            )
            if gained_points:
                score += gained_points
                high_score = max(high_score, score)
            if got_power_pellet:
                power_mode_until = elapsed_sec + POWER_MODE_DURATION_SEC
            if not pellet_tiles:
                is_round_clear = True

            update_ghosts(ghosts, elapsed_sec, ghost_radius)
            power_mode_active = elapsed_sec < power_mode_until
            for ghost in ghosts:
                if ghost.state == "in_box":
                    continue
                if pacman_position.distance_to(ghost.position) <= (pacman_radius + ghost_radius - 4):
                    if power_mode_active:
                        score += GHOST_EAT_POINTS
                        high_score = max(high_score, score)
                        send_ghost_back_to_box(ghost, elapsed_sec)
                    else:
                        lives -= 1
                        score = max(0, score - HIT_PENALTY_POINTS)
                        pacman_position = pygame.Vector2(tile_center(14, 23, 0, HUD_TOP))
                        pacman_direction = DIR_NONE
                        buffered_direction = DIR_NONE
                        last_facing = DIR_RIGHT
                        ghosts = create_ghosts(elapsed_sec + GHOST_RELEASE_DELAY_SEC)
                        power_mode_until = 0.0
                        if lives <= 0:
                            is_game_over = True
                        break

        screen.fill(BG_COLOR)
        draw_hud(screen, score, high_score, lives)
        draw_info_button(screen, active=show_info_overlay)
        draw_map(screen, 0, HUD_TOP, pellet_tiles=pellet_tiles)
        draw_ghosts(screen, ghosts, ghost_radius, power_mode_active=elapsed_sec < power_mode_until)
        draw_pacman(
            screen,
            (int(pacman_position.x), int(pacman_position.y)),
            pacman_radius,
            mouth_angle_deg=35,
            direction=direction_to_mouth_angle(last_facing),
        )
        if is_game_over:
            draw_center_message(screen, "GAME OVER", "Press R to restart")
        elif is_round_clear:
            draw_center_message(screen, "YOU WIN!", "All pellets cleared - press R to play again")
        if show_info_overlay:
            draw_info_overlay(screen)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
