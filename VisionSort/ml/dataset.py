import numpy as np
from PIL import Image, ImageDraw, ImageFilter
import torch
from torch.utils.data import Dataset
import random

# Categories mapping
CLASSES = {
    0: "Plastic",
    1: "Metal",
    2: "Biological",
    3: "Paper"
}

def generate_synthetic_item(label, size=64):
    """
    Generates a synthetic 64x64 image of a specific material category.
    Background is a textured gray color (simulating conveyor belt steel).
    """
    # Create background (steel-like textured gray)
    bg_color = random.randint(30, 50)
    image = Image.new("RGB", (size, size), (bg_color, bg_color, bg_color))
    draw = ImageDraw.Draw(image)
    
    # Add conveyor belt texture/noise
    for _ in range(50):
        x = random.randint(0, size - 1)
        y = random.randint(0, size - 1)
        noise = random.randint(-8, 8)
        c = max(0, min(255, bg_color + noise))
        draw.point((x, y), fill=(c, c, c))
        
    # Draw item based on category
    margin = 8
    obj_size = random.randint(24, 44)
    cx = size // 2 + random.randint(-4, 4)
    cy = size // 2 + random.randint(-4, 4)
    r = obj_size // 2
    
    if label == 0:  # Plastic (transparent/cyan/teal, smooth, oval shape)
        # Draw soft glowing bottle shape
        color = (random.randint(100, 180), random.randint(200, 245), random.randint(220, 255))
        # Draw semi-transparent/layered circles to simulate plastic volume
        draw.ellipse([cx - r, cy - int(r*1.3), cx + r, cy + int(r*1.3)], outline=color, width=2)
        # Highlight reflection
        draw.ellipse([cx - r//2, cy - r//2, cx - r//4, cy - r//4], fill=(255, 255, 255, 180))
        
    elif label == 1:  # Metal (silver/gray/bronze, rectangular/cylindrical, highlights)
        # Cylinder/can shape
        m_color = random.choice([
            (180, 180, 180),  # Steel/Silver
            (210, 180, 140),  # Bronze/Aluminum
            (140, 140, 150)   # Tin
        ])
        draw.rectangle([cx - int(r*0.8), cy - r, cx + int(r*0.8), cy + r], fill=m_color)
        # Add metallic reflections (vertical stripes)
        for x_offset in range(-int(r*0.4), int(r*0.4), 3):
            stripe_color = tuple(min(255, c + 35) for c in m_color)
            draw.line([cx + x_offset, cy - r, cx + x_offset, cy + r], fill=stripe_color, width=1)
            
    elif label == 2:  # Biological/Organic (yellow banana, red/green apple, green/brown leaf)
        choice = random.choice(["banana", "apple", "leaf"])
        if choice == "banana":
            # Yellow arc
            draw.arc([cx - r, cy - r, cx + r, cy + r], start=30, end=150, fill=(230, 210, 30), width=6)
            # Brown tips
            draw.point((cx - int(r*0.86), cy + r//2), fill=(100, 70, 20))
            draw.point((cx + int(r*0.86), cy + r//2), fill=(100, 70, 20))
        elif choice == "apple":
            # Red circle
            draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(220, 40, 40))
            # Green leaf
            draw.ellipse([cx - r//3, cy - r - 2, cx + 2, cy - r + 3], fill=(40, 160, 40))
        else:
            # Green/brown leaf/blob
            color = (random.randint(40, 90), random.randint(120, 180), random.randint(40, 70)) if random.random() > 0.3 else (139, 90, 43)
            draw.polygon([
                (cx, cy - r),
                (cx + r, cy),
                (cx, cy + r),
                (cx - r, cy)
            ], fill=color)
            
    elif label == 3:  # Paper/Cardboard (brown/white rectangles, lines)
        p_color = random.choice([
            (210, 180, 140),  # Cardboard Brown
            (240, 240, 240)   # White Paper
        ])
        # Draw rotated rectangle (cardboard flap/sheet)
        coords = [
            (cx - r, cy - r//2),
            (cx + r, cy - r),
            (cx + int(r*0.8), cy + r),
            (cx - int(r*0.8), cy + r//2)
        ]
        draw.polygon(coords, fill=p_color)
        # Text/lines on paper
        draw.line([cx - r//2, cy, cx + r//2, cy], fill=(50, 50, 50), width=1)
        draw.line([cx - r//3, cy + r//4, cx + r//3, cy + r//4], fill=(50, 50, 50), width=1)

    # Optional blur to simulate high-speed motion
    if random.random() > 0.5:
        image = image.filter(ImageFilter.BoxBlur(1))
        
    return image

class SyntheticSortingDataset(Dataset):
    """
    A PyTorch Dataset that generates synthetic recycling item images.
    """
    def __init__(self, size=2000, transform=None):
        self.size = size
        self.transform = transform
        # Pre-allocate labels
        self.labels = [i % 4 for i in range(size)]
        random.shuffle(self.labels)
        
    def __len__(self):
        return self.size
        
    def __getitem__(self, idx):
        label = self.labels[idx]
        pil_img = generate_synthetic_item(label)
        
        # Convert to numpy array (HWC) and normalize to [0, 1]
        img_np = np.array(pil_img, dtype=np.float32) / 255.0
        # Change layout to CHW (PyTorch format)
        img_tensor = torch.from_numpy(img_np.transpose((2, 0, 1)))
        
        if self.transform:
            img_tensor = self.transform(img_tensor)
            
        return img_tensor, label

if __name__ == "__main__":
    # Test generation and dataset
    dataset = SyntheticSortingDataset(size=10)
    img, lbl = dataset[0]
    print(f"Generated sample image of class '{CLASSES[lbl]}' (Label {lbl}). Tensor shape: {img.shape}")
