import torch
import torch.nn as nn
import torch.nn.functional as F

class VisionSortCNN(nn.Module):
    """
    A custom Convolutional Neural Network (CNN) for high-speed object classification
    on sorting lines. Inputs are 64x64 RGB images of cropped sorting items.
    """
    def __init__(self, num_classes=4):
        super(VisionSortCNN, self).__init__()
        
        # Convolutional layers
        # Input: 3 x 64 x 64
        self.conv1 = nn.Conv2d(in_channels=3, out_channels=16, kernel_size=3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(16)
        
        # Input: 16 x 32 x 32 (after pooling)
        self.conv2 = nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(32)
        
        # Input: 32 x 16 x 16 (after pooling)
        self.conv3 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
        self.bn3 = nn.BatchNorm2d(64)
        
        # Pooling layer
        self.pool = nn.MaxPool2d(kernel_size=2, stride=2)
        
        # Fully connected layers
        # After 3 pooling layers, 64x64 becomes 8x8 (64 -> 32 -> 16 -> 8)
        self.fc1 = nn.Linear(64 * 8 * 8, 128)
        self.dropout = nn.Dropout(0.3)
        self.fc2 = nn.Linear(128, num_classes)
        
    def forward(self, x):
        # Conv block 1
        x = self.pool(F.relu(self.bn1(self.conv1(x))))
        # Conv block 2
        x = self.pool(F.relu(self.bn2(self.conv2(x))))
        # Conv block 3
        x = self.pool(F.relu(self.bn3(self.conv3(x))))
        
        # Flatten
        x = x.view(-1, 64 * 8 * 8)
        
        # FC block
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        return x

if __name__ == "__main__":
    # Quick dimensions check
    model = VisionSortCNN()
    test_tensor = torch.randn(1, 3, 64, 64)
    out = model(test_tensor)
    print("Inference test successful! Input: 1x3x64x64, Output shape:", out.shape)
