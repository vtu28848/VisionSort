import os
import sys
import torch
import torch.nn.functional as F
import numpy as np
from PIL import Image
import logging

# Ensure ML folder is in python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from ml.model import VisionSortCNN
from ml.dataset import CLASSES

logger = logging.getLogger("VisionSortMLEngine")

class VisionSortMLEngine:
    """
    ML Inference engine loading the trained PyTorch CNN weights
    and performing classification on cropped item images.
    """
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.model_loaded = False
        
        # Load weights
        model_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../ml/model.pth"))
        self.load_model(model_path)
        
    def load_model(self, path: str):
        try:
            self.model = VisionSortCNN(num_classes=4)
            if os.path.exists(path):
                # Load weights map_location matches cpu/cuda
                self.model.load_state_dict(torch.load(path, map_location=self.device))
                self.model.to(self.device)
                self.model.eval()
                self.model_loaded = True
                logger.info(f"ML Model weights loaded successfully from {path}!")
            else:
                logger.warning(f"Model weights not found at {path}. Running in Heuristic Mock mode.")
                self.model_loaded = False
        except Exception as e:
            logger.error(f"Error loading model weights: {e}. Falling back to Heuristic Mock mode.")
            self.model_loaded = False

    def predict(self, pil_image: Image.Image) -> tuple[int, float]:
        """
        Predicts the category of an item cropped from the conveyor.
        Returns:
            class_id (int)
            confidence (float)
        """
        if not self.model_loaded:
            # Fallback heuristic: guess based on average color
            return self._predict_heuristic(pil_image)
            
        try:
            # Preprocess image to match training: composite onto gray background of synthetic dataset
            if pil_image.mode == "RGBA":
                bg = Image.new("RGB", pil_image.size, (40, 40, 40))
                bg.paste(pil_image, (0, 0), pil_image)
                resized = bg.resize((64, 64))
            else:
                resized = pil_image.convert("RGB").resize((64, 64))
            img_np = np.array(resized, dtype=np.float32) / 255.0
            
            # Reorder dimensions from HWC to CHW
            img_transposed = img_np.transpose((2, 0, 1))
            
            # Convert to PyTorch tensor and send to device
            img_tensor = torch.from_numpy(img_transposed).unsqueeze(0).to(self.device)
            
            with torch.no_grad():
                logits = self.model(img_tensor)
                probs = F.softmax(logits, dim=1)
                confidence, predicted_idx = torch.max(probs, dim=1)
                
            return int(predicted_idx.item()), float(confidence.item())
        except Exception as e:
            logger.error(f"Inference error: {e}. Using fallback prediction.")
            return self._predict_heuristic(pil_image)
            
    def _predict_heuristic(self, pil_image: Image.Image) -> tuple[int, float]:
        """Heuristic fallback analyzing basic image statistics (color)."""
        if pil_image.mode == "RGBA":
            r_ch, g_ch, b_ch, a_ch = pil_image.split()
            r_np = np.array(r_ch, dtype=np.float32)
            g_np = np.array(g_ch, dtype=np.float32)
            b_np = np.array(b_ch, dtype=np.float32)
            a_np = np.array(a_ch, dtype=np.float32)
            
            mask = a_np > 20
            if mask.any():
                r = r_np[mask].mean()
                g = g_np[mask].mean()
                b = b_np[mask].mean()
            else:
                r, g, b = 40.0, 40.0, 40.0
        else:
            img_np = np.array(pil_image)
            avg_color = img_np.mean(axis=(0, 1))
            r, g, b = avg_color[0], avg_color[1], avg_color[2]
            
        # Robust relative color channel classification
        # Transparent/Teal (high green and blue relative to red) -> Plastic
        if b > r + 15 and g > r + 15 and b > 100:
            class_id = 0  # Plastic
            confidence = 0.88
        # Reddish/Yellowish fruit shapes -> Biological
        elif r > g + 30 and r > 130:
            class_id = 2  # Biological
            confidence = 0.85
        # Silver/Gray (r,g,b very close) or shiny soda can -> Metal
        elif abs(r - g) < 20 and abs(g - b) < 20 and 80 < r < 210:
            class_id = 1  # Metal
            confidence = 0.82
        # Default fallback for cardboard/crumpled paper -> Paper
        else:
            class_id = 3  # Paper
            confidence = 0.79
            
        return class_id, confidence

# Global inference engine
ml_engine = VisionSortMLEngine()
