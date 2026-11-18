"""Render a contact sheet of every enemy/boss/hero sprite to qa/shots/sprites.png (headless)."""
import os, sys
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import pygame
from game.sprites import ENEMY, HERO

keys = sorted(ENEMY, key=lambda k: (str(k[0]), k[1]))
heroes = list(HERO)
cell = 90
cols = 8
rows = (len(keys) + len(heroes) + cols - 1) // cols
sheet = pygame.Surface((cols * cell, rows * (cell + 14)))
sheet.fill((46, 40, 66))
f = pygame.font.Font(None, 15)
items = [(f"{k[0]}{k[1] if k[0]=='slime' else ''}", ENEMY[k][0]) for k in keys] + [(h, HERO[h][0]) for h in heroes]
for n, (label, fr) in enumerate(items):
    cx, cy = (n % cols) * cell + cell // 2, (n // cols) * (cell + 14) + cell - 4
    sheet.blit(fr, (cx - fr.get_width() // 2, cy - fr.get_height()))
    img = f.render(label, False, (240, 240, 245))
    sheet.blit(img, (cx - img.get_width() // 2, cy + 1))
sheet = pygame.transform.scale(sheet, (sheet.get_width() * 2, sheet.get_height() * 2))
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shots", "sprites.png")
os.makedirs(os.path.dirname(out), exist_ok=True)
pygame.image.save(sheet, out)
print(out, len(items), "sprites")
