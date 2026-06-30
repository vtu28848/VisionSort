import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
import os
import argparse
from model import VisionSortCNN
from dataset import SyntheticSortingDataset, CLASSES

def train_model(epochs=5, batch_size=32, lr=0.001):
    # Set device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"VisionSort Model Training Pipeline starting...")
    print(f"Device: {device}")
    
    # Initialize datasets
    print("Generating synthetic datasets (Training: 1200, Validation: 300)...")
    train_dataset = SyntheticSortingDataset(size=1200)
    val_dataset = SyntheticSortingDataset(size=300)
    
    # Create dataloaders
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    # Initialize model
    model = VisionSortCNN(num_classes=4).to(device)
    
    # Loss and Optimizer
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)
    
    print(f"Training parameters: Epochs={epochs}, Batch Size={batch_size}, LR={lr}")
    print("-" * 50)
    
    for epoch in range(1, epochs + 1):
        # Training phase
        model.train()
        running_loss = 0.0
        correct_train = 0
        total_train = 0
        
        for images, labels in train_loader:
            images, labels = images.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            
            running_loss += loss.item() * images.size(0)
            _, predicted = torch.max(outputs.data, 1)
            total_train += labels.size(0)
            correct_train += (predicted == labels).sum().item()
            
        epoch_loss = running_loss / len(train_loader.dataset)
        epoch_acc = (correct_train / total_train) * 100
        
        # Validation phase
        model.eval()
        val_loss = 0.0
        correct_val = 0
        total_val = 0
        
        with torch.no_grad():
            for images, labels in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                loss = criterion(outputs, labels)
                
                val_loss += loss.item() * images.size(0)
                _, predicted = torch.max(outputs.data, 1)
                total_val += labels.size(0)
                correct_val += (predicted == labels).sum().item()
                
        val_epoch_loss = val_loss / len(val_loader.dataset)
        val_epoch_acc = (correct_val / total_val) * 100
        
        print(f"Epoch [{epoch}/{epochs}] "
              f"| Train Loss: {epoch_loss:.4f} | Train Acc: {epoch_acc:.2f}% "
              f"| Val Loss: {val_epoch_loss:.4f} | Val Acc: {val_epoch_acc:.2f}%")
              
    # Save the model
    os.makedirs(os.path.dirname(__file__) or ".", exist_ok=True)
    save_path = os.path.join(os.path.dirname(__file__) or ".", "model.pth")
    torch.save(model.state_dict(), save_path)
    print("-" * 50)
    print(f"Model saved successfully to: {os.path.abspath(save_path)}")
    print(f"VisionSort model weights generated successfully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train custom VisionSort CNN")
    parser.add_argument("--epochs", type=int, default=5, help="Number of epochs to train")
    parser.add_argument("--batch_size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=0.001, help="Learning rate")
    args = parser.parse_args()
    
    train_model(epochs=args.epochs, batch_size=args.batch_size, lr=args.lr)
