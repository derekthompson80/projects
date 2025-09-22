"""
Watermark GUI Application (Tkinter + Pillow)

Features:
- Load an image (PNG/JPG/WebP/etc.)
- Add a text watermark and/or logo watermark
- Choose position (Top-Left/Top-Right/Bottom-Left/Bottom-Right/Center)
- Adjust opacity and size (text font size or logo scale)
- Set padding from edges
- Live preview (scaled to fit a window)
- Save the result as a new image

Run:
  python projects\Water_mark\water_m.py

Requirements:
  - Python 3.8+
  - Pillow (pip install Pillow)

This app degrades gracefully and shows a helpful message if Pillow is not installed.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk, ImageDraw, ImageFont  # type: ignore



@dataclass
class WatermarkConfig:
    position: str = "Bottom-Right"  # TL/TR/BL/BR/Center
    opacity: int = 60  # 0-100
    padding: int = 16  # pixels from edge
    text: str = ""
    text_size: int = 36  # pt
    logo_path: str | None = None
    logo_scale: int = 40  # percentage scale relative to base width (e.g., 40%)


class WatermarkApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Image Watermark Tool")
        self.geometry("1000x700")
        self.minsize(900, 600)

        self.base_image: Image.Image | None = None
        self.rendered_image: Image.Image | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.base_path: str | None = None

        self.config_state = WatermarkConfig()

        self._build_ui()
        self._bind_events()

    # --- UI ---
    def _build_ui(self) -> None:
        # Top toolbar
        toolbar = ttk.Frame(self)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self.btn_open = ttk.Button(toolbar, text="Open Image", command=self.open_image)
        self.btn_open.pack(side=tk.LEFT, padx=6, pady=6)

        self.btn_open_logo = ttk.Button(toolbar, text="Open Logo (Optional)", command=self.open_logo)
        self.btn_open_logo.pack(side=tk.LEFT, padx=6, pady=6)

        self.btn_save = ttk.Button(toolbar, text="Save As…", command=self.save_image)
        self.btn_save.pack(side=tk.LEFT, padx=6, pady=6)

        # Right control panel
        main = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main.pack(fill=tk.BOTH, expand=True)

        self.preview_frame = ttk.Frame(main)
        self.sidebar = ttk.Frame(main, width=320)
        main.add(self.preview_frame, weight=4)
        main.add(self.sidebar, weight=0)

        # Preview canvas
        self.canvas = tk.Canvas(self.preview_frame, bg="#1f2937", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Sidebar controls
        row = 0
        def add_label(text: str):
            nonlocal row
            lbl = ttk.Label(self.sidebar, text=text)
            lbl.grid(row=row, column=0, sticky="w", padx=10, pady=(12, 2))
            row += 1
            return lbl

        def add_entry(var: tk.StringVar):
            nonlocal row
            ent = ttk.Entry(self.sidebar, textvariable=var)
            ent.grid(row=row, column=0, sticky="ew", padx=10)
            row += 1
            return ent

        def add_scale(var: tk.IntVar, from_, to_, step=1):
            nonlocal row
            scl = ttk.Scale(self.sidebar, orient=tk.HORIZONTAL, from_=from_, to=to_, command=lambda v: var.set(int(float(v))))
            scl.set(var.get())
            scl.grid(row=row, column=0, sticky="ew", padx=10)
            # show current value
            val_lbl = ttk.Label(self.sidebar, textvariable=var, width=4)
            val_lbl.grid(row=row, column=1, sticky="w")
            row += 1
            return scl

        def add_combo(var: tk.StringVar, values: list[str]):
            nonlocal row
            cb = ttk.Combobox(self.sidebar, textvariable=var, values=values, state="readonly")
            cb.grid(row=row, column=0, sticky="ew", padx=10)
            row += 1
            return cb

        self.sidebar.columnconfigure(0, weight=1)

        # Position
        add_label("Position")
        self.var_position = tk.StringVar(value=self.config_state.position)
        self.cb_position = add_combo(self.var_position, ["Top-Left", "Top-Right", "Bottom-Left", "Bottom-Right", "Center"])

        # Opacity
        add_label("Opacity (%)")
        self.var_opacity = tk.IntVar(value=self.config_state.opacity)
        self.s_opacity = add_scale(self.var_opacity, 0, 100)

        # Padding
        add_label("Padding (px)")
        self.var_padding = tk.IntVar(value=self.config_state.padding)
        self.s_padding = add_scale(self.var_padding, 0, 200)

        # Text watermark
        add_label("Text Watermark")
        self.var_text = tk.StringVar(value=self.config_state.text)
        self.e_text = add_entry(self.var_text)

        add_label("Text Size (pt)")
        self.var_text_size = tk.IntVar(value=self.config_state.text_size)
        self.s_text_size = add_scale(self.var_text_size, 8, 200)

        # Logo watermark
        add_label("Logo Scale (% of base width)")
        self.var_logo_scale = tk.IntVar(value=self.config_state.logo_scale)
        self.s_logo_scale = add_scale(self.var_logo_scale, 5, 100)

        # Info label
        self.lbl_status = ttk.Label(self.sidebar, text="Load an image to begin.", foreground="#374151")
        self.lbl_status.grid(row=row, column=0, sticky="w", padx=10, pady=16)

    def _bind_events(self) -> None:
        # Update preview on changes
        for var in (self.var_position, self.var_opacity, self.var_padding, self.var_text, self.var_text_size, self.var_logo_scale):
            var.trace_add("write", lambda *args: self.update_preview())
        self.bind("<Configure>", lambda e: self._refresh_canvas())

    # --- File Actions ---
    def open_image(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Image",
            filetypes=[
                ("Image Files", ".png .jpg .jpeg .webp .bmp .gif"),
                ("All Files", "*.*"),
            ],
        )
        if not path:
            return
        if Image is None:
            messagebox.showerror("Missing dependency", "Pillow is required to open images.")
            return
        try:
            img = Image.open(path).convert("RGBA")
        except Exception as e:
            messagebox.showerror("Open failed", f"Could not open image.\n{e}")
            return
        self.base_image = img
        self.base_path = path
        self.lbl_status.config(text=f"Loaded: {os.path.basename(path)} ({img.width}x{img.height})")
        self.update_preview()

    def open_logo(self) -> None:
        path = filedialog.askopenfilename(
            title="Open Logo",
            filetypes=[
                ("Image Files", ".png .jpg .jpeg .webp .bmp .gif"),
                ("All Files", "*.*"),
            ],
        )
        if not path:
            return
        if Image is None:
            messagebox.showerror("Missing dependency", "Pillow is required to open images.")
            return
        try:
            # Keep path and lazy-load during render to allow re-scaling
            self.config_state.logo_path = path
            self.lbl_status.config(text=f"Logo selected: {os.path.basename(path)}")
            self.update_preview()
        except Exception as e:
            messagebox.showerror("Logo load failed", str(e))

    def save_image(self) -> None:
        if self.base_image is None:
            messagebox.showinfo("No image", "Please open an image first.")
            return
        if Image is None:
            messagebox.showerror("Missing dependency", "Pillow is required to save images.")
            return
        # Compose final at full size
        try:
            result = self._compose_full()
        except Exception as e:
            messagebox.showerror("Compose failed", f"Could not render watermark.\n{e}")
            return
        # Decide default name
        base = os.path.splitext(self.base_path or "output.png")[0]
        default = f"{base}_watermarked.png"
        out_path = filedialog.asksaveasfilename(
            title="Save Image As",
            defaultextension=".png",
            initialfile=os.path.basename(default),
            filetypes=[
                ("PNG", ".png"),
                ("JPEG", ".jpg .jpeg"),
                ("WebP", ".webp"),
                ("All Files", "*.*"),
            ],
        )
        if not out_path:
            return
        try:
            # Convert to RGB for JPEG
            ext = os.path.splitext(out_path)[1].lower()
            if ext in (".jpg", ".jpeg"):
                result = result.convert("RGB")
            result.save(out_path)
            messagebox.showinfo("Saved", f"Saved to:\n{out_path}")
        except Exception as e:
            messagebox.showerror("Save failed", f"Could not save image.\n{e}")

    # --- Rendering ---
    def _compose_full(self) -> Image.Image:
        """Render watermark onto the full-size image and return new RGBA image."""
        assert self.base_image is not None
        base = self.base_image.copy().convert("RGBA")
        overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Compute watermark from text and/or logo
        elements: list[Image.Image] = []

        # Text
        text = self.var_text.get().strip()
        if text:
            font = self._get_font(self.var_text_size.get())
            # Draw text to its own image for alpha control
            tmp = Image.new("RGBA", base.size, (0, 0, 0, 0))
            tdraw = ImageDraw.Draw(tmp)
            bbox = tdraw.textbbox((0, 0), text, font=font)
            text_w, text_h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            text_img = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 0))
            ImageDraw.Draw(text_img).text((0, 0), text, font=font, fill=(255, 255, 255, 255))
            elements.append(text_img)

        # Logo
        if self.config_state.logo_path:
            try:
                logo = Image.open(self.config_state.logo_path).convert("RGBA")
                # Scale based on base width
                target_w = max(1, int(base.width * (self.var_logo_scale.get() / 100.0)))
                scale = target_w / max(1, logo.width)
                target_h = max(1, int(logo.height * scale))
                logo = logo.resize((target_w, target_h), Image.LANCZOS)
                elements.append(logo)
            except Exception:
                # Ignore logo errors in compose
                pass

        if not elements:
            return base

        # Combine text and logo into a single watermark tile stacked vertically with small gap
        gap = 8
        wm_w = max(e.width for e in elements)
        wm_h = sum(e.height for e in elements) + gap * (len(elements) - 1)
        watermark = Image.new("RGBA", (wm_w, wm_h), (0, 0, 0, 0))
        y = 0
        for i, e in enumerate(elements):
            x = (wm_w - e.width) // 2
            watermark.alpha_composite(e, (x, y))
            y += e.height + (gap if i < len(elements) - 1 else 0)

        # Apply opacity
        opacity = max(0, min(100, self.var_opacity.get()))
        if opacity < 100:
            alpha = watermark.split()[-1].point(lambda a: int(a * (opacity / 100.0)))
            watermark.putalpha(alpha)

        # Position watermark
        pad = max(0, self.var_padding.get())
        pos = self._compute_position(base.size, watermark.size, self.var_position.get(), pad)
        overlay.alpha_composite(watermark, pos)

        # Composite overlay over base
        result = Image.alpha_composite(base, overlay)
        return result

    def _compute_position(self, base_size: tuple[int, int], wm_size: tuple[int, int], pos_name: str, pad: int) -> tuple[int, int]:
        bw, bh = base_size
        ww, wh = wm_size
        if pos_name == "Top-Left":
            return (pad, pad)
        if pos_name == "Top-Right":
            return (bw - ww - pad, pad)
        if pos_name == "Bottom-Left":
            return (pad, bh - wh - pad)
        if pos_name == "Center":
            return ((bw - ww) // 2, (bh - wh) // 2)
        # Bottom-Right default
        return (bw - ww - pad, bh - wh - pad)

    def _get_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        # Try common fonts, fallback to default bitmap font
        candidates = [
            # Windows common
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/segoeui.ttf",
            # DejaVu (often present with Pillow)
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/Library/Fonts/Arial.ttf",
        ]
        for p in candidates:
            try:
                if os.path.exists(p):
                    return ImageFont.truetype(p, size=size)
            except Exception:
                continue
        try:
            return ImageFont.load_default()
        except Exception:
            return ImageFont.load_default()

    # --- Preview ---
    def update_preview(self) -> None:
        if self.base_image is None or Image is None:
            # Clear canvas
            self.canvas.delete("all")
            self.preview_photo = None
            return
        try:
            composed = self._compose_full()
        except Exception as e:
            self.lbl_status.config(text=f"Render error: {e}")
            return
        self.rendered_image = composed
        self._refresh_canvas()

    def _refresh_canvas(self) -> None:
        if self.rendered_image is None or Image is None:
            self.canvas.delete("all")
            return
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        img = self.rendered_image
        # Fit image into canvas keeping aspect ratio
        scale = min(cw / img.width, ch / img.height)
        scale = max(0.05, min(1.0, scale))
        new_w = max(1, int(img.width * scale))
        new_h = max(1, int(img.height * scale))
        preview = img.resize((new_w, new_h), Image.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(preview)
        self.canvas.delete("all")
        x = (cw - new_w) // 2
        y = (ch - new_h) // 2
        self.canvas.create_image(x, y, anchor=tk.NW, image=self.preview_photo)


def main() -> int:
    app = WatermarkApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
