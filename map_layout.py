"""Pac-Man map layout and drawing helpers for pygame."""

from __future__ import annotations

import pygame

TILE_SIZE = 28
WALL_COLOR = (0, 102, 255)
PATH_COLOR = (0, 0, 0)
PELLET_COLOR = (255, 235, 140)

# Legend:
# 1 = wall
# 0 = walkable path
# 2 = ghost house area (walkable for ghosts only in a full game)
# 3 = power pellet spawn tile
MAZE_LAYOUT = [
    "1111111111111111111111111111",
    "1000000000000110000000000001",
    "1011110111110110111110111101",
    "1311110111110110111110111131",
    "1011110111110110111110111101",
    "1000000000000000000000000001",
    "1011110110111111110110111101",
    "1011110110111111110110111101",
    "1000000110000110000110000001",
    "1111110111110110111110111111",
    "1111110111110110111110111111",
    "1111110110000000000110111111",
    "1111110110111222110110111111",
    "1111110110122222210110111111",
    "0000000000122222210000000000",
    "1111110110122222210110111111",
    "1111110110111111110110111111",
    "1111110110000000000110111111",
    "1111110110111111110110111111",
    "1111110110111111110110111111",
    "1000000000000110000000000001",
    "1011110111110110111110111101",
    "1011110111110110111110111101",
    "1300110000000000000010001131",
    "1110110110111111110110110111",
    "1110110110111111110110110111",
    "1000000110000110000110000001",
    "1011111111110110111111111101",
    "1011111111110110111111111101",
    "1000000000000000000000000001",
    "1111111111111111111111111111",
]

ROWS = len(MAZE_LAYOUT)
COLS = len(MAZE_LAYOUT[0])
MAP_WIDTH = COLS * TILE_SIZE
MAP_HEIGHT = ROWS * TILE_SIZE


def tile_center(col: int, row: int, offset_x: int = 0, offset_y: int = 0) -> tuple[int, int]:
    """Return pixel center for a tile coordinate."""
    return (
        offset_x + col * TILE_SIZE + TILE_SIZE // 2,
        offset_y + row * TILE_SIZE + TILE_SIZE // 2,
    )


def draw_map(surface: pygame.Surface, offset_x: int = 0, offset_y: int = 0) -> None:
    """Draw walls, floor, and pellets based on MAZE_LAYOUT."""
    for row_index, row in enumerate(MAZE_LAYOUT):
        for col_index, tile in enumerate(row):
            x = offset_x + col_index * TILE_SIZE
            y = offset_y + row_index * TILE_SIZE
            cell_rect = pygame.Rect(x, y, TILE_SIZE, TILE_SIZE)

            if tile == "1":
                pygame.draw.rect(surface, WALL_COLOR, cell_rect, border_radius=6)
            else:
                pygame.draw.rect(surface, PATH_COLOR, cell_rect)
                if tile == "0":
                    pygame.draw.circle(
                        surface,
                        PELLET_COLOR,
                        cell_rect.center,
                        max(2, TILE_SIZE // 8),
                    )
                elif tile == "3":
                    pygame.draw.circle(
                        surface,
                        PELLET_COLOR,
                        cell_rect.center,
                        max(5, TILE_SIZE // 4),
                    )
