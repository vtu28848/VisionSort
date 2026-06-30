import asyncio
import io
import base64
import random
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import logging
from datetime import datetime
from backend.ml_engine import ml_engine
from backend.database import db
from ml.dataset import generate_synthetic_item, CLASSES
import os

logger = logging.getLogger("VisionSortStreamer")

# Load crisp TrueType fonts for high-clarity dashboard names
def load_industrial_font(size):
    for f in ["consola.ttf", "lucon.ttf", "tahoma.ttf", "arial.ttf"]:
        try:
            return ImageFont.truetype(f, size)
        except IOError:
            continue
    # Check absolute windows font path just in case
    win_path = f"C:\\Windows\\Fonts\\consola.ttf"
    if os.path.exists(win_path):
        try:
            return ImageFont.truetype(win_path, size)
        except IOError:
            pass
    return ImageFont.load_default()

font_sm = load_industrial_font(12)
font_md = load_industrial_font(14)
font_lg = load_industrial_font(16)

def generate_transparent_item(label, size=64):
    """Generates an item with alpha transparency for realistic conveyor rendering."""
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    obj_size = random.randint(34, 44)
    cx = size // 2
    cy = size // 2
    r = obj_size // 2
    
    if label == 0:  # Plastic (Detailed Cyan/Teal Water Bottle)
        cap_y1 = cy - r
        cap_y2 = cy - r + 6
        neck_y1 = cap_y2
        neck_y2 = cy - r//2
        body_y1 = neck_y2
        body_y2 = cy + r
        
        # Cap (solid dark blue/teal)
        draw.rectangle([cx - 6, cap_y1, cx + 6, cap_y2], fill=(0, 119, 182, 255), outline=(3, 83, 151, 255))
        
        # Neck (translucent cyan/teal)
        draw.polygon([(cx - 6, neck_y1), (cx + 6, neck_y1), (cx + 10, neck_y2), (cx - 10, neck_y2)], 
                     fill=(144, 224, 239, 160), outline=(0, 180, 216, 225))
        
        # Main Body
        draw.rectangle([cx - 12, body_y1, cx + 12, body_y2], fill=(144, 224, 239, 90), outline=(0, 180, 216, 225), width=2)
        draw.chord([cx - 12, body_y2 - 8, cx + 12, body_y2 + 4], start=0, end=180, fill=(144, 224, 239, 90), outline=(0, 180, 216, 225), width=2)
        
        # Brand Label
        draw.rectangle([cx - 12, cy - 4, cx + 12, cy + 4], fill=(255, 255, 255, 220))
        draw.rectangle([cx - 8, cy - 2, cx + 8, cy + 2], fill=(46, 204, 113, 200))
        
        # Highlights/ridges on bottle
        draw.line([cx - 8, cy - 10, cx + 8, cy - 10], fill=(255, 255, 255, 120), width=1)
        draw.line([cx - 8, cy + 10, cx + 8, cy + 10], fill=(255, 255, 255, 120), width=1)
        draw.line([cx - 6, neck_y2 + 2, cx - 6, body_y2 - 2], fill=(255, 255, 255, 180), width=2)
        
    elif label == 1:  # Metal (Detailed Soda Can with Pull Tab)
        # Silver metal top
        draw.ellipse([cx - 12, cy - r, cx + 12, cy - r + 6], fill=(189, 195, 199, 255), outline=(127, 140, 141, 255))
        draw.ellipse([cx - 3, cy - r + 1, cx + 1, cy - r + 4], fill=(127, 140, 141, 255))
        
        # Can body
        body_color = random.choice([
            (231, 76, 60, 255),   # Red Cola Can
            (52, 152, 219, 255),  # Blue Pepsi style
            (46, 204, 113, 255)   # Green Sprite style
        ])
        draw.rectangle([cx - 12, cy - r + 3, cx + 12, cy + r - 3], fill=body_color, outline=(127, 140, 141, 255))
        
        # Curved can highlight
        draw.rectangle([cx - 8, cy - r + 3, cx - 4, cy + r - 3], fill=(255, 255, 255, 80))
        draw.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(255, 255, 255, 200))
        
        # Bottom metal rim
        draw.ellipse([cx - 12, cy + r - 6, cx + 12, cy + r], fill=(127, 140, 141, 255))
        
    elif label == 2:  # Biological (Detailed Organic Apple with stem and leaves)
        draw.ellipse([cx - 14, cy - 10, cx + 2, cy + 12], fill=(231, 76, 60, 255), outline=(192, 57, 43, 255))
        draw.ellipse([cx - 2, cy - 10, cx + 14, cy + 12], fill=(231, 76, 60, 255), outline=(192, 57, 43, 255))
        draw.ellipse([cx - 10, cy, cx + 2, cy + 8], fill=(241, 196, 15, 120))
        
        # Stem
        draw.line([cx, cy - 10, cx + 4, cy - 20], fill=(139, 69, 19, 255), width=3)
        # Leaf
        draw.polygon([(cx + 4, cy - 20), (cx + 14, cy - 24), (cx + 10, cy - 15)], fill=(39, 174, 96, 255))
        draw.line([cx + 4, cy - 20, cx + 10, cy - 18], fill=(255, 255, 255, 100), width=1)
        
        # Shiny white reflection spot
        draw.ellipse([cx - 8, cy - 6, cx - 3, cy - 2], fill=(255, 255, 255, 220))
        
    elif label == 3:  # Paper (Detailed Cardboard Box with Packing Tape)
        box_color = (210, 180, 140, 255)
        outline_color = (139, 90, 43, 255)
        draw.rectangle([cx - 14, cy - 14, cx + 14, cy + 14], fill=box_color, outline=outline_color, width=2)
        draw.rectangle([cx - 3, cy - 14, cx + 3, cy + 14], fill=(139, 69, 19, 180))
        draw.rectangle([cx + 2, cy - 8, cx + 10, cy], fill=(255, 255, 255, 255))
        draw.line([cx + 4, cy - 4, cx + 8, cy - 4], fill=(0, 0, 0, 255), width=1)
        draw.line([cx + 4, cy - 2, cx + 8, cy - 2], fill=(0, 0, 0, 255), width=1)
        
    return image


