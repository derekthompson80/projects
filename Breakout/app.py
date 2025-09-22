from __future__ import annotations

import sys
import random
import tkinter as tk
from dataclasses import dataclass

"""
Single-player Breakout (Tkinter)

How to run (from project root):
  - python -m projects.Breakout.app
  or
  - python projects\Breakout\app.py

Controls:
  - Left / Right arrow keys: move paddle
  - A / D keys: move paddle
  - Mouse move (optional): move paddle
  - Space: launch ball or pause/resume
  - R: restart when game over/win

Notes:
  - No external dependencies required (Tkinter only)
  - Window is resizable; game field is a fixed logical size with scaling
"""

# Logical game dimensions
LOGICAL_W = 800
LOGICAL_H = 600

# Gameplay constants
PADDLE_W = 100
PADDLE_H = 16
PADDLE_Y = LOGICAL_H - 40
PADDLE_SPEED = 12

BALL_R = 8
BALL_SPEED_INIT = 6.0
BALL_SPEED_MAX = 12.0
SPEEDUP_EVERY = 8  # bricks per speed up

BRICK_ROWS = 6
BRICK_COLS = 12
BRICK_MARGIN_X = 8
BRICK_MARGIN_Y = 6
BRICK_TOP = 80
BRICK_AREA_W = LOGICAL_W - 2 * 20
BRICK_W = (BRICK_AREA_W - (BRICK_COLS - 1) * BRICK_MARGIN_X) // BRICK_COLS
BRICK_H = 22

HUD_HEIGHT = 40

COLORS = [
    "#60a5fa",  # blue-400
    "#34d399",  # green-400
    "#fbbf24",  # amber-400
    "#f87171",  # red-400
    "#a78bfa",  # violet-400
    "#f472b6",  # pink-400
]

@dataclass
class Brick:
    x: int
    y: int
    w: int
    h: int
    color: str
    alive: bool = True


class BreakoutApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Breakout — Single Player")
        self.geometry("900x700")
        self.minsize(640, 480)
        self.configure(bg="#0f172a")

        # Canvas with dark theme
        self.canvas = tk.Canvas(self, bg="#0b1220", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Bindings
        self.bind("<Left>", lambda e: self._key_left(True))
        self.bind("<KeyRelease-Left>", lambda e: self._key_left(False))
        self.bind("<Right>", lambda e: self._key_right(True))
        self.bind("<KeyRelease-Right>", lambda e: self._key_right(False))
        self.bind("<KeyPress-a>", lambda e: self._key_left(True))
        self.bind("<KeyRelease-a>", lambda e: self._key_left(False))
        self.bind("<KeyPress-d>", lambda e: self._key_right(True))
        self.bind("<KeyRelease-d>", lambda e: self._key_right(False))
        self.bind("<space>", lambda e: self.toggle_pause_or_launch())
        self.bind("<KeyPress-p>", lambda e: self.toggle_pause_or_launch())
        self.bind("<KeyPress-r>", lambda e: self.restart())
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.bind("<Configure>", lambda e: self._redraw_static())

        # Game state
        self.scale_x = 1.0
        self.scale_y = 1.0
        self.running = True
        self.paused = True
        self.lives = 3
        self.score = 0
        self.bricks: list[Brick] = []
        self.bricks_destroyed = 0

        self.paddle_x = (LOGICAL_W - PADDLE_W) // 2
        self.left_pressed = False
        self.right_pressed = False

        self.ball_x = LOGICAL_W // 2
        self.ball_y = PADDLE_Y - BALL_R - 2
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self.ball_speed = BALL_SPEED_INIT
        self.awaiting_launch = True

        self._build_level()
        self._game_loop()

    # --- Input handlers ---
    def _key_left(self, down: bool):
        self.left_pressed = down

    def _key_right(self, down: bool):
        self.right_pressed = down

    def _on_mouse_move(self, event):
        # Map screen coords to logical
        lx, _ = self._screen_to_logical(event.x, event.y)
        self.paddle_x = max(10, min(int(lx - PADDLE_W // 2), LOGICAL_W - PADDLE_W - 10))

    def toggle_pause_or_launch(self):
        if self.is_over():
            return
        if self.awaiting_launch:
            # Launch with random slight angle
            self.awaiting_launch = False
            self.paused = False
            ang = random.uniform(-0.6, 0.6)
            self.ball_vx = self.ball_speed * ang
            self.ball_vy = -self.ball_speed * (1.0 - abs(ang) * 0.4)
        else:
            self.paused = not self.paused

    def restart(self):
        # Reset everything
        self.paused = True
        self.awaiting_launch = True
        self.running = True
        self.lives = 3
        self.score = 0
        self.bricks_destroyed = 0
        self.ball_speed = BALL_SPEED_INIT
        self.paddle_x = (LOGICAL_W - PADDLE_W) // 2
        self.ball_x = LOGICAL_W // 2
        self.ball_y = PADDLE_Y - BALL_R - 2
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self._build_level()
        self._redraw_static()

    # --- Level / Draw ---
    def _build_level(self):
        self.bricks.clear()
        left = (LOGICAL_W - BRICK_AREA_W) // 2
        for r in range(BRICK_ROWS):
            for c in range(BRICK_COLS):
                x = left + c * (BRICK_W + BRICK_MARGIN_X)
                y = BRICK_TOP + r * (BRICK_H + BRICK_MARGIN_Y)
                color = COLORS[r % len(COLORS)]
                self.bricks.append(Brick(x, y, BRICK_W, BRICK_H, color, True))

    def _logical_to_screen(self, lx: float, ly: float) -> tuple[int, int]:
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        self.scale_x = cw / LOGICAL_W
        self.scale_y = ch / LOGICAL_H
        return int(lx * self.scale_x), int(ly * self.scale_y)

    def _screen_to_logical(self, sx: float, sy: float) -> tuple[float, float]:
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        self.scale_x = cw / LOGICAL_W
        self.scale_y = ch / LOGICAL_H
        return sx / self.scale_x, sy / self.scale_y

    def _redraw_static(self):
        # redraw everything from current state
        self.canvas.delete("all")
        # HUD background
        self._draw_hud()
        # Bricks
        for b in self.bricks:
            if b.alive:
                self._draw_rect(b.x, b.y, b.w, b.h, fill=b.color, outline="#111827")
        # Paddle
        self._draw_rect(self.paddle_x, PADDLE_Y, PADDLE_W, PADDLE_H, fill="#93c5fd", outline="#1e3a8a")
        # Ball
        self._draw_ball()
        # Overlay messages
        self._maybe_draw_messages()

    def _draw_hud(self):
        # Top strip
        self._draw_rect(0, 0, LOGICAL_W, HUD_HEIGHT, fill="#0b1220", outline="")
        txt = f"Score: {self.score}    Lives: {self.lives}"
        if self.awaiting_launch and not self.is_over():
            txt += "    Press Space to Launch"
        self._draw_text(LOGICAL_W // 2, HUD_HEIGHT // 2, txt, size=14, color="#e5e7eb")

    def _draw_rect(self, x: int, y: int, w: int, h: int, fill: str, outline: str = "#1f2937"):
        x1, y1 = self._logical_to_screen(x, y)
        x2, y2 = self._logical_to_screen(x + w, y + h)
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline)

    def _draw_ball(self):
        x1, y1 = self._logical_to_screen(self.ball_x - BALL_R, self.ball_y - BALL_R)
        x2, y2 = self._logical_to_screen(self.ball_x + BALL_R, self.ball_y + BALL_R)
        self.canvas.create_oval(x1, y1, x2, y2, fill="#fde68a", outline="#92400e")

    def _draw_text(self, cx: int, cy: int, text: str, size: int = 16, color: str = "#e5e7eb"):
        x, y = self._logical_to_screen(cx, cy)
        self.canvas.create_text(x, y, text=text, fill=color, font=("Segoe UI", size))

    def _maybe_draw_messages(self):
        if self.is_over():
            msg = "You Win!" if self._all_cleared() else "Game Over"
            sub = "Press R to Restart"
            self._draw_text(LOGICAL_W // 2, LOGICAL_H // 2 - 10, msg, size=28)
            self._draw_text(LOGICAL_W // 2, LOGICAL_H // 2 + 24, sub, size=16, color="#9ca3af")
        elif self.paused:
            self._draw_text(LOGICAL_W // 2, LOGICAL_H // 2, "Paused — Press Space", size=20, color="#9ca3af")

    # --- Game loop / physics ---
    def _game_loop(self):
        try:
            self._step()
            self._redraw_static()
        finally:
            # Run at ~60 FPS
            self.after(16, self._game_loop)

    def _step(self):
        if not self.running or self.paused:
            return
        # Move paddle from input
        if self.left_pressed and not self.right_pressed:
            self.paddle_x -= PADDLE_SPEED
        elif self.right_pressed and not self.left_pressed:
            self.paddle_x += PADDLE_SPEED
        self.paddle_x = max(10, min(self.paddle_x, LOGICAL_W - PADDLE_W - 10))

        # Move ball
        self.ball_x += self.ball_vx
        self.ball_y += self.ball_vy

        # Wall collisions
        if self.ball_x <= BALL_R:
            self.ball_x = BALL_R
            self.ball_vx = abs(self.ball_vx)
        elif self.ball_x >= LOGICAL_W - BALL_R:
            self.ball_x = LOGICAL_W - BALL_R
            self.ball_vx = -abs(self.ball_vx)
        if self.ball_y <= HUD_HEIGHT + BALL_R:
            self.ball_y = HUD_HEIGHT + BALL_R
            self.ball_vy = abs(self.ball_vy)

        # Bottom — lose life
        if self.ball_y > LOGICAL_H + BALL_R:
            self.lives -= 1
            if self.lives <= 0:
                self.running = False
                self.paused = True
            # Reset ball to paddle
            self.awaiting_launch = True
            self.paused = True
            self.ball_x = self.paddle_x + PADDLE_W // 2
            self.ball_y = PADDLE_Y - BALL_R - 2
            self.ball_vx = 0.0
            self.ball_vy = 0.0
            return

        # Paddle collision (only when moving downward)
        if self.ball_vy > 0 and (PADDLE_Y - BALL_R - 1) <= self.ball_y <= (PADDLE_Y + PADDLE_H) and \
           (self.paddle_x - BALL_R) <= self.ball_x <= (self.paddle_x + PADDLE_W + BALL_R):
            self.ball_y = PADDLE_Y - BALL_R - 1
            # Determine bounce based on where it hits the paddle
            hit_pos = (self.ball_x - self.paddle_x) / PADDLE_W  # 0..1
            angle = (hit_pos - 0.5) * 1.2  # widen range
            speed = max(BALL_SPEED_INIT, min(BALL_SPEED_MAX, (self.ball_speed)))
            self.ball_vx = speed * angle * 1.6
            self.ball_vy = -abs(speed * (1.0 - abs(angle) * 0.3))

        # Brick collisions: check AABB overlap; remove one brick per frame
        hit_index = -1
        for i, b in enumerate(self.bricks):
            if not b.alive:
                continue
            # Ball-center to rect collision using nearest point approach
            nearest_x = max(b.x, min(self.ball_x, b.x + b.w))
            nearest_y = max(b.y, min(self.ball_y, b.y + b.h))
            dx = self.ball_x - nearest_x
            dy = self.ball_y - nearest_y
            if dx * dx + dy * dy <= BALL_R * BALL_R:
                hit_index = i
                break
        if hit_index >= 0:
            b = self.bricks[hit_index]
            b.alive = False
            self.score += 10
            self.bricks_destroyed += 1
            # Reflect ball based on which side is closer
            # Compute penetration direction
            overlap_left = abs((self.ball_x + BALL_R) - b.x)
            overlap_right = abs((b.x + b.w) - (self.ball_x - BALL_R))
            overlap_top = abs((self.ball_y + BALL_R) - b.y)
            overlap_bottom = abs((b.y + b.h) - (self.ball_y - BALL_R))
            min_overlap = min(overlap_left, overlap_right, overlap_top, overlap_bottom)
            if min_overlap == overlap_left:
                self.ball_vx = -abs(self.ball_vx)
            elif min_overlap == overlap_right:
                self.ball_vx = abs(self.ball_vx)
            elif min_overlap == overlap_top:
                self.ball_vy = -abs(self.ball_vy)
            else:
                self.ball_vy = abs(self.ball_vy)

            # Speed up every few bricks
            if self.bricks_destroyed % SPEEDUP_EVERY == 0 and self.ball_speed < BALL_SPEED_MAX:
                self.ball_speed = min(BALL_SPEED_MAX, self.ball_speed + 0.8)
                # Renormalize velocity to new speed keeping direction
                sp = max(0.1, (self.ball_speed))
                norm = (self.ball_vx ** 2 + self.ball_vy ** 2) ** 0.5
                if norm > 0:
                    self.ball_vx = self.ball_vx / norm * sp
                    self.ball_vy = self.ball_vy / norm * sp

        # Win condition
        if self._all_cleared():
            self.running = False
            self.paused = True

        # If awaiting launch, stick ball to paddle
        if self.awaiting_launch:
            self.ball_x = self.paddle_x + PADDLE_W // 2
            self.ball_y = PADDLE_Y - BALL_R - 2

    def _all_cleared(self) -> bool:
        return all(not b.alive for b in self.bricks)

    def is_over(self) -> bool:
        return (not self.running) and (self._all_cleared() or self.lives <= 0)


def main() -> int:
    app = BreakoutApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
