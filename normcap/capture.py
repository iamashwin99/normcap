"""
"""
# Default
from collections import namedtuple
import logging
import tkinter
import sys

# Extra
import mss
from PIL import Image, ImageTk

# Own
from data_model import Selection
from utils import log_dataclass


class _FullscreenWindow:
    def __init__(self, root_window, current_window, shot):
        self.logger = logging.getLogger(__name__)
        self.root_window = root_window
        self.tk = current_window
        # self.tk.attributes("-fullscreen", True)
        self.tk.configure(bg="black")  # To hide top border on i3
        self.shot = shot
        self.area_thres = 400

        # Produces frame, useful for debug
        self.frame = tkinter.Frame(self.tk)
        self.frame.pack()

        # Create canvas
        self.canvas = tkinter.Canvas(
            self.tk,
            bg="red",
            width=self.shot.position["width"],
            height=self.shot.position["height"],
            highlightthickness=0,
            borderwidth=0,
            relief="flat",
            cursor="cross",
        )
        self.canvas.pack(expand=tkinter.YES, fill=tkinter.BOTH)

        # Add image to canvas
        tkimage = ImageTk.PhotoImage(shot.image)
        self.screen_gc = tkimage  # Prevent img being garbage collected
        self.canvas.create_image(0, 0, anchor="nw", image=tkimage)

        # Add border as NormCap indication
        self.draw_border()

        # Prepare rectangle
        self.rect = None
        self.start_x = None
        self.start_y = None
        self.x = 0
        self.y = 0

        # Bindings
        self.root_window.bind_all("<Escape>", self.on_escape_press)
        self.canvas.bind("<B1-Motion>", self.on_move_press)
        self.canvas.bind("<ButtonPress-1>", self.on_button_press)
        self.canvas.bind("<ButtonRelease-1>", self.on_button_release)

        # Set size & pos
        self.tk.geometry(
            f"{shot.position['width']}x{shot.position['height']}"
            + f"+{shot.position['left']}+{shot.position['top']}"
        )
        self.tk.overrideredirect(1)

    def draw_border(self):
        self.canvas.create_rectangle(
            0,
            0,
            self.shot.position["width"] - 1,
            self.shot.position["height"] - 2,
            width=3,
            outline="red",
        )

    def on_escape_press(self, event):
        self.logger.info("ESC pressed: Aborting screen capture")
        self.end_fullscreen()

    def is_valid_selected_area(self, position):
        # Calculate selected area
        if position is not None:
            area = (position["lower"] - position["upper"]) * (
                position["right"] - position["left"]
            )
        else:
            area = 0

        # Check for threshold
        if area >= self.area_thres:
            large_enough = True
        else:
            large_enough = False
            self.logger.warn(
                f"Selection area of {area:.0f} px² is below threshold of {self.area_thres} px²]"
            )

        return large_enough

    def end_fullscreen(self, result=None):
        if self.is_valid_selected_area(result):
            self.root_window.result = result
        else:
            self.root_window.result = None
        self.root_window.destroy()

    def on_button_press(self, event):
        # save mouse start position
        self.start_x = self.canvas.canvasx(event.x)
        self.start_y = self.canvas.canvasy(event.y)

        # create rectangle
        if not self.rect:
            self.rect = self.canvas.create_rectangle(
                self.x, self.y, 1, 1, outline="red"
            )

    def on_move_press(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)

        # expand rectangle as you drag the mouse
        self.canvas.coords(self.rect, self.start_x, self.start_y, cur_x, cur_y)

    def on_button_release(self, event):
        cur_x = self.canvas.canvasx(event.x)
        cur_y = self.canvas.canvasy(event.y)

        crop_args = {
            "monitor": self.shot.monitor,
            "upper": min([cur_y, self.start_y]),
            "lower": max([cur_y, self.start_y]),
            "left": min([cur_x, self.start_x]),
            "right": max([cur_x, self.start_x]),
        }

        self.end_fullscreen(result=crop_args)


class Capture:
    def __init__(self, *args, **kwargs):
        self.logger = logging.getLogger(__name__)
        self.clicks = []
        self.Shot = namedtuple("Shot", "monitor image position")
        self.shots = []
        self.selection = None
        return super().__init__(*args, **kwargs)

    def select_region_with_gui(self):
        root = tkinter.Tk()
        for idx, shot in enumerate(self.shots):
            if idx == 0:
                _FullscreenWindow(root, root, shot)
            else:
                top = tkinter.Toplevel()
                _FullscreenWindow(root, top, shot)
        root.mainloop()

        # Store result in selection class
        result = root.result
        if result:
            self.selection = Selection(
                bottom=result["lower"],
                top=result["upper"],
                left=result["left"],
                right=result["right"],
                monitor=result["monitor"],
            )
        else:
            self.logger.info("Exiting. No selection available.")
            sys.exit(0)

    def crop_shot(self):
        crop_monitor = self.shots[self.selection.monitor]
        cropped_image = crop_monitor.image.crop(
            (
                self.selection.left,
                self.selection.top,
                self.selection.right,
                self.selection.bottom,
            )
        )
        self.selection.image_full = crop_monitor.image
        self.selection.image = cropped_image
        log_dataclass(self.selection)

    def capture_screen(self):
        with mss.mss() as sct:
            # Grab all screens
            for idx, position in enumerate(sct.monitors[1:]):
                # Capture
                temp_shot = sct.grab(position)
                # Convert to Pil
                temp_img = Image.frombytes(
                    "RGB", temp_shot.size, temp_shot.bgra, "raw", "BGRX"
                )
                # Append list with screenshots
                temp_shot = self.Shot(monitor=idx, image=temp_img, position=position)
                self.shots.append(temp_shot)
        return