class ConveyorStreamer:
    """
    Simulates an industrial conveyor belt, rendering frames at high speed,
    running CNN inference on items, and logging metrics to the database.
    This version is simplified and runs sorting operations without E-Stops or jams.
    """
    def __init__(self):
        self.width = 800
        self.height = 300
        self.is_running = False
        self.speed = 1.67  # Pixels per frame (baseline 0.5x at 30 FPS)
        self.speed_multiplier = 0.5
        self.items = []
        self.item_counter = 0
        self.target_material = "Plastic"  # Active stream target
        self.diverter_type = "Air Jet"     # Active diverter mechanism
        self.bypass_mode = False           # If True, bypasses all contaminants
        
        # Statistics
        self.total_sorted = 0
        self.faults_detected = 0
        self.overall_accuracy = 98.5
        self.conveyor_ticks = 0
        
        # Callbacks (to broadcast via WebSockets)
        self.broadcast_callback = None

    def start(self):
        if not self.is_running:
            self.is_running = True
            asyncio.create_task(self._stream_loop())
            logger.info("Conveyor belt simulator started.")

    def stop(self):
        self.is_running = False
        logger.info("Conveyor belt simulator stopped.")

    def set_speed(self, speed_multiplier: float):
        self.speed_multiplier = max(0.1, min(15.0, speed_multiplier))
        self.speed = self.speed_multiplier * 3.333
        logger.info(f"Conveyor speed multiplier set to {self.speed_multiplier}x ({self.speed:.2f} px/frame).")

    def set_target_material(self, material: str):
        if material in CLASSES.values():
            self.target_material = material
            logger.info(f"Sorting target changed to: {material}")

    def set_diverter_type(self, div_type: str):
        if div_type in ["Air Jet", "Piston", "Swing Arm", "Drop Gate", "Suction Lifter"]:
            self.diverter_type = div_type
            logger.info(f"Diverter type changed to: {div_type}")

    def set_bypass_mode(self, active: bool):
        self.bypass_mode = active
        logger.info(f"Bypass mode changed to: {active}")

    async def _stream_loop(self):
        while self.is_running:
            try:
                # Update positions and spawn new items
                self._update_conveyor_state()
                
                # Render the conveyor frame
                frame_data = self._render_frame()
                
                # Broadcast frame and metrics
                if self.broadcast_callback:
                    await self.broadcast_callback(frame_data)
                    
            except Exception as e:
                logger.error(f"Error in conveyor stream loop: {e}")
                
            # Run at roughly 30 FPS (33ms sleep)
            await asyncio.sleep(0.033)

    def get_diverter_piston(self, category: str) -> int:
        if category == self.target_material:
            return 0
        contaminants = [c for c in ["Plastic", "Metal", "Biological", "Paper"] if c != self.target_material]
        for i, c in enumerate(contaminants):
            if category == c:
                return i + 1
        return 1

    def _update_conveyor_state(self):
        self.conveyor_ticks += 1
        
        # Move existing items
        for item in self.items:
            if item["diverted"] and item["predicted_category"] != self.target_material and not item.get("bypassed", False):
                px = 380.0 if item.get("piston") == 1 else (520.0 if item.get("piston") == 2 else 660.0)
                item["x"] = px + (item["x"] - px) * 0.1
                item["y"] += 25.0
            else:
                item["x"] += self.speed
            
            # Check if item enters detection zone (centered at 160-300 before Piston 1)
            if 160 <= item["x"] <= 300 and not item["classified"]:
                self._classify_item(item)
                
            # Check if contaminant reaches Piston 1 (x = 380)
            if item["x"] >= 380 and not item.get("piston_1_checked", False):
                item["piston_1_checked"] = True
                if not self.bypass_mode:
                    p = self.get_diverter_piston(item["predicted_category"])
                    if p == 1:
                        item["diverted"] = True
                        item["piston"] = 1
                        item["divert_time"] = 4
                        self.faults_detected += 1
                        asyncio.create_task(db.log_sorting_event(
                            category=item["category"],
                            confidence=item["confidence"],
                            status="Fault",
                            conveyor_speed=self.speed
                        ))
                else:
                    item["bypassed"] = True
                    
            # Check if contaminant reaches Piston 2 (x = 520)
            if item["x"] >= 520 and not item.get("piston_2_checked", False):
                item["piston_2_checked"] = True
                if not self.bypass_mode and not item["diverted"]:
                    p = self.get_diverter_piston(item["predicted_category"])
                    if p == 2:
                        item["diverted"] = True
                        item["piston"] = 2
                        item["divert_time"] = 4
                        self.faults_detected += 1
                        asyncio.create_task(db.log_sorting_event(
                            category=item["category"],
                            confidence=item["confidence"],
                            status="Fault",
                            conveyor_speed=self.speed
                        ))
                elif self.bypass_mode:
                    item["bypassed"] = True

            # Check if contaminant reaches Piston 3 (x = 660)
            if item["x"] >= 660 and not item.get("piston_3_checked", False):
                item["piston_3_checked"] = True
                if not self.bypass_mode and not item["diverted"]:
                    p = self.get_diverter_piston(item["predicted_category"])
                    if p == 3:
                        item["diverted"] = True
                        item["piston"] = 3
                        item["divert_time"] = 4
                        self.faults_detected += 1
                        asyncio.create_task(db.log_sorting_event(
                            category=item["category"],
                            confidence=item["confidence"],
                            status="Fault",
                            conveyor_speed=self.speed
                        ))
                elif self.bypass_mode:
                    item["bypassed"] = True

            # Check if target reaches success zone (end of belt x >= 740)
            if item["x"] >= 740 and not item.get("success_logged", False):
                item["success_logged"] = True
                if not item["diverted"] and item["predicted_category"] == self.target_material:
                    self.total_sorted += 1
                    asyncio.create_task(db.log_sorting_event(
                        category=item["category"],
                        confidence=item["confidence"],
                        status="Success",
                        conveyor_speed=self.speed
                    ))

        # Filter out items that have moved off screen (x > width or y leaves vertical bounds)
        self.items = [item for item in self.items if item["x"] < self.width + 40 and -40 < item["y"] < self.height + 40]
        
        # Spawn new items on the left (x = -40)
        if len(self.items) == 0 or (self.items[-1]["x"] > random.randint(100, 220)):
            self.item_counter += 1
            lbl = random.randint(0, 3)
            category = CLASSES[lbl]
            item_patch = generate_transparent_item(lbl, size=64)
            
            self.items.append({
                "id": self.item_counter,
                "x": -40.0,
                "y": random.randint(60, self.height - 80),
                "category": category,
                "label": lbl,
                "classified": False,
                "diverted": False,
                "divert_time": 0,
                "predicted_category": "Pending",
                "confidence": 0.0,
                "patch": item_patch
            })

    def _classify_item(self, item):
        """Runs the PyTorch CNN model to classify the cropped item."""
        item["classified"] = True
        
        # Use ML engine to predict
        predicted_lbl, confidence = ml_engine.predict(item["patch"])
        predicted_category = CLASSES[predicted_lbl]
        
        item["predicted_category"] = predicted_category
        item["confidence"] = confidence
        
        # Calculate real-time accuracy shift
        is_correct = (predicted_category == item["category"])
        accuracy_weight = 0.05
        current_acc = self.overall_accuracy
        target_acc = 100.0 if is_correct else 0.0
        self.overall_accuracy = (current_acc * (1 - accuracy_weight)) + (target_acc * accuracy_weight)

    def _render_frame(self) -> dict:
        """Renders the conveyor belt state into a JPEG base64 image."""
        # Create conveyor background (charcoal factory floor plates)
        frame = Image.new("RGB", (self.width, self.height), (20, 22, 25))
        draw = ImageDraw.Draw(frame)
        
        # Factory floor panel gridlines
        for gx in range(0, self.width, 100):
            draw.line([gx, 0, gx, self.height], fill=(28, 30, 35), width=2)
        for gy in range(0, self.height, 50):
            draw.line([0, gy, self.width, gy], fill=(28, 30, 35), width=2)
        for gx in range(100, self.width, 100):
            for gy in range(50, self.height, 50):
                draw.ellipse([gx - 2, gy - 2, gx + 2, gy + 2], fill=(74, 79, 88))

        belt_y1 = 40
        belt_y2 = self.height - 40

        # Draw Physical Collection Chutes (behind belt)
        # Chute 1 (at x = 380)
        draw.polygon([(340, belt_y2), (420, belt_y2), (405, self.height), (355, self.height)], fill=(47, 54, 64), outline=(116, 125, 140), width=2)
        draw.polygon([(350, belt_y2), (410, belt_y2), (395, self.height - 2), (365, self.height - 2)], fill=(24, 28, 36))
        draw.text((352, self.height - 18), "SORTING 1", fill=(116, 125, 140), font=font_sm)

        # Chute 2 (at x = 520)
        draw.polygon([(480, belt_y2), (560, belt_y2), (545, self.height), (495, self.height)], fill=(47, 54, 64), outline=(116, 125, 140), width=2)
        draw.polygon([(490, belt_y2), (550, belt_y2), (535, self.height - 2), (505, self.height - 2)], fill=(24, 28, 36))
        draw.text((492, self.height - 18), "SORTING 2", fill=(116, 125, 140), font=font_sm)

        # Chute 3 (at x = 660)
        draw.polygon([(620, belt_y2), (700, belt_y2), (685, self.height), (635, self.height)], fill=(47, 54, 64), outline=(116, 125, 140), width=2)
        draw.polygon([(630, belt_y2), (690, belt_y2), (675, self.height - 2), (645, self.height - 2)], fill=(24, 28, 36))
        draw.text((632, self.height - 18), "SORTING 3", fill=(116, 125, 140), font=font_sm)
        
        # Draw conveyor belt base
        draw.rectangle([0, belt_y1, self.width, belt_y2], fill=(34, 36, 40))
        
        # Draw horizontal moving slat lines
        offset = int(self.conveyor_ticks * self.speed) % 30
        for bx in range(-30 + offset, self.width + 30, 30):
            draw.line([bx, belt_y1, bx, belt_y2], fill=(26, 28, 31), width=2)

        # Draw Side Rollers
        for x in range(-80 + offset, self.width + 80, 80):
            draw.ellipse([x - 10, belt_y1 - 6, x + 10, belt_y1 + 6], fill=(74, 79, 88), outline=(149, 150, 155))
            draw.ellipse([x - 10, belt_y2 - 6, x + 10, belt_y2 + 6], fill=(74, 79, 88), outline=(149, 150, 155))
            
        # Draw Steel Guard Rails
        draw.rectangle([0, belt_y1 - 6, self.width, belt_y1], fill=(130, 137, 143), outline=(75, 80, 85), width=1)
        draw.line([0, belt_y1 - 5, self.width, belt_y1 - 5], fill=(220, 225, 230), width=1)  # highlight
        draw.rectangle([0, belt_y2, self.width, belt_y2 + 6], fill=(130, 137, 143), outline=(75, 80, 85), width=1)
        draw.line([0, belt_y2 + 1, self.width, belt_y2 + 1], fill=(220, 225, 230), width=1)  # highlight
        
        # Mounting bolts on rails
        for bx in range(40, self.width, 80):
            draw.ellipse([bx - 3, belt_y1 - 4, bx + 3, belt_y1 - 1], fill=(80, 85, 90))
            draw.ellipse([bx - 3, belt_y2 + 1, bx + 3, belt_y2 + 4], fill=(80, 85, 90))

        # Create alpha overlay for overhead scanner beam
        beam_overlay = Image.new("RGBA", (self.width, self.height), (0, 0, 0, 0))
        beam_draw = ImageDraw.Draw(beam_overlay)
        # Translucent light beam cone projecting down from x=230 to 160-300 zone on belt
        beam_draw.polygon([(220, 0), (240, 0), (300, belt_y2), (160, belt_y2)], fill=(0, 210, 255, 35))
        # Composite beam overlay
        frame = Image.alpha_composite(frame.convert("RGBA"), beam_overlay).convert("RGB")
        draw = ImageDraw.Draw(frame)
        
        # Draw Overhead Scanner Lens Camera Body
        draw.rectangle([220, 0, 240, 15], fill=(53, 59, 72), outline=(127, 140, 141))
        draw.ellipse([215, 10, 245, 25], fill=(47, 53, 66), outline=(0, 210, 255), width=2)
        # Blinking active green LED status
        led_color = (46, 204, 113) if (self.conveyor_ticks % 10 < 5) else (39, 174, 96)
        draw.ellipse([227, 5, 233, 11], fill=led_color)
        draw.text((255, 8), "SCANNING", fill=(0, 210, 255), font=font_md)
        
        # Draw transparent items onto conveyor belt
        for item in self.items:
            ix, iy = int(item["x"]), int(item["y"])
            
            # If item is diverted, push it down the belt at a smooth vertical deflection rate
            if item["diverted"] and item["predicted_category"] != self.target_material and not item.get("bypassed", False):
                iy = int(item["y"])
                
            # Paste item using its alpha channel as a mask for pixel-perfect transparency
            frame.paste(item["patch"], (ix - 32, iy - 32), item["patch"])
            
            # Draw bounding box
            if item["classified"]:
                is_target = (item["predicted_category"] == self.target_material)
                box_color = (46, 204, 113) if is_target else (231, 76, 60)
                draw.rectangle([ix - 32, iy - 32, ix + 32, iy + 32], outline=box_color, width=2)
                label_text = f"{item['predicted_category']} {item['confidence']:.0%}"
                draw.text((ix - 32, iy - 48), label_text, fill=box_color, font=font_sm)
                
        # --- Draw Triple Pneumatic Pistons (P1 at 380, P2 at 520, P3 at 660) ---
        contaminants = [c for c in ["Plastic", "Metal", "Biological", "Paper"] if c != self.target_material]
        p1_text = f"P1 ({contaminants[0].upper()})" if len(contaminants) >= 1 else "P1"
        p2_text = f"P2 ({contaminants[1].upper()})" if len(contaminants) >= 2 else "P2"
        p3_text = f"P3 ({contaminants[2].upper()})" if len(contaminants) >= 3 else "P3"

        # Check active states for Piston 1, Piston 2, and Piston 3
        piston1_active = False
        piston2_active = False
        piston3_active = False
        p1_target_y = belt_y1 + 20
        p2_target_y = belt_y1 + 20
        p3_target_y = belt_y1 + 20
        
        for item in self.items:
            if item["divert_time"] > 0:
                if item.get("piston") == 1:
                    piston1_active = True
                    p1_target_y = max(p1_target_y, item["y"])
                elif item.get("piston") == 2:
                    piston2_active = True
                    p2_target_y = max(p2_target_y, item["y"])
                elif item.get("piston") == 3:
                    piston3_active = True
                    p3_target_y = max(p3_target_y, item["y"])

        # Draw Piston 1 (x = 380)
        draw.rectangle([370, 0, 390, belt_y1 - 5], fill=(53, 59, 72), outline=(189, 195, 199), width=2)
        draw.rectangle([365, 0, 395, 4], fill=(74, 79, 88))
        if piston1_active:
            draw.line([380, belt_y1 - 5, 380, p1_target_y], fill=(220, 221, 225), width=8)
            draw.line([381, belt_y1 - 5, 381, p1_target_y], fill=(255, 255, 255), width=2)
            draw.rectangle([372, p1_target_y - 6, 388, p1_target_y], fill=(116, 125, 140))
            draw.rectangle([350, p1_target_y, 410, p1_target_y + 12], fill=(230, 126, 34), outline=(211, 84, 0), width=1)
            draw.line([360, p1_target_y + 2, 365, p1_target_y + 10], fill=(0, 0, 0), width=2)
            draw.line([375, p1_target_y + 2, 380, p1_target_y + 10], fill=(0, 0, 0), width=2)
            draw.line([390, p1_target_y + 2, 395, p1_target_y + 10], fill=(0, 0, 0), width=2)
            draw.ellipse([354, 6, 364, 16], fill=(245, 246, 250), outline=(220, 221, 225))
            draw.line([370, 11, 356, 5], fill=(220, 221, 225), width=2)
            draw.line([370, 11, 356, 17], fill=(220, 221, 225), width=2)
        else:
            draw.line([380, belt_y1 - 5, 380, belt_y1 + 5], fill=(220, 221, 225), width=8)
            draw.rectangle([372, belt_y1 + 4, 388, belt_y1 + 8], fill=(116, 125, 140))
            draw.rectangle([350, belt_y1 + 8, 410, belt_y1 + 20], fill=(211, 84, 0), outline=(127, 140, 141), width=1)
            draw.line([360, belt_y1 + 10, 365, belt_y1 + 18], fill=(0, 0, 0), width=2)
            draw.line([375, belt_y1 + 10, 380, belt_y1 + 18], fill=(0, 0, 0), width=2)
            draw.line([390, belt_y1 + 10, 395, belt_y1 + 18], fill=(0, 0, 0), width=2)
        draw.text((355, belt_y2 - 20), p1_text, fill=(243, 156, 18), font=font_sm)

        # Draw Piston 2 (x = 520)
        draw.rectangle([510, 0, 530, belt_y1 - 5], fill=(53, 59, 72), outline=(189, 195, 199), width=2)
        draw.rectangle([505, 0, 535, 4], fill=(74, 79, 88))
        if piston2_active:
            draw.line([520, belt_y1 - 5, 520, p2_target_y], fill=(220, 221, 225), width=8)
            draw.line([521, belt_y1 - 5, 521, p2_target_y], fill=(255, 255, 255), width=2)
            draw.rectangle([512, p2_target_y - 6, 528, p2_target_y], fill=(116, 125, 140))
            draw.rectangle([490, p2_target_y, 550, p2_target_y + 12], fill=(230, 126, 34), outline=(211, 84, 0), width=1)
            draw.line([500, p2_target_y + 2, 505, p2_target_y + 10], fill=(0, 0, 0), width=2)
            draw.line([515, p2_target_y + 2, 520, p2_target_y + 10], fill=(0, 0, 0), width=2)
            draw.line([530, p2_target_y + 2, 535, p2_target_y + 10], fill=(0, 0, 0), width=2)
            draw.ellipse([494, 6, 504, 16], fill=(245, 246, 250), outline=(220, 221, 225))
            draw.line([510, 11, 496, 5], fill=(220, 221, 225), width=2)
            draw.line([510, 11, 496, 17], fill=(220, 221, 225), width=2)
        else:
            draw.line([520, belt_y1 - 5, 520, belt_y1 + 5], fill=(220, 221, 225), width=8)
            draw.rectangle([512, belt_y1 + 4, 528, belt_y1 + 8], fill=(116, 125, 140))
            draw.rectangle([490, belt_y1 + 8, 550, belt_y1 + 20], fill=(211, 84, 0), outline=(127, 140, 141), width=1)
            draw.line([500, belt_y1 + 10, 505, belt_y1 + 18], fill=(0, 0, 0), width=2)
            draw.line([515, belt_y1 + 10, 520, belt_y1 + 18], fill=(0, 0, 0), width=2)
            draw.line([530, belt_y1 + 10, 535, belt_y1 + 18], fill=(0, 0, 0), width=2)
        draw.text((495, belt_y2 - 20), p2_text, fill=(243, 156, 18), font=font_sm)

        # Draw Piston 3 (x = 660)
        draw.rectangle([650, 0, 670, belt_y1 - 5], fill=(53, 59, 72), outline=(189, 195, 199), width=2)
        draw.rectangle([645, 0, 675, 4], fill=(74, 79, 88))
        if piston3_active:
            draw.line([660, belt_y1 - 5, 660, p3_target_y], fill=(220, 221, 225), width=8)
            draw.line([661, belt_y1 - 5, 661, p3_target_y], fill=(255, 255, 255), width=2)
            draw.rectangle([652, p3_target_y - 6, 668, p3_target_y], fill=(116, 125, 140))
            draw.rectangle([630, p3_target_y, 690, p3_target_y + 12], fill=(230, 126, 34), outline=(211, 84, 0), width=1)
            draw.line([640, p3_target_y + 2, 645, p3_target_y + 10], fill=(0, 0, 0), width=2)
            draw.line([655, p3_target_y + 2, 660, p3_target_y + 10], fill=(0, 0, 0), width=2)
            draw.line([670, p3_target_y + 2, 675, p3_target_y + 10], fill=(0, 0, 0), width=2)
            draw.ellipse([634, 6, 644, 16], fill=(245, 246, 250), outline=(220, 221, 225))
            draw.line([650, 11, 636, 5], fill=(220, 221, 225), width=2)
            draw.line([650, 11, 636, 17], fill=(220, 221, 225), width=2)
        else:
            draw.line([660, belt_y1 - 5, 660, belt_y1 + 5], fill=(220, 221, 225), width=8)
            draw.rectangle([652, belt_y1 + 4, 668, belt_y1 + 8], fill=(116, 125, 140))
            draw.rectangle([630, belt_y1 + 8, 690, belt_y1 + 20], fill=(211, 84, 0), outline=(127, 140, 141), width=1)
            draw.line([640, belt_y1 + 10, 645, belt_y1 + 18], fill=(0, 0, 0), width=2)
            draw.line([655, belt_y1 + 10, 660, belt_y1 + 18], fill=(0, 0, 0), width=2)
            draw.line([670, belt_y1 + 10, 675, belt_y1 + 18], fill=(0, 0, 0), width=2)
        draw.text((635, belt_y2 - 20), p3_text, fill=(243, 156, 18), font=font_sm)
        
        # Decrement divert time counters
        for item in self.items:
            if item["divert_time"] > 0:
                item["divert_time"] -= 1

        # Compress image to JPEG
        buffered = io.BytesIO()
        frame.save(buffered, format="JPEG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # Calculate contamination rate
        contamination_rate = 0.0
        if self.total_sorted + self.faults_detected > 0:
            contamination_rate = (self.faults_detected / (self.total_sorted + self.faults_detected)) * 100
            
        return {
            "image": img_str,
            "target_material": self.target_material,
            "speed": self.speed_multiplier,
            "diverter_type": self.diverter_type,
            "bypass_mode": self.bypass_mode,
            "metrics": {
                "total_sorted": self.total_sorted,
                "faults_detected": self.faults_detected,
                "contamination_rate": round(contamination_rate, 1),
                "accuracy": round(self.overall_accuracy, 2),
                "db_status": db.get_status_label()
            }
        }

# Global conveyor simulation instance
conveyor = ConveyorStreamer()
